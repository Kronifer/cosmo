from cosmo import App, Request, Response

app = App("0.0.0.0", 8080)


@app.route("/", "text/html")
def index(request: Request):
    headers = {"x-custom-header": "custom", "x-poggers": "true"}
    content = "<h1>Custom Headers: </h1>\n<ul>"
    for header in headers.keys():
        content += f"<li>{header}: {headers[header]}</li>\n"
    content += "</ul>"
    return Response(content, headers)


app.serve()
