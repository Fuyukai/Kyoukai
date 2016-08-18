"""
Misc utilities.
"""
import os
import pathlib

from kyoukai.exc import HTTPException

VERSION = "1.8.1"
VERSIONT = tuple(map(int, VERSION.split('.')))


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

    :param response: The tuple or otherwise object that is being wrapped.
    :param response_cls: The Response class that is being used.
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
