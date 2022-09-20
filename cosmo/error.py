class Error:
    def __init__(self, content_type: str, content: str):
        self.content_type = content_type
        self.content = content
