"""
Misc utilities.
"""
import os
import pathlib

VERSION = "1.5.1"
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
