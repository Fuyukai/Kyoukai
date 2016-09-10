"""
Kyoukai exceptions.

Contains the HTTPException class, which is used for immediately terminating out of a request handler with a HTTP error.
"""
import kyoukai


class HTTPException(Exception):
    """
    A basic HTTP error.

    This is used to quickly escape out of a function, by raising the appropriate HTTP Exception.

    .. code:: python

        if not some_condition:
            raise HTTPException(404)

    :ivar route: The route that this Exception was invoked from. Could be None.
    :ivar bp: The blueprint that this Exception was invoked from. Could also be None.
    :ivar body: The body to use for the exception. This is not recommended - use ``response`` instead.
    :ivar code: The response code to use for the exception. This is not recommended - use ``response`` instead.
    :ivar response: The :class:`Response` that should be emitted when this exception is caught.
    """

    def __init__(self, errcode, msg=None,
                 route=None):
        self.code = errcode

        self.body = msg

        self.route = route

        self.bp = None

        self.response = None

    @classmethod
    def new(cls, code=500, body="", headers=None, *,
            route=None, blueprint=None,
            response_cls=None):
        """
        Creates a new HTTPException.

        This is most often used when you need to return data from a request hook.

        .. code:: python

            rendered = ctx.app.renderer.render("errors/401.html")
            raise HTTPException.new(code=401, body=rendered)

        :param code: The HTTP status code to return.
        :param body: The body to use for the error.
        :param headers: The HTTP headers to send.
        :param route: The route this exception is from. This is usually filled in automatically - add this field to
            override it.
        :param blueprint: The blueprint this exception is from. This is usually filled in automatically - add this
            field to override it.
        :param response_cls: The response class to use to encode the embedded response.
        :return: A new :class:`HTTPException`.
        """
        if headers is None:
            headers = {}

        if response_cls is None:
            response_cls = kyoukai.Response

        r = response_cls(code=code, body=body)
        r.headers = headers

        exception = cls(errcode=code)
        exception.route = route
        exception.bp = blueprint
        exception.response = r

        return exception

    @property
    def blueprint(self) -> 'kyoukai.blueprints.Blueprint':
        """
        :returns: the Blueprint this exception bubbled from.
        """
        if self.route is not None:
            if self.route.bp is not None:
                return self.route.bp

        return self.bp

    def __repr__(self):
        return "HTTP {} {}".format(self.code, self.msg)


def abort(code: int):
    """
    Aborts the current request, raising a HTTPException.

    This is similar to Flask's abort method.

    This does not allow specifying custom bodies or anything similar. If you wish to do that, instantiate the
    exception yourself, or use :meth:`HTTPException.new`.

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
