"""
A request represents a client wanting to get a resource from the server.

This is automatically passed into your app route when an appropriate path is recieved.
"""
import json
from http import cookies
import urllib.parse as uparse
from io import BytesIO

from werkzeug import formparser
from werkzeug.datastructures import Headers, MultiDict, OrderedMultiDict
from werkzeug.http import parse_options_header

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

    :ivar args: The arguments from the query string, parsed out.
    :ivar form: The form data for the request. If the request was JSON, this is automatically parsed out.
    :ivar values: THe arguments and the form combined.

    :ivar source: The source IP of the request.
    """

    def __init__(self):
        """
        Creates a new request.

        The request is probably useless right now, but the HTTP parser will then go on to set the right attributes on
        it.
        """
        # Empty values.
        self.method = ""

        # This differs from path/query because it's the full `/a/b/?c=d`.
        # This is then urlsplit into a path and query string in _parse_path.
        self.full_path = b""

        self.path = ""
        self.query = ""
        self.version = ""

        # Empty body, as this isn't known until it's passed in.
        self.body = ""

        self.cookies = cookies.SimpleCookie()

        # We use a Headers object here as it serves our purposes the best.
        self.headers = Headers()

        # Args, values, and forms are OrderedMultiDicts.
        # So are files.
        self.args = OrderedMultiDict()
        self._form = OrderedMultiDict()
        self.values = OrderedMultiDict()
        self.files = OrderedMultiDict()

        # Protocol-specific data.
        self.ip = ""
        self.port = 0

        # Extra values, for hooks.
        self.extra = {}

        self.should_keep_alive = False

    @property
    def source(self):
        """
        :return: A :class:`tuple` containing the IP address and port.
        """
        return self.ip, self.port

    @property
    def form(self) -> dict:
        """
        Returns the form data for the specified request.
        JSON forms are lazy loaded. This means that parsing is done in the first call to `.form`, rather than when
        the request is created.
        """
        if self._form:
            return self._form
        # Parse JSON, otherwise.
        if self.headers.get("Content-Type") == "application/json":
            self._form = json.loads(self.body)
            self.values.update(self._form if self._form else {})
        return self._form

    def _parse_path(self):
        """
        urlsplits the full path.
        """
        split = uparse.urlsplit(self.full_path.decode())
        self.path = split.path
        self.query = split.query

    def _parse_query(self):
        """
        Parses the query string, and updates `args` with it as appropriate.
        """
        new_args = uparse.parse_qs(self.query)
        # Unpack the urlparsed arguments.
        for name, value in new_args.items():
            if len(value) == 1:
                self.args[name] = value[0]
            elif len(value) == 0:
                self.args[name] = None
            else:
                self.args[name] = value

    def _parse_body(self):
        """
        Parses the body data.
        """
        if self.headers.get("Content-Type") != "application/json":
            # Parse the form data out.
            f_parser = formparser.FormDataParser()

            # Wrap the body in a BytesIO.
            body = BytesIO(self.body.encode())

            # The headers can't be directly passed into Werkzeug.
            # Instead, we have to get a the custom content type, then pass in some fake WSGI options.
            mimetype, c_t_args = parse_options_header(self.headers.get("Content-Type"))

            if mimetype:
                # We have a valid mimetype.
                # This is good!
                # Now parse the body.

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

                data = f_parser.parse(body,
                                      mimetype,
                                      content_length,
                                      options=env
                                      )

                # Extract the new data from the form parser.
                self._form.update(data[1])
                self.files.update(data[2])

    def parse_all(self):
        """
        Called when all data is parsed.

        This tells the request to re-parse everything based off of the raw data.

        This is an internal method.

        .. versionadded:: 1.9
        """
        # Call _parse_path to parse the path.
        self._parse_path()
        # Call _parse_query to parse the query string.
        self._parse_query()
        # Call _parse_body to parse the body.
        self._parse_body()

        # Load cookies.
        cookie_header = self.headers.get_all("Cookie")
        for c in cookie_header:
            self.cookies.load(c)
