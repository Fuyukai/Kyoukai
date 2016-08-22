"""
Testing application for Kyoukai.
"""
import asyncio
import collections
import typing

from asphalt.core import Context
from kyoukai import KyoukaiProtocol

from kyoukai import Request
from kyoukai import Response
from kyoukai.app import Kyoukai


class TestProtocol(KyoukaiProtocol):
    """
    A fake test protocol, that has a mock close and send method to emulate a real transport for the app.
    """
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

        self._testing_protocol = TestProtocol(self, Context())

        self._responses = asyncio.Queue()

    async def feed_request(self, data: typing.Union[str, Request]) -> Response:
        """
        Feeds a new Request object to the app.

        :param data: Either a string containing request data, or a raw Request object.
        :return: The Response object produced from `delegate_request`.
        """
        if isinstance(data, str):
            data = data.replace("\n", "\r\n")
            if not data.endswith("\r\n\r\n"):
                data += "\r\n"
            data = data.encode()

        # Call data_received on the protocol.
        self._testing_protocol.parser.feed_data(data)
        try:
            await self._testing_protocol._wait()
        finally:
            self._testing_protocol._empty_state()

        return self._responses.get_nowait()

    def clean(self):
        """
        Cleans up the state of the responses Queue after a request.
        """
        self._responses._queue = collections.deque()


