import socket
import traceback
from loguru import logger
from threading import Thread
from .request import Request


class Route:
    def __init__(self, path: str, method: str, content_type: str, function: callable):
        self.path = path
        self.method = method
        self.content_type = content_type
        self.function = function

    def _create_response(self, request: Request):
        try:
            content = self.function(request)
            return f"HTTP/1.0 200 OK\nContent-Type: {self.content_type}\n\n{content}"
        except Exception as e:
            logger.critical(e.__traceback__)
            return "HTTP/1.0 500 Internal Server Error\nContent-Type: text/plain\n\nInternal Server Error"


class App:
    def __init__(self, host: str, port: int):
        self.host: str = host
        self.port: int = port
        self.sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.routes = {}

    def route(self, path: str, content_type: str = "text/html", method: str = "GET"):
        def decorator(func):
            r = Route(path, method, content_type, func)
            self.routes[path] = r
            return r

        logger.debug(f"Added new route: {path}")
        return decorator

    def _parse_headers(self, request: str):
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

    def _new_connection(self, conn, addr):
        logger.debug(f"New connection from {addr[0]}")
        headers = conn.recv(1024).decode()
        http_header, headers = self._parse_headers(headers)
        try:
            method = http_header.split()[0]
        except:
            conn.sendall(
                "HTTP/1.0 500 INTERNAL SERVER ERROR\nContent-Type: text/plain\n\n500 Internal Server Error".encode()
            )  # Strange edge case where the HTTP header is blank
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
            conn.sendall(
                "HTTP/1.0 404 Not Found\nContent-Type: text/plain\n\nNot Found".encode()
            )
            return
        else:
            return conn.sendall(route._create_response(r).encode())

    def serve(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        logger.debug(f"Listening on {self.host}:{self.port}")
        while True:
            conn, addr = self.sock.accept()
            Thread(target=self._new_connection, args=(conn, addr)).start()
