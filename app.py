#!/usr/bin/env python3
from cosmo import App, Request, Response

app = App("127.0.0.1", 8080)


@app.route("/", "text/plain")
async def index(request: Request):
    return Response(str(request.headers))


app.serve()
