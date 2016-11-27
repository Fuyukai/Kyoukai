"""
Testing helpers for Kyoukai.
"""
import random
from io import BytesIO

from asphalt.core import Context
from werkzeug.wrappers import Request, Response

from kyoukai.app import Kyoukai
from kyoukai.blueprint import Blueprint
from kyoukai.wsgi import to_wsgi_environment


class _TestingBpCtxManager(object):
    def __init__(self, app: 'TestKyoukai'):
        self.app = app

        self._old_root = self.app.root

    def __enter__(self) -> Blueprint:
        id = str(random.randint(0, 1000))
        name = "bp-{}".format(id)

        b = Blueprint(name)
        self.app._root_bp = b

        return b

    def __exit__(self, exc_type, exc_val, exc_tb):
        # reset the root blueprint
        del self.app._root_bp
        self.app._root_bp = self._old_root

        if exc_type:
            return False

        return True


class TestKyoukai(Kyoukai):
    """
    A special subclass that allows you to easily test your Kyoukai-based app.
    """

    def __init__(self, *args, base_context: Context = None, **kwargs):
        """
        :param base_context: The base context to use for all request testing.
        """
        super().__init__(*args, **kwargs)
        self.base_context = base_context

    def testing_bp(self) -> _TestingBpCtxManager:
        """
        Context handler that allows ``with TestKyoukai.testing_bp() as bp:``

        You can then register items onto this new root blueprint until __exit__, which will then destroy the blueprint.
        """
        return _TestingBpCtxManager(self)

    async def inject_request(self, headers: dict, url: str, method: str = "GET", body: str = None) -> Response:
        """
        Injects a request into the test client.

        This will automatically create the correct context.

        :param headers: The headers to use.
        :param body: The body to use.
        :param url: The URL to use.
        :param method: The method to use.
        :return: The result.
        """
        if body is not None:
            body = BytesIO(body.encode())

        e = to_wsgi_environment(headers, method, url, http_version="1.1", body=body)
        e["SERVER_NAME"] = ""
        e["SERVER_PORT"] = ""

        r = Request(e)

        # for testing blueprints, etc
        # slow but it's a test so oh well
        self.finalize()

        return await self.process_request(r, self.base_context)
