from typing import Optional


class Request:

    def __init__(self,
                 method: str,
                 headers: dict,
                 address: str,
                 url_flags: Optional[dict] = None):
        self.method = method
        self.headers = headers
        self.address = address
        self.url_flags = url_flags
