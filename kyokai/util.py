"""
Misc utilities.
"""
import os
import pathlib

VERSION = "1.3.0"
VERSIONT = tuple(map(int, VERSION.split('.')))

HTTP_CODES = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
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