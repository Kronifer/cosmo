from typing import Optional


class Request:
    """A class representing an HTTP request."""

    def __init__(
        self,
        method: str,
        headers: dict,
        address: str,
        url_flags: Optional[dict] = None,
        body: Optional[str] = None,
    ):
        self.method = method
        self.headers = headers
        self.address = address
        self.url_flags = url_flags
        self.body = body
