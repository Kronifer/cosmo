from typing import Optional


class Response:
    """A class representing an HTTP response."""

    def __init__(self, content: str, headers: Optional[dict] = None, resp_code: Optional[int] = 200):
        self.content = content
        self.headers = headers
        self.code = resp_code
