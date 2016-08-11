"""
Converters.

Defines how to convert arguments in a Route via the signature.
"""
import inspect
# Converters: A dict of `type` -> `callable` where callable takes one argument, the item to convert, and produces a new item of the type.
from kyoukai.context import HTTPRequestContext

converters = {
    str: str,
    int: int
}


def convert(coro, *args, bound=False):
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
        if type_ not in converters:
            # Just add the argument, without converting.
            new_args.append(item)
        else:
            _converter = converters[type_]
            # Convert the arg.
            new_args.append(_converter(item))

    return new_args
