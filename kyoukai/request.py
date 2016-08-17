"""
A request represents a client wanting to get a resource from the server.

This is automatically passed into your app route when an appropriate path is recieved.
"""
import json
import urllib.parse as uparse

from http import cookies

# Use the C parser if applicable.
from io import BytesIO

from werkzeug.datastructures import Accept, Authorization
from werkzeug.exceptions import ClientDisconnected

try:
    from http_parser.parser import HttpParser, IOrderedDict
except ImportError:
    from http_parser.pyparser import HttpParser, IOrderedDict

# Used for parsing headers.
from werkzeug import http, formparser

from kyoukai.exc import HTTPException


class Request(object):
    """
    A Request object.

    This should not be manually created. Instead, it is automatically provided by Kyokai.

    If you must create one, use :meth:`from_data` or :meth:`parse`.

    :ivar method: The HTTP method (GET, POST, PUT, etc)
    :ivar path: The full path of the request (``/api/v1/whatever``)
    :ivar headers: A :class:`IOrderedDict` representing the headers of the request.
    :ivar query: The raw query string (``a=b&c=d``)
    :ivar body: The raw body of the request.

    :ivar cookies: A :class:`cookies.SimpleCookie` containing the cookies of the request.
    :ivar raw_data: The raw data of the request.

    :ivar args: The arguments from the query string, parsed out.
    :ivar form: The form data for the request. If the request was JSON, this is automatically parsed out.
    :ivar values: THe arguments and the form combined.

    :ivar source: The source IP of the request.
    """

    def _parse(self, parser: HttpParser):
        """
        Parse the data.
        """
        self._parser = parser
        # Check if fully parsed before continuing.
        if not self.fully_parsed:
            # This is due to Kyoukai's buffer handling.
            # The request is called to parse multiple times.
            # Now, we just return if we're not 100% ready, meaning we won't get parsed needlessly.
            # This saves CPU and memory parsing stuff.
            return
        self.version = parser.get_version()
        self.method = parser.get_method()
        self.path = uparse.unquote(parser.get_path())
        self.headers = parser.get_headers()
        self.query = parser.get_query_string()
        self.body = parser.recv_body()

        self.cookies = cookies.SimpleCookie()
        self.cookies.load(self.headers.get("Cookie", "")) or {}

        self.raw_data = b""

        self.source = "0.0.0.0"

        self.extra = {}

        self.should_keep_alive = parser.should_keep_alive()

        self.version = parser.get_version()
        self.sversion = '.'.join(map(str, self.version))

        # urlparse out the items.
        _raw_args = uparse.parse_qs(self.query, keep_blank_values=True)
        # Reparse args
        self.args = IOrderedDict()
        for k, v in _raw_args.items():
            if len(v) == 1:
                self.args[k] = v[0]
            elif len(v) == 0:
                self.args[k] = None
            else:
                self.args[k] = v
        if self.headers.get("Content-Type") == "application/json":
            # Parse as JSON
            try:
                self.form = json.loads(self.body.decode())
            except json.JSONDecodeError:
                # Malformed JSON.
                raise HTTPException(400)

            # JSON bodies obviously don't have "native" upload support.
            # If you want to use a files key in the JSON, that's fine.
            self.files = {}

        else:
            # Parse the form data out.
            f_parser = formparser.FormDataParser()

            # Wrap the body in a BytesIO.
            body = BytesIO(self.body)

            # The headers can't be directly passed into Werkzeug.
            # Instead, we have to get a the custom content type, then pass in some fake WSGI options.
            mimetype, c_t_args = http.parse_options_header(self.headers.get("Content-Type"))

            if not mimetype:
                # Ok, no body.
                self.form = {}
                self.files = {}

            else:
                # Construct a fake WSGI environment.
                env = {"Content-Type": self.headers.get("Content-Type"),
                       "Content-Length": self.headers.get("Content-Length")}

                # Take the boundary out of the Content-Type, if applicable.
                boundary = c_t_args.get("boundary")
                if boundary is not None:
                    env["boundary"] = boundary

                # Get a good content length.
                content_length = self.headers.get("Content-Length")
                try:
                    content_length = int(content_length)
                except ValueError:
                    content_length = len(self.body)
                except TypeError:
                    # NoneType...
                    raise HTTPException(411)

                # Then, the form body itself is parsed.
                try:
                    data = f_parser.parse(body,
                                          mimetype,
                                          content_length,
                                          options=env
                                          )
                except ClientDisconnected:
                    # This means we were asked to parse before the request is fully made.
                    # This is a quirk of how Kyoukai handles buffers.
                    # We can just safely return here.
                    return

                # Extract the new data from the form parser.
                self.form = data[1]
                self.files = data[2]

        self.values = IOrderedDict(self.args)
        self.values.update(self.form if self.form else {})

    @property
    def accept(self) -> Accept:
        """
        Parses the Accept header
        :return: A new :class:`werkzeug.datastructures.Accept` object.
        """
        header = self.headers.get("Accept", "")
        return http.parse_accept_header(header)

    @property
    def auth(self) -> Authorization:
        """
        Parses the Authorization header.

        Note: this will return None in the case of an authorization header that is not Basic or Digest.
        :return: A new :class:`werkzeug.datastructures.Authorization` object.
        """
        header = self.headers.get("Authorization", "")
        return http.parse_authorization_header(header)

    @property
    def fully_parsed(self):
        if not hasattr(self, "_parser"):
            return False
        return self._parser.is_message_complete()

    def parse(self, data: bytes, source: str):
        """
        Parse the request.

        :param data: The HTTP request's raw data.
        :param source: The source address of the
        """
        parser = HttpParser()
        data_len = len(data)
        # Execute the parser.
        parsed_len = parser.execute(data, data_len)
        if parsed_len == 0 or (data_len != parsed_len and parser.is_message_complete()):
            raise HTTPException(400, "Bad Request")

        self.raw_data = data
        self.source = source

        # Parse the data.
        self._parse(parser)

    @classmethod
    def from_data(cls, data: bytes, source: str):
        """
        Create a new request from request data.

        Shortcut for:

        r = Request()
        r.parse(data, source)
        """
        # Create a new request.
        req = cls()

        req.parse(data, source)

        return req
