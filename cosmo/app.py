import asyncio
import socket
import sys

import uvloop
from loguru import logger

from .error import Error
from .request import Request
from .response import Response
from .route import Route
from .router import Router


class App:
    """The base class for a Cosmo app."""

    def __init__(
        self, host: str, port: int, cors: bool = True, use_uvloop: bool = True
    ):
        self.host: str = host
        self.port: int = port
        self.cors = cors
        self.sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket.setdefaulttimeout(2)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if use_uvloop:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.routes = {}
        self.errors = {
            500: Error("text/plain", "Internal Server Error"),
            404: Error("text/plain", "Not Found"),
            405: Error("text/plain", "Method Not Allowed"),
            400: Error("text/plain", "Bad Request"),
        }
        self.default_headers = (
            {"Access-Control-Allow-Origin": "*", "server": "cosmo"}
            if self.cors
            else {"server": "cosmo"}
        )

    def throw_error(self, conn, error_code: int):
        error = self.errors.get(error_code, None)
        if error is None:
            raise ValueError(f"Error code {error_code} not found")
        base = f"HTTP/1.0 {error_code} {error}\r\nContent-Type: {error.content_type}\r\nContent-Length: {len(error)+2}\r\n"
        for key in self.default_headers.keys():
            base += f"{key}: {self.default_headers[key]}\r\n"
        base += f"\r\n{error.content}\r\n"
        conn.sendall(base.encode())
        return

    async def recv_headers(self, conn: socket.socket):
        """Coroutine to receive headers asynchronously."""
        headers = bytes()
        while True:
            try:
                piece = conn.recv(1024)
            except:
                return
            headers += piece
            if len(piece) < 1024:
                return headers

    async def send_resp(self, conn: socket.socket, route: Route, request: Request):
        """Coroutine to send response asynchronously."""
        conn.sendall(await route._create_response(request))
        conn.close()

    def route(self, path: str, content_type: str = "text/html", method: str = "GET"):
        """Decorator to define a new route."""

        def decorator(func):
            r = Route(path, method, content_type, func)
            self.routes[path] = r
            return r

        return decorator

    def import_router(self, router: Router):
        """Imports a router from another file."""
        for path in router.export_routes().keys():
            self.routes[path] = router.export_routes()[path]

    def static(self, file_path: str, file_type: str):
        """Defines a static file."""

        async def serve_file(request: Request):
            headers = {"accept-ranges": "bytes"}
            with open(file_path, "rb") as f:
                content = f.read()
            headers["content-length"] = f"{len(content)}"
            return Response(content, headers)

        r = Route(f"/static/{file_path.split('/')[-1]}", "GET", file_type, serve_file)
        self.routes[f"/static/{file_path.split('/')[-1]}"] = r
        return r

    def set_error(self, error_code: int, content_type: str, content: str):
        self.errors[error_code] = Error(content_type, content)
        return

    async def _parse_headers(self, request: str):
        """Parses HTTP headers."""
        headers = request.split("\n")
        http_header = headers[0]
        del headers[0]
        for i in headers:
            index = headers.index(i)
            i = i.replace("\r", "")  # Remove \r
            headers[index] = i
        while True:
            try:
                headers.remove("")
            except ValueError:
                break
        headers = {i.split(":")[0]: i.split(":")[1] for i in headers}
        return http_header, headers

    async def _new_connection(self, conn: socket.socket, addr: tuple):
        """Connection handler."""
        headers = await self.recv_headers(conn)
        if headers is None:
            conn.close()
            logger.debug(
                f"Closed connection from {addr[0]} as no headers were received"
            )
            return
        try:
            headers = headers.decode()
        except:
            self.throw_error(conn, 400)
            logger.error(f"{addr[0]} send an invalid request")
            return
        try:
            http_header, headers = await self._parse_headers(headers)
        except:
            self.throw_error(conn, 400)
            logger.error(f"{addr[0]} sent an invalid request")
            return
        try:
            method = http_header.split()[0]
        except:
            self.throw_error(conn, 400)
            logger.error(f"{addr[0]} sent an invalid request")
            return
        try:
            routename = http_header.split()[1].split("?")[0]
        except:
            self.throw_error(conn, 400)
            logger.error(f"{addr[0]} sent an invalid request")
            return
        if routename[-1] == "/" and len(routename) != 1:
            routename = list(routename)
            del routename[-1]
            routename = "".join(routename)
        try:
            flags = http_header.split()[1].split("?")[1]
            flags = [[i[0], i[1]] for i in [i.split("=") for i in flags.split("&")]]
            flags = {i[0]: i[1] for i in flags}
        except IndexError:
            flags = None
        r = Request(method, headers, addr[0], flags)
        route = self.routes.get(routename, None)
        if route is None:
            self.throw_error(conn, 404)
            logger.error(
                f"Request from {addr[0]} attempted to access a resource that does not exist"
            )
            return
        for header in self.default_headers:
            route.headers[header] = self.default_headers[header]
        if route.method != method:
            self.throw_error(conn, 405)
            logger.error(
                f"Request from {addr[0]} attempted to access a resource using an incorrect HTTP method"
            )
            return
        else:
            return await self.send_resp(conn, route, r)

    def serve(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        logger.debug(f"Listening on {self.host}:{self.port}")
        while True:
            conn, addr = self.sock.accept()
            asyncio.run(self._new_connection(conn, addr))
