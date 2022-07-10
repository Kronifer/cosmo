# Cosmo

Cosmo is a multithreaded python webserver that I'm developing in my spare time. Cosmo utilizes a TCP socket to send and receive data.

## Examples

### Simple Server

```py
from cosmo import App, Request, Response

app = App("0.0.0.0", 8080)

@app.route("/", "text/html")
def index(request: Request):
    return Response(f"<h1>{request.address}</h1>")

app.serve()
```

### Using Custom Headers

```py
from cosmo import App, Request, Response

app = App("0.0.0.0", 8080)

@app.route("/", "text/html")
def index(request: Request):
    headers = {"x-custom-header": "custom"}
    content = "<h1>Custom Headers: </h1>\n<ul>"
    for header in headers.keys():
        content += f"<li>{header}: {headers[header]}</li>\n"
    content += "</ul>"
    return Response(content, headers)

app.serve()
```

## Docs

Coming soon...