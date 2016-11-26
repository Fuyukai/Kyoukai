"""
A uWSGI adapter for Kyoukai.

This allows you to run Kyoukai with uWSGI as the web server. It translates the WSGI protocol into Kyoukai itself.
"""

import asyncio
import greenlet

import functools

import yaml
from asphalt.core import Context, ContainerComponent
from asphalt.core.component import component_types
from kyoukai.app import Kyoukai
from kyoukai.asphalt import KyoukaiComponent
from werkzeug.wrappers import Request, Response


def uwsgi_entry_point(func):
    """
    Wraps a function as a uWSGI entry point.

    This will automatically switch greenlets and set the result on a Future instance.
    :param func: The function to wrap.
    """

    @functools.wraps(func)
    async def _uwsgi_entry_point(self, current_greenlet: greenlet.greenlet, future: asyncio.Future,
                                 *args, **kwargs):
        """
        uWSGI wrapper entry point.
        """
        try:
            # Call the underlying wrapped function.
            result = await func(self, *args, **kwargs)
        except Exception as e:
            # Set the exception on the Future, allowing the web server to retrieve it.
            future.set_exception(e)
        else:
            # Set the result of the function on the Future.
            future.set_result(result)
        finally:
            # Switch back context.
            current_greenlet.switch()

    return _uwsgi_entry_point


class uWSGIAdapter(object):
    """
    The main adapter.

    To use uWSGI with Kyoukai, you must create an instance of this class with your app object, and point uWSGI to the
    ``wsgi_application`` method.

    .. code:: python

        from kyoukai.backends.uwsgi import uWSGIAdapter
        from myapp.app import kyk

        adapter = uWSGIAdapter(kyk)

    This adapter also supports using Asphalt .yml files.

    .. code:: python

        adapter = uWSGIAdapter.from_component(component, "config.yml")

    Then, your app will be running under uWSGI.
    """

    def __init__(self, app: Kyoukai, base_context: Context = None):
        """
        :param app: The application this class is running.
        """
        self.app = app
        self.app.finalize()

        # The base_context is passed into the app's handle function to create the HTTPContext.
        # As such, we need to store it here.
        self.base_context = base_context or Context()

        # The event loop.
        # This is set in run_application if it is None, otherwise it is set in `from_component`, to get the right
        # event loop.
        # This is used on the futures.
        self.loop = None

    @classmethod
    def from_asphalt_config(cls, filename: str) -> 'uWSGIAdapter':
        """
        Produces a new uWSGIAdapter from an Asphalt config file.

        :param filename: The full path to the config file.
        """
        with open(filename):
            config_data = yaml.load(filename)

        # Instantiate the root component
        try:
            component_config = config_data.pop('component')
        except KeyError:
            raise LookupError('missing configuration key: component') from None
        else:
            component = component_types.create_object(**component_config)  # type: ContainerComponent

        # Create a new Context.
        context = Context()

        # Run `start()` on the app.
        loop = asyncio.get_event_loop()
        # You best hope this doesn't block.
        loop.run_until_complete(component.start(context))

        # Find the KyoukaiComponent.
        for c in component.child_components:
            if isinstance(c, KyoukaiComponent):
                break
        else:
            raise TypeError("Could not find KyoukaiComponent in component list")

        # Create a new adapter.
        klass = cls(c.app, context)
        return klass

    @uwsgi_entry_point
    async def enter_kyoukai(self, request: Request) -> Response:
        """
        The main entry point to enter the app.

        This will be running inside the app greenlet.

        :param request: The request object to handle.
        :return: A response object to return.
        """
        result = await self.app.process_request(request, self.base_context)

        return result

    def run_application(self, environment: dict, start_response: callable):
        """
        Main entry point for the application.
        Called upon every request.

        :param environment: The WSGI environment for the application.
        :param start_response: A callable which is used by the Response.
        :return: A Werkzeug Response object.
        """
        if self.loop is None:
            self.loop = asyncio.get_event_loop()

        # Produce an event from the environment.
        request = Request(environment)

        # Create the future that is used for the result.
        # This is used so that WSGI can be implemented into asyncio.
        fut = asyncio.Future(loop=self.loop)

        # Get our current greenlet, which we pass into enter_kyoukai.
        g = greenlet.getcurrent()  # type: greenlet.greenlet

        # Make a task for the coroutine, and switch to the event loop context.
        self.loop.create_task(self.enter_kyoukai(g, fut, request))
        # bye-bye uwsgi! see you in a little while!
        g.parent.switch()

        # hello uwsgi!
        # we're back!

        # Get the result/exception from the future.
        # This will automatically re-raise. Kyoukai handles exceptions from user code, so this *shouldn't* kill
        # anything, only cause uWSGI to emit a 500.
        result = fut.result()  # type: Response

        # Write the response to the WSGI stream.
        return result(environment, start_response)
