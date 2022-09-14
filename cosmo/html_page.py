class html_page:
    """A class representing an HTML page."""

    def __init__(self, file_path: str):
        with open(file_path, "r") as f:
            self.content = f.read()

    def __str__(self):
        return self.content
