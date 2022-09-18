from .route import Route


class Router:
    """Router class to add routes across Python files."""

    def __init__(self, route_root="/"):
        self.root = route_root
        self.routes = {}

    def route(self, path: str, content_type: str = "text/html", method: str = "GET"):
        def decorator(func):
            nonlocal path
            path = list(path)
            path[0] = f"{self.root}/"
            path = "".join(path)
            if path[-1] == "/":
                path = list(path)
                del path[-1]
                path = "".join(path)
            r = Route(path, method, content_type, func)
            self.routes[path] = r
            return r

        return decorator

    def export_routes(self):
        return self.routes
