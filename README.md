# Cosmo

Cosmo is a multithreaded python webserver that I'm developing in my spare time. Cosmo utilizes a TCP socket to send and receive data.

## Benchmarking

![Connections Handled per Second](https://user-images.githubusercontent.com/44979306/191119603-e9b97cb1-b8dc-4cf0-8bf3-2a927dac8dac.png)

## Examples

### Simple Server

```py
from cosmo import App, Request, Response

app = App("0.0.0.0", 8080)

@app.route("/", "text/html")
async def index(request: Request):
    return Response(f"<h1>{request.address}</h1>")

app.serve()
```

### Using Custom Headers

```py
from cosmo import App, Request, Response

app = App("0.0.0.0", 8080)

@app.route("/", "text/html")
async def index(request: Request):
    headers = {"x-custom-header": "custom"}
    content = "<h1>Custom Headers: </h1>\n<ul>"
    for header in headers.keys():
        content += f"<li>{header}: {headers[header]}</li>\n"
    content += "</ul>"
    return Response(content, headers)

app.serve()
```

### Returning an HTML Page

```py
from cosmo import App, html_page, Request, Response

app = App("0.0.0.0", 8080)

@app.route("/", "text/html")
async def index(request: Request):
    return Response(html_page("path/to/page.html"))

app.serve()
```

### Using Routes from a different file

In `router.py`:
```py
from cosmo import Request, Response, Router

router = Router()

@router.route("/")
async def index():
    return Response("<h1>Hi</h1>")
```

In `app.py`:
```py
from cosmo import App, Request, Response

from router import router

app = App("0.0.0.0", 8080)

app.import_router(router)

app.serve()
```

## Docs

Coming soon...
