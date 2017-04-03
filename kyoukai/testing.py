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
    """
    A context manager that is returned from :meth:`~.TestKyoukai.testing_bp`. When entered, this will produce a new
    Blueprint object, that is then set onto the test application as the root blueprint.

    After exiting, it will automatically restore the old root Blueprint onto the application, allowing complete
    isolation of individual test routes away from eachother.
    """
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

    @classmethod
    def wrap_existing_app(cls, other_app: Kyoukai, base_context: Context = None):
        """
        Wraps an existing app in a test frame.

        This allows easy usage of writing unit tests:

        .. code:: python

            # main.py
            kyk = Kyoukai("my_app")

            # test.py
            testing = TestKyoukai.wrap_existing_app(other_app)
            # use testing as you would normally

        :param other_app: The application object to wrap.
            Internally, this creates a new instance of ourselves, then sets the ``process_request`` 
            of the subclass to the copied object.

            This means whenever ``inject_request`` is called, it will use the old app's 
            process_request to run with,
            which will use the environment of the previous instance.

            Of course, if the old app has any side effects upon process_request, these side effects 
            will happen when the testing application runs as well, as the old app is completely 
            copied over.

        :param base_context: The base context to use for this.
        """
        new_object = cls("test_app", base_context=base_context)
        new_object.original_app = other_app
        new_object.process_request = other_app.process_request

        return new_object

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
