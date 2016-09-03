"""
Kyoukai exceptions.
"""


class HTTPException(Exception):
    """
    A basic HTTP error.

    This is used to quickly escape out of a function, by raising the appropriate HTTP Exception.

    .. code:: python

        if not some_condition:
            raise HTTPException(404)
    """

    def __init__(self, errcode, msg=None,
                 route=None):
        self.code = errcode

        self.msg = msg

        self.route = route

        self.bp = None

    def __repr__(self):
        return "HTTP {} {}".format(self.code, self.msg)


def abort(code: int):
    """
    Aborts the current request, raising a HTTPException.

    This is similar to Flask's abort method.

    :param code: The code of the HTTPException to create.
    :raises: A :class:`HTTPException`.
    """
    raise HTTPException(code)


def exc_from(exc: Exception) -> HTTPException:
    """
    Creates a new HTTP 500 INTERNAL SERVER ERROR exception from a previous exception.

    You probably don't want to use this.

    :param exc: The exception to convert.
    :return: The new :class:`HTTPException`.
    """
    if isinstance(exc, HTTPException):
        return exc
    nwexc = HTTPException(500)
    # Set the context.
    nwexc.__context__ = exc
    return nwexc
