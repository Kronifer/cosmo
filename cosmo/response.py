from typing import Optional


class Response:
    """A class representing an HTTP response."""

    def __init__(self, content: str, headers: Optional[dict] = None):
        self.content = content
        self.headers = headers
