"""
Testing application for Kyoukai.
"""
import asyncio
import collections
import typing

from asphalt.core import Context

from kyoukai import HTTPRequestContext
from kyoukai import Request
from kyoukai import Response
from kyoukai.app import Kyoukai


class TestProtocol:
    """
    A fake test protocol, that has a mock close and send method to emulate a real transport for the app.
    """
    def __init__(self, app: 'TestKyk'):
        self.app = app

        # Make a fake lock, for the Request lock.
        self.lock = asyncio.Lock()

    def handle_resp(self, response: Response):
        self.app._responses.put_nowait(response)

    def close(self):
        pass


class TestingKyk(Kyoukai):
    """
    A test application for Kyoukai.

    This has a few notable differences from a regular app:

     - The :meth:`TestKyk.feed_request` method that feeds a new request to be processed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._testing_protocol = TestProtocol(self)

        self._responses = asyncio.Queue()

    async def feed_request(self, data: typing.Union[str, Request]) -> Response:
        """
        Feeds a new Request object to the app.

        :param data: Either a string containing request data, or a raw Request object.
        :return: The Response object produced from `delegate_request`.
        """
        if isinstance(data, str):
            request = Request.from_data(data.encode(), "127.0.0.1")
        else:
            request = data

        # Create a new HTTPRequestContext.
        ctx = HTTPRequestContext(request, self, Context())

        # Delegate the request.
        await self.delegate_request(self._testing_protocol, ctx)
        # This should return None, as the queue was updated during delegate_request.
        return self._responses.get_nowait()

    def clean(self):
        """
        Cleans up the state of the responses Queue after a request.
        """
        self._responses._queue = collections.deque()


