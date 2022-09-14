import traceback
from typing import Coroutine

from loguru import logger

from .request import Request


class Route:
    """A class representing a route in a Cosmo app."""

    def __init__(self, path: str, method: str, content_type: str, function: Coroutine):
        self.path = path
        self.method = method
        self.content_type = content_type
        self.function = function
        self.headers = {"Content-Type": self.content_type}

    async def _create_response(self, request: Request):
        try:
            content = await self.function(request)
            if content.headers is not None:
                for header in content.headers:
                    self.headers[header] = content.headers[header]
            headers = ""
            for header in self.headers.keys():
                headers += f"{header}: {self.headers[header]}\n"
            headers += "\n"
            if type(content.content) is bytes:
                return (
                    b"HTTP/1.0 200 OK\n"
                    + bytes(headers, encoding="utf-8")
                    + content.content
                )
            else:
                return f"HTTP/1.0 200 OK\n{headers}{content.content}".encode()
        except Exception as e:
            logger.critical(
                f"Traceback encountered while sending response: {traceback.format_exc(e.__traceback__)}"
            )
            return "HTTP/1.0 500 Internal Server Error\nContent-Type: text/plain\n\nInternal Server Error"
