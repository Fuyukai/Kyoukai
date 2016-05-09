"""
Kyokai exceptions.
"""


class HTTPException(Exception):
    """
    A basic HTTP error.

    Should not be created directly, only caught, or one of the subclasses caught.
    """
    def __init__(self, errcode, msg=None):
        self.errcode = errcode
        self.msg = msg

    def __repr__(self):
        # TODO: Add a lookup.
        return "HTTP {} {}".format(self.errcode, self.msg)


class HTTPClientException(Exception):
    """
    Raised when a client causes an error.
    """