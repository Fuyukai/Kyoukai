"""
A gunicorn (green unicorn) based WSGI wrapper for Kyoukai.

This is similar to the uWSGI wrapper in that it implements a WSGI application for gunicorn to attach 
to. This only works with the gaiohttp worker, as otherwise the worker will have to block whilst 
the event loop  runs.

The gaiohttp worker allows asyncio execution of a coroutine (in our case, Kyoukai.process_request), 
so the asyncio event loop should work like normal whilst allowing gunicorn to take the brunt of 
the application work.
"""
import asyncio

import typing
from asphalt.core import Context
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import ClosingIterator

try:
    import gunicorn
    import aiohttp
except ImportError:
    raise RuntimeError("gunicorn and aiohttp must be installed for the gunicorn backend")

from asphalt.core import ContainerComponent
from asphalt.core.component import component_types

from kyoukai.app import Kyoukai
from kyoukai.asphalt import KyoukaiBaseComponent


class GunicornAdapter(object):
    """
    This class should be instantiated to create a gunicorn-compatible WSGI class.

    The instance method ``run_application`` should be set as the WSGI application, which calls your 
    app.
    For example:
    
    .. code-block:: python

        kyk = Kyoukai("my_app")
        runner = GunicornAdapter(kyk)

        application = runner.run_application

    """

    @classmethod
    def from_asphalt_config(cls, filename: str) -> 'GunicornAdapter':
        """
        Creates a new :class:`GunicornAdapter` from an Asphalt component config file.
        """
        from ruamel import yaml
        with open(filename):
            config_data = yaml.load(filename)

        # Instantiate the root component
        try:
            component_config = config_data.pop('component')
        except KeyError:
            raise LookupError('missing configuration key: component') from None
        else:
            component = component_types.create_object(
                **component_config)  # type: ContainerComponent

        # Create a new Context.
        context = Context()

        # Run `start()` on the app.
        loop = asyncio.get_event_loop()
        # You best hope this doesn't block.
        loop.run_until_complete(component.start(context))

        # Find the KyoukaiComponent.
        for c in component.child_components:
            if isinstance(c, KyoukaiBaseComponent):
                break
        else:
            raise TypeError("Could not find KyoukaiComponent in component list")

        del component

        # Create a new adapter.
        klass = cls(c.app, context)
        return klass

    def __init__(self, app: Kyoukai, base_context: Context = None):
        """
        :param app: The current application to run.
        :param base_context: The base context which is used as the parent to the \ 
            HTTPRequestContext created.
        """
        self.app = app

        self._base_context = base_context
        if not self._base_context:
            # Create an empty context as the default base context.
            self._base_context = Context()

    async def _run_application(self, environ, start_response) -> ClosingIterator:
        """
        Main entry point of the application.

        This is wrapped into a :class:`asyncio.Task` by ``run_application`` which is awaited on to 
        run the app itself.
        """
        if not self.app.root.finalized:
            self.app.root.finalize()
        request = self.app.request_class(environ=environ)

        response = await self.app.process_request(request, self._base_context)
        # Return the Response object which will be iterated over by Gunicorn.

        c = response(environ, start_response)  # type: ClosingIterator
        return c

    def run_application(self, environment: dict, start_response: typing.Callable) -> asyncio.Task:
        """
        Runs Kyoukai for the current request.

        This is **not** a coroutine - it returns a single item (a Task), which is awaited on to get 
        the response.

        :param environment: The WSGI environment to run this request with.
        :param start_response: A callable that can be used to start the response.
        :return: A new :class:`asyncio.Task` that can be awaited on to get a response from the \
        application.
        """
        is_async = environment.get("wsgi.async", False)

        if not is_async:
            # Damnit. Return a WSGI response that ells the user they're stupid.
            r = Response("<h1>Error</h1><br/>You did not use the <code>gaiohttp</code> "
                         "gunicorn worker. This is an "
                         "error! Please switch to the gaiohttp worker instead.")
            r.headers["Content-Type"] = "text/html; charset=utf-8"
            r.status_code = 500
            return r(environment, start_response)

        coro = self._run_application(environment, start_response)

        loop = asyncio.get_event_loop()
        t = loop.create_task(coro)

        environment["kyoukai.task"] = t

        return t
