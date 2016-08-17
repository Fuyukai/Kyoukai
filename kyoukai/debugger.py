"""
The Kyoukai debugger is a subset of the Werkzeug debugger.

It uses the Werkzeug debugger for the heavy lifting, whilst providing this as a wrapper around to ensure that it acts
properly inside the very different Kyoukai HTTP server.
"""
import mimetypes
import os
import typing

from werkzeug.debug import get_current_traceback
from werkzeug import debug

from kyoukai.context import HTTPRequestContext
from kyoukai.response import Response


class KyoukaiDebugger:
    """
    The main debugger class.

    You should never create this yourself. Only the application object should create this.
    """
    def __init__(self, app):
        self.app = app

        self.frames = {}
        self.tracebacks = {}

    def debug(self, ctx: HTTPRequestContext, exc: Exception) -> typing.Tuple[bool, Response]:
        """
        Produces debug output for the application in a new template.
        """
        if not self.app.debug:
            return


        # Check the request's params.
        params = ctx.request.args

        debugger = params.get("__debugger__")
        if debugger == "yes":
            command = params.get("cmd")
            # Switch based on the command.
            if command is None:
                return Response(code=404, body="404")
            elif command == "resource":
                # Send a resource down the line.
                filename = params.get("f")
                # Get the __file__ of the werkzeug debugger.
                wz_f = os.path.dirname(debug.__file__)
                filename = os.path.join(wz_f, 'shared', os.path.basename(filename))
                # Guess the content type from the filename.
                mimetype = mimetypes.guess_type(filename)[0] \
                    or 'application/octet-stream'
                if os.path.exists(filename):
                    with open(filename, 'rb') as f:
                        return False, Response(body=f.read(), code=200, headers={"Content-Type": mimetype})
                else:
                    return False, Response(body="404", code=404)
            else:
                # It's a console command.
                frame = self.frames.get(int(ctx.request.args.get('frm')))
                if frame is None:
                    return False, Response(body="404", code=404)
                # Run the console command inside the frame.
                result = frame.console.eval(command)
                return False, Response(body=result, code=200, headers={"Content-Type": "text/html"})
        else:
            # Get the traceback, now.
            traceback = get_current_traceback(
                skip=0, show_hidden_frames=True,
                ignore_system_exceptions=False)
            for frame in traceback.frames:
                self.frames[frame.id] = frame
            self.tracebacks[traceback.id] = traceback
            # Render the base page.
            body = traceback.render_full(evalex=True, evalex_trusted=True, )
            r = Response(code=500, body=body.encode(), headers={"X-XSS-Protection": "0"})
            return True, r
