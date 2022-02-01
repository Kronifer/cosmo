# Cosmo

Cosmo is a multithreaded python webserver that I'm developing in my spare time. This README will be updated at a later date.

## Example Server

```py
from cosmo import App, Request

app = App("0.0.0.0", 8080)

@app.route("/", "text/html")
def index(request: Request):
    return f"<h1>{request.address}</h1>"

app.serve()
```