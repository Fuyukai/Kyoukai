"""
Class that handles logins.
"""
import typing

import functools

import asyncio

from kyokai import Kyokai, Request
from kyokai.context import HTTPRequestContext
from kyokai.response import redirect, Response

try:
    import itsdangerous
except ImportError:
    raise ImportError("itsdangerous is not installed - cannot use session extension")


class SessionUser(object):
    """
    This is a stub class, that is used for KyoukaiSession.

    You can override this class and use it with KyoukaiSession.
    """
    def __init__(self):
        """
        The only attribute that is required here is `self.id`.
        """
        self.id = None


class KyoukaiSession(object):
    """
    A KyoukaiSession object provides a few useful methods for handling client logins.

    The class takes a callable, which will then be called to get a user upon a request.
    The callable must take a HTTPRequestContext, or other suitable class.

    This user will be passed in to your route, as the second argument.

    To require login on a route, decorate the route with `@sess.login_required`, for example:

    ```python
    @app.route("/")
    @session.login_required
    async def index(ctx: HTTPRequestContext, user: User):
        return "You are " + repr(user)
    ```

    If the user is not logged in, then it will redirect them to `redirect_uri`. This can be passed as the second param.

    This ext is Flask-like in terms of handling the application object - you can either pass it as the last item of
    the args, or call `init_app` later to initialize it.

    To login a user, return `session.login(id, redirect_uri="/")`, which will return a response that logs in the
    specified ID, and redirects them.
    """
    def __init__(self, user_f, redirect_uri: str="/login", app: Kyokai=None):
        """
        Create a new KyoukaiSession object.
        """

        self._callable_f = user_f
        self.redirect_uri = redirect_uri

        self.secret_key = b""
        self.signer = None

        if app:
            self.init_app(app)

    def init_app(self, app: Kyokai):
        """
        Loads the secret key from the config.
        """
        try:
            self.secret_key = app.config["secret_key"].encode()
        except KeyError:
            raise Exception("You must set a secret key in `config.yml` for sessions to work.")

        self.signer = itsdangerous.Signer(self.secret_key)

    def _get_id(self, request: Request):
        """
        Checks a request for the cookie headers.
        """
        cook = request.cookies.get("KySess")
        if not cook:
            return None
        # Load, and unsign.
        try:
            id = self.signer.unsign(cook)
        except itsdangerous.BadSignature:
            return None
        else:
            return id

    def login_required(self, func):
        """
        Decorator for checking if the login is correct.
        """
        @functools.wraps(func)
        async def _login_required_fake_func(ctx: HTTPRequestContext, *args):
            """
            You will never see this.

            Enforces login.
            """
            id = self._get_id(ctx.request)
            if not id:
                return redirect(self.redirect_uri)
            # Get the user object.
            if asyncio.iscoroutine(self._callable_f):
                # Don't know why, but ok
                u = await self._callable_f
            elif asyncio.iscoroutinefunction(self._callable_f):
                u = await self._callable_f(id)
            else:
                u = self._callable_f(id)
            # Await the underlying function.
            return await func(ctx, u, *args)

        return _login_required_fake_func

    def login(self, id, redirect_uri="/"):
        """
        Logs in a user, and returns a Response.
        """
        r = redirect(redirect_uri)
        r.cookies["KySess"] = self.signer.sign(id)
        return r