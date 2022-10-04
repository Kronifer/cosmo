import asyncio
import socket
import ssl
import sys
from typing import Optional

from loguru import logger

from .error import Error
from .request import Request
from .response import Response
from .route import Route, Subroute
from .router import Router
from .ssl import SSL


class App:
    """The base class for a Cosmo app."""

    def __init__(
        self,
        host: str,
        port: int,
        cors: bool = True,
        use_uvloop: bool = True,
        ssl_cert: Optional[SSL] = None,
    ):
        self.host: str = host
        self.port: int = port
        self.cors = cors
        self.sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket.setdefaulttimeout(2)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if use_uvloop:
            import uvloop

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        if ssl_cert is not None:
            self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ctx.load_cert_chain(ssl_cert.cert_path, ssl_cert.key_path)
            self.sock = self.ctx.wrap_socket(self.sock, server_side=True)
            self.port = 443 if self.port == 80 else 8443
            logger.debug(f"Using HTTPS, switching port to {self.port}")
        self.routes = {}
        self.errors = {
            500: Error("text/plain", "Internal Server Error"),
            404: Error("text/plain", "Not Found"),
            405: Error("text/plain", "Method Not Allowed"),
            400: Error("text/plain", "Bad Request"),
        }
        self.error_names = {
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
        }
        self.default_headers = (
            {"Access-Control-Allow-Origin": "*", "server": "cosmo"}
            if self.cors
            else {"server": "cosmo"}
        )

    async def throw_error(self, conn, error_code: int):
        error = self.errors.get(error_code, None)
        if error is None:
            raise ValueError(f"Error code {error_code} not found")
        base = f"HTTP/1.0 {error_code} {self.error_names[error_code]}\r\nContent-Type: {error.content_type}\r\nContent-Length: {len(error.content)+2}\r\n"
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

    async def send_resp(
        self, conn: socket.socket, addr: tuple, route: Route, request: Request
    ):
        """Coroutine to send response asynchronously."""
        resp = await route._create_response(request)
        if resp is None:
            await self.throw_error(conn, 405)
            logger.error(
                f"Request from {addr[0]} attempted to access a resource with an invalid method"
            )
            return
        conn.sendall(resp)
        conn.close()

    def route(self, path: str, content_type: str = "text/html", method: str = "GET"):
        """Decorator to define a new route."""

        def decorator(func):
            if path in self.routes.keys():
                if self.routes[path].functions[method.upper()] is not None:
                    raise KeyError("Method Already Exists")
                self.routes[path].functions[method] = Subroute(content_type, func)
                return
            r = Route(path, method, content_type, func)
            self.routes[path] = r
            return r

        return decorator

    def import_router(self, router: Router):
        """Imports a router from another file."""
        for path in router.export_routes().keys():
            if path in self.routes.keys():
                if self.routes[path].functions[method.upper()] is not None:
                    raise KeyError("Method Already Exists")
                self.routes[path].functions[method] = Subroute(content_type, func)
                return
            self.routes[path] = router.export_routes()[path]

    def static(self, file_path: str, file_type: str):
        """Defines a static file."""

        async def serve_file(request: Request):
            headers = {"accept-ranges": "bytes"}
            with open(file_path, "rb") as f:
                content = f.read()
            headers["Content-Length"] = f"{len(content)}"
            return Response(content, headers)

        r = Route(f"/static/{file_path.split('/')[-1]}", "GET", file_type, serve_file)
        self.routes[f"/static/{file_path.split('/')[-1]}"] = r
        return r

    def set_error(self, error_code: int, content_type: str, content: str):
        self.errors[error_code] = Error(content_type, content)
        return

    async def _get_post_body(self, request: str):
        headers = request.split("\r\n")
        if headers.index("") != len(headers) - 1:
            body = "\r\n".join(headers[headers.index("") :])
            if body == "":
                body = None
            return body, headers.index("")
        else:
            return None

    async def _parse_headers(self, request: str, index: str):
        """Parses HTTP headers."""
        headers = request.split("\r\n")
        del headers[index:]
        http_header = headers[0]
        del headers[0]
        for i in headers:
            index = headers.index(i)
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
            await self.throw_error(conn, 400)
            logger.error(f"{addr[0]} send an invalid request")
            return
        try:
            body, index = await self._get_post_body(headers)
            http_header, headers = await self._parse_headers(headers, index)
        except:
            await self.throw_error(conn, 400)
            logger.error(f"{addr[0]} sent an invalid request")
            return
        try:
            method = http_header.split()[0]
        except:
            await self.throw_error(conn, 400)
            logger.error(f"{addr[0]} sent an invalid request")
            return
        try:
            routename = http_header.split()[1].split("?")[0]
        except:
            await self.throw_error(conn, 400)
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
        r = Request(method, headers, addr[0], flags, body)
        route = self.routes.get(routename, None)
        if route is None:
            await self.throw_error(conn, 404)
            logger.error(
                f"Request from {addr[0]} attempted to access a resource that does not exist"
            )
            return
        for header in self.default_headers:
            route.default_headers[header] = self.default_headers[header]
        return await self.send_resp(conn, addr, route, r)

    def serve(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        logger.debug(f"Listening on {self.host}:{self.port}")
        while True:
            conn, addr = self.sock.accept()
            asyncio.run(self._new_connection(conn, addr))
