"""
Testing helpers for Kyoukai.
"""
from io import BytesIO

from asphalt.core import Context
from werkzeug.wrappers import Request, Response

from kyoukai.app import Kyoukai
from kyoukai.wsgi import to_wsgi_environment


class TestKyoukai(Kyoukai):
    """
    A special subclass that allows you to easily test your Kyoukai-based app.
    """
    def __init__(self, *args, base_context: Context=None, **kwargs):
        """
        :param base_context: The base context to use for all request testing.
        """
        super().__init__(*args, **kwargs)
        self.base_context = base_context

    async def inject_request(self, headers: dict, url: str, method: str="GET", body: str=None) -> Response:
        """
        Injects a request into the test client.

        This will automatically create the correct context.

        :param headers: The headers to use.
        :param body: The body to use.
        :param url: The URL to use.
        :param method: The method to use.
        :return: The result.
        """
        e = to_wsgi_environment(headers, method, url, http_version="1.1", body=BytesIO(body))
        e["SERVER_NAME"] = ""
        e["SERVER_PORT"] = ""

        r = Request(e)

        return await self.process_request(r, self.base_context)

