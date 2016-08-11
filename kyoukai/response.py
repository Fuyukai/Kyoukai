"""
Module for a Response object.

A Response is returned by Routes when the underlying coroutine is done.
"""
import gzip
import http
import warnings

import sys

try:
    from http_parser.parser import IOrderedDict
except ImportError:
    from http_parser.pyparser import IOrderedDict

    warnings.warn("Using fallback Python HTTP parser - this will negatively affect performance.")

from . import util

try:
    import magic
except (ImportError, OSError):
    _has_magic = False
    warnings.warn("Cannot load libmagic - Cannot determine file types automatically...")
else:
    _has_magic = True

from email.utils import formatdate
from http.cookies import SimpleCookie
import urllib.parse as uparse


class Response(object):
    """
    A response is responsible (no pun intended) for delivering data to the client, again.

    The method :meth:`to_bytes` transforms this into a bytes response.

    :ivar code: The response code.
    :ivar cookies: The cookies to send down with the response.
    :ivar body: The string or bytes body of the request.
    :ivar headers: A dict of headers for the response.
    :ivar request: The request object this Response is handling.
            This is automatically set inside Kyoukai.
    """

    def __init__(self, code: int, body: str, headers: dict = None):
        """
        Create a new response.
        """
        self.code = code
        self.cookies = SimpleCookie()
        self.body = body
        self.headers = IOrderedDict(headers) if headers else IOrderedDict()

        self._should_gzip = False
        self._is_head = False

        self.request = None

    @property
    def gzip(self):
        """
        :return: If the request is to be gzip compressed.
        """
        return self._should_gzip

    @gzip.setter
    def gzip(self, value):
        self._should_gzip = value

    def _mimetype(self, body):
        """
        Calculates the mime type of the response, using libmagic.

        This is an **internal method**.
        """
        if _has_magic:
            mime = magic.from_buffer(body, mime=True)
            if mime:
                return mime.decode() if isinstance(mime, bytes) else mime
            else:
                return "empty"
        else:
            return "text/plain"

    def _recalculate_headers(self):
        """
        Override certain headers, like Content-Size.

        This is an **internal method**.
        """
        if not self._is_head:
            # The +2 is for the \r\n at the end.
            self.headers["Content-Length"] = len(self.body) + 2
        if 'Content-Type' not in self.headers:
            self.headers["Content-Type"] = self._mimetype(self.body) or "text/plain"

        # If it's gzip enabled, add the gzip header.
        if self._should_gzip:
            self.headers["Content-Encoding"] = "gzip"

        # Set cookies.
        self.headers["Date"] = formatdate()
        self.headers["Server"] = "Kyoukai/{} (see https://github.com/SunDwarf/Kyoukai)".format(util.VERSION)
        self.headers["X-Powered-By"] = "Kyoukai"

    def to_bytes(self):
        """
        Serialize a Response into :class:`bytes` to return and send to the client.

        :return: The encoded data for the response.
        """
        if self.request and self.request.fully_parsed:
            if self.request.method.lower() == "head":
                self._is_head = True
            version = ".".join(map(str, self.request.version))

            self.gzip = self.gzip and 'gzip' in self.request.headers.get("Accept-Encoding", "")
        else:
            version = "1.0"
            self.gzip = False

        if isinstance(self.body, str):
            self.body = self.body.encode()
        elif isinstance(self.body, bytes):
            pass
        else:
            self.body = str(self.body).encode()

        if self.gzip:
            if 'Content-Type' not in self.headers:
                self.headers["Content-Type"] = self._mimetype(self.body)
            self.body = gzip.compress(self.body, 5)

        # Re-calculate headers to update everything as appropriate.
        self._recalculate_headers()

        fmt = "HTTP/{version} {code} {msg}\r\n{headers}{cookies}\r\n"
        headers_fmt = ""
        # Calculate headers
        for name, val in self.headers.items():
            headers_fmt += "{}: {}\r\n".format(name, val)

        # Get the HTTP code.
        code = http.HTTPStatus(self.code).name.replace("_", " ")

        built = fmt.format(code=self.code, msg=code, headers=headers_fmt,
                           cookies=(self.cookies.output() + "\r\n") if len(self.cookies) else "",
                           version=version)

        # Encode the built string so far.
        built = built.encode()

        # Append the body, plus the terminator.
        built += self.body + b"\r\n"

        return built

    @classmethod
    def redirect(cls, location, code=302):
        """
        Creates a new Response that redirects to a specific location.

        :param location: The location to redirect to.
        :param code: The code (usually a 301 or 302) to add to the response.
        :return: A new :class:`Response` for the redirect.
        """
        # https://github.com/pallets/werkzeug/blob/master/werkzeug/utils.py#L373
        # response body used from Werkzeug
        #location = uparse.quote(location)

        res = cls(
            code=code,
            body=
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
            '<title>Redirecting...</title>\n'
            '<h1>Redirecting...</h1>\n'
            '<p>You should be redirected automatically to target URL: '
            '<a href="{location}">{location}</a>.  If not click the link.'.format(location=location),
            headers={"Location": location}
        )
        return res
