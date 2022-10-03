import traceback
from dataclasses import dataclass
from typing import Coroutine

from loguru import logger

from .request import Request


@dataclass
class Subroute:
    content_type: str
    function: Coroutine


class Route:
    """A class representing a route in a Cosmo app."""

    def __init__(self, path: str, method: str, content_type: str, function: Coroutine):
        self.path = path
        self.method = method.upper()
        self.content_type = content_type
        self.functions = {
            "GET": None,
            "POST": None,
            "HEAD": None,
            "PUT": None,
            "DELETE": None,
            "CONNECT": None,
            "OPTIONS": None,
            "TRACE": None,
            "PATCH": None,
        }
        self.functions[method] = Subroute(content_type, function)
        self.default_headers = {}

    async def _create_response(self, request: Request):
        try:
            method = request.method.upper()
            subroute = self.functions.get(method, None)
            if subroute is None:
                return None
            headers_dict = {"Content-Type": subroute.content_type}
            content = await subroute.function(request)
            headers_dict["Content-Length"] = len(str(content.content)) + 2
            if content.headers is not None:
                for header in content.headers:
                    headers_dict[header] = content.headers[header]
            headers = ""
            for header in self.default_headers.keys():
                headers += f"{header}: {self.default_headers[header]}\r\n"
            for header in headers_dict.keys():
                headers += f"{header}: {headers_dict[header]}\r\n"
            headers += "\r\n"
            if type(content.content) is bytes:
                return (
                    b"HTTP/1.0 200 OK\r\n"
                    + bytes(headers, encoding="utf-8")
                    + content.content
                )
            else:
                return f"HTTP/1.0 200 OK\r\n{headers}{content.content}\r\n".encode()
        except Exception as e:
            logger.critical(
                f"Traceback encountered while sending response: {traceback.format_exc(e.__traceback__)}"
            )
            return "HTTP/1.0 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error"
