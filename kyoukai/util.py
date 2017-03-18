"""
Misc utilities for usage inside the framework.
"""
from werkzeug.wrappers import Response


def wrap_response(args, response_class: Response=Response) -> Response:
    """
    Wrap up a response, if applicable.
    This allows Flask-like `return "whatever"`.

    :param args: The arguments that are being wrapped.
    :param response_class: The Response class that is being used.
    """
    if not args:
        # Return a 204 NO CONTENT.
        return response_class("", status=204)

    if isinstance(args, tuple):
        # We enforce ``tuple`` here instead of any iterable.
        if len(args) == 1:
            # Only body, use 200 for the response code.
            return response_class(args[0], status=200)

        if len(args) == 2:
            # Body and status code.
            return response_class(args[0], status=args[1])

        if len(args) == 3:
            # Body, status code, and headers.
            return response_class(args[0], status=args[1], headers=args[2])

        raise TypeError("Cannot return more than 3 arguments from a view")

    if isinstance(args, response_class):
        # Return the bare response, unmodified.
        return args

    # Otherwise, wrap it in a response.
    return response_class(args)
