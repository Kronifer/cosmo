import asyncio
import socket
import sys

import uvloop
from loguru import logger

from .request import Request
from .response import Response
from .route import Route

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class App:
    """The base class for a Cosmo app."""

    def __init__(self, host: str, port: int, cors: bool = True):
        self.host: str = host
        self.port: int = port
        self.cors = cors
        self.sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.routes = {}
        self.errors = {
            500: "Internal Server Error",
            404: "Not Found",
            405: "Method Not Allowed",
            400: "Bad Request",
        }
        self.default_headers = {"Access-Control-Allow-Origin": "*"} if self.cors else {}

    def throw_error(self, conn, error_code: int):
        error = self.errors.get(error_code, None)
        if error is None:
            raise ValueError(f"Error code {error_code} not found")
        base = f"HTTP/1.0 {error_code} {error}\nContent-Type: text/plain\n"
        for key in self.default_headers.keys():
            base += f"{key}: {self.default_headers[key]}\n"
        base += f"\n{error}\n\n"
        conn.sendall(base.encode())
        return

    def route(self, path: str, content_type: str = "text/html", method: str = "GET"):
        def decorator(func):
            r = Route(path, method, content_type, func)
            self.routes[path] = r
            return r

        logger.debug(f"Added new route: {path}")
        return decorator

    def static(self, file_path: str, file_type: str):
        async def serve_file(request: Request):
            headers = {"accept-ranges": "bytes"}
            with open(file_path, "rb") as f:
                content = f.read()
            headers["content-length"] = f"{len(content)}"
            return Response(content, headers)

        r = Route(f"/static/{file_path.split('/')[-1]}", "GET", file_type, serve_file)
        self.routes[f"/static/{file_path.split('/')[-1]}"] = r
        return r

    async def _parse_headers(self, request: str):
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

    async def _new_connection(self, conn, addr):
        logger.debug(f"New connection from {addr[0]}")
        headers = conn.recv(1024).decode()
        http_header, headers = await self._parse_headers(headers)
        try:
            method = http_header.split()[0]
        except:
            self.throw_error(conn, 400)
            logger.debug(f"Request from {addr[0]} was invalid")
            return
        routename = http_header.split()[1].split("?")[0]
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
            logger.debug(
                f"Request from {addr[0]} attempted to access a resource that does not exist"
            )
            return
        for header in self.default_headers:
            route.headers[header] = self.default_headers[header]
        if route.method != method:
            self.throw_error(conn, 405)
            logger.debug(
                f"Request from {addr[0]} attempted to use an invalid HTTP method to access a resource"
            )
            return
        else:
            return conn.sendall(await route._create_response(r))

    def serve(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        logger.debug(f"Listening on {self.host}:{self.port}")
        while True:
            conn, addr = self.sock.accept()
            asyncio.run(self._new_connection(conn, addr))
