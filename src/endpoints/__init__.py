"""
Provides some generic utility functions for defining JSON endpoints.
"""

import flask
import functools
import inspect
import ipaddress

import context
import errors
import permissions


### ENDPOINT DECORATOR ###

def endpoint(route, method, required_role):
    """
    A decorator that marks the decorated function as a JSON endpoint that is exposed for requests at the given route
    for the given method.

    If the decorated function receives an argument named `address`, the value of that argument is converted into a
    `ipaddress.IPv4Network` or `ipaddress.IPv6Network` instance, as appropriate, before being passed through to the
    decorated function. If the value cannot be converted, an appropriate error is raised and the decorated function
    isn't called.

    Also, ensures that the user is logged in and has the appropriate role before calling the decorated function.
    If the decorated function receives an argument named `address`, that address refers to a network containing
    two or more IP addresses, and `'network-' + required_role` is a valid role, the decorator checks that the user
    has that role. Otherwise, the decorator checks that the user has `required_role`. The `apps/blockip/` prefix
    needs to be omitted from the role name in all cases.
    """

    def decorator(f):

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            argument_dict = inspect.getcallargs(f, *args, **kwargs)

            if 'address' in argument_dict:
                address = parse_address(argument_dict['address'])
                argument_dict['address'] = address
                permissions.check_authorization(required_role, address.num_addresses > 1)
            else:
                permissions.check_authorization(required_role, False)

            return f(**argument_dict)

        return context.app.route(route, methods=[method])(wrapper)

    return decorator


def parse_address(address):
    """Parses the given IP address into a `ipaddress.IPv{4,6}Network` object. Wrap expected errors."""
    try:
        return ipaddress.ip_network(address, strict=True)
    except ValueError as e:
        if 'has host bits set' in str(e):
            raise HostBitsSet(address=address)
        elif 'does not appear to be an IPv4 or IPv6 network' in str(e):
            raise MalformedAddress(address=address)
        else:
            raise


class HostBitsSet(errors.RequestError):
    message_template = 'The IP address "{address}" has host bits set.'


class MalformedAddress(errors.RequestError):
    message_template = 'The parameter "{address}" is not a valid IP address.'


### EXTRACT REQUEST DATA ###

def get_user_name():
    """Returns the LDAP name of the user making the request."""
    authorization = flask.request.authorization
    if authorization:
        return authorization.username
    else:
        return 'nobody'


def get_comment():
    """Returns the `comment` form parameter of current request. Raises `MissingComment` if the parameter is missing."""
    comment = flask.request.form.get('comment', '').strip()
    if comment:
        return comment
    else:
        raise endpoints.errors.MissingComment()


def get_duration():
    """
    Returns a tuple `(duration_type, duration_value)`, where `duration_vale` is the value of the `for` or `until`
    form parameter from the current request, and `duration_type` is the name of the parameter that was used.

    Returns `('for', DEFAULT_BLACKLIST_DURATION)` if the request has neither a `for` not an `until` parameter. Raises
    `MultipleDurations` if the request has both parameters. Does not raise an error if either parameter has
    an invalid value.
    """
    for_value = flask.request.form.get('for', '').strip()
    until_value = flask.request.form.get('until', '').strip()

    if for_value and until_value:
        raise RequestWithMultipleDurations(for_value=for_value, until_value=until_value)
    elif for_value:
        return 'for', for_value
    elif until_value:
        return 'until', until_value
    else:
        return 'for', DEFAULT_BLACKLIST_DURATION


# ERRORS

class MissingComment(errors.RequestError):
    message = 'The request does not contain a comment that explains the purpose of the operation.'
    note = 'The comment is specified as a form parameter named "comment".'


class MultipleDurations(errors.RequestError):
    message_template = 'The request specifies the duration using both "for" ("{for_value}") and "until" ("{until_value}").'


### CONVENIENCE IMPORTS ###

import endpoints.blacklist
import endpoints.whitelist
import endpoints.history

