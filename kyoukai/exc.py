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

    def __repr__(self):
        return "HTTP {} {}".format(self.code, self.msg)
