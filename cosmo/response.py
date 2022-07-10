from typing import Optional


class Response:
    def __init__(self, content: str, headers: Optional[dict] = None):
        self.content = content
        self.headers = headers
