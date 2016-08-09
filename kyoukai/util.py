"""
Misc utilities.
"""
import os
import pathlib

from kyoukai.exc import HTTPException

VERSION = "1.5.4"
VERSIONT = tuple(map(int, VERSION.split('.')))

HTTP_CODES = {
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    410: "Gone",
    413: "Payload Too Large",
    429: "Too Many Requests",
    500: "Internal Server Error"
}


def static_filename(filename: str) -> str:
    """
    Naive static filename implementation, to allow serving static files.
    """
    built = ""
    p = pathlib.PurePath(filename)
    for part in p.parts:
        if part != "..":
            built += part + os.path.sep

    return built[:-1]


def wrap_response(response, response_cls=None):
    """
    Wrap up a response, if applicable.

    This allows Flask-like `return ""`.
    """
    # Import inside here to prevent circular imports.
    if response_cls is None:
        from kyoukai.response import Response
    else:
        Response = response_cls

    if response is None:
        r = Response(204, "", {})
    elif isinstance(response, tuple):
        if len(response) == 1:
            # Only body.
            r = Response(200, response[0], {})
        elif len(response) == 2:
            # Body and code.
            r = Response(response[1], response[0], {})
        elif len(response) == 3:
            # Body, code, headers.
            r = Response(response[1], response[0], response[2])
        else:
            # what
            raise HTTPException
    elif isinstance(response, Response):
        r = response
    else:

        r = Response(200, response, {})
    return r
