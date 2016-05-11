"""
Misc utilities.
"""

VERSION = "0.2.0"
VERSIONT = tuple(map(int, VERSION.split('.')))

HTTP_CODES = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error"
}