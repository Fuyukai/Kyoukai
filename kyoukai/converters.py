"""
Converters.

Defines how to convert arguments in a Route via the signature.
"""
import inspect
# Converters: A dict of `type` -> `callable` where callable takes one argument, the item to convert, and produces a new item of the type.
from kyoukai.exc import HTTPException
from kyoukai.context import HTTPRequestContext

_converters = {
    str: str,
    int: int
}


def add_converter(type_: type, cb):
    """
    Adds a converter to the conversions list/
    :param type_: The type to use as the annotation param.
    :param cb: A callable.
            Takes one parameter, which is the value of the argument.
            Should return a value of `type_`.

            This callable should raise a TypeError or a ValueError on failing to convert, at which point a 400 error will be raised.
            Anything else will cause a normal 500 error.
    """
    if not callable(cb):
        raise TypeError("cb should be callable")

    _converters[type_] = cb


def convert_args(coro, *args, bound=False):
    """
    Converts a the arguments of a function using it's signature.

    Will ignore `self` if bound is True.

    :param coro: The coroutine function to inspect for the signature.
    :param args: The arguments that are to be passed into the function.
            The first one should be the HTTPRequestContext; this is ignored.
    :param bound: If this route is bound to a View.
            Setting this will ignore the first parameter of the signature.
    """
    signature = inspect.signature(coro)
    params = signature.parameters

    if len(args) != len(params):
        raise IndexError("Arguments passed in were not the same length as {}'s function signature".format(coro))

    new_args = []

    for num, (name, value) in enumerate(params.items()):
        # If bound, just ignore the `self` param.
        if bound and num == 0:
            new_args.append(args[0])
            continue

        item = args[num]
        # Skip over the HTTPRequestContext.
        if isinstance(item, HTTPRequestContext):
            new_args.append(item)
            continue

        # Extract the annotation from the parameter.
        assert isinstance(value, inspect.Parameter)
        type_ = value.annotation
        if type_ not in _converters:
            # Just add the argument, without converting.
            new_args.append(item)
        else:
            _converter = _converters[type_]
            # Convert the arg.
            try:
                new_args.append(_converter(item))
            except (TypeError, ValueError):
                # Raise a bad request error.
                raise HTTPException(400)

    return new_args
