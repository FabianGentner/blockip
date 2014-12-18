"""
Provides some generic utility functions for dealing with databases.
"""

import context
import functools
import ipaddress
import psycopg2
import psycopg2.errorcodes
import psycopg2.extensions
import psycopg2.extras
import re

import errors
import utilities


### CONNECTIONS ###

def with_connection(f):
    """
    A decorator that ensures that a psycopg2 connection is passed to the decorated function.

    If the first argument passed to the decorated function is a connection, the function is called as normal.
    Otherwise, a new connection is created, prepended to the positional arguments, and passed to the decorated
    function.

    That is, a decorated function `f(connection, p)` can be called by outside code as `f(p)`, but decorated functions
    can pass their connections to other decorated functions so that only one connection object will be created.
    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if args and is_connection(args[0]):
            return f(*args, **kwargs)
        else:
            try:
                with create_connection() as connection:
                    return f(connection, *args, **kwargs)
            except psycopg2.OperationalError as e:
                raise CannotTalkToDatabase(original_message=str(e))

    return wrapper


def is_connection(o):
    """Indicates whether the given object is a psycopg2 connection."""
    return isinstance(o, psycopg2._psycopg.connection)


def create_connection():
    """Creates a new psycopg2 connection using the settings from the configuration file."""
    return psycopg2.connect(
        host=context.settings.get('db', 'host'),
        database=context.settings.get('db', 'database'),
        user=context.settings.get('db', 'user'),
        password=context.settings.get('db', 'password'),
    )


### EXECUTING QUERIES ###

def execute_query(connection, query, parameters=(), mapper=utilities.identity):
    """
    Executes the given query with the given parameters using the given connection, maps the returned rows with the
    given mapper function, and returns the result.
    """
    with connection.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor) as cursor:
        context.logger.debug('Executing query\n%s\nwith parameters %s.', query, parameters)
        try:
            cursor.execute(query, parameters)
        except psycopg2.Error as e:
            raise wrap_expected_errors(e)
        return [mapper(row) for row in cursor.fetchall()]


### ERROR HANDLING ###

def wrap_expected_errors(e):
    """
    If the given `psycopg2.Error` is one of several expected errors, returns a custom exception for better error
    reporting. Otherwise, returns the error as is.

    Note that this will fail if the language for error messages is set to something other than English in the database,
    or if the PostgreSQL folks change the format of their error messages, but blockip will just fall back to more
    generic error reporting in that case, so this is still better than not trying.
    """
    return wrap_malformed_timestamp_error(e) \
        or wrap_malformed_interval_error(e) \
        or wrap_empty_duration_error(e) \
        or e


# PATTERNS

PATTERN_MALFORMED_TIMESTAMP = re.compile(r'invalid input syntax for type timestamp( with time zone)?: "(.*)"')
PATTERN_MALFORMED_INTERVAL = re.compile(r'invalid input syntax for type interval: "(.*)"')
PATTERN_SHORT_DURATION = re.compile(r'new row for relation "blocking_rule" violates check constraint "br_valid_duration"')


# WRAPPERS

def wrap_malformed_timestamp_error(e):
    """Returns a `MalformedTimestamp` exception if the given exception is due to a invalid timestamp value."""
    if e.pgcode == psycopg2.errorcodes.INVALID_DATETIME_FORMAT:
        match = PATTERN_MALFORMED_TIMESTAMP.search(str(e))
        if match:
            return MalformedTimestamp(timestamp=match.group(2))


def wrap_malformed_interval_error(e):
    """Returns a `MalformedInterval` exception if the given exception is due to a invalid interval value."""
    if e.pgcode == psycopg2.errorcodes.INVALID_DATETIME_FORMAT:
        match = PATTERN_MALFORMED_INTERVAL.search(str(e))
        if match:
            return MalformedInterval(interval=match.group(1))


def wrap_empty_duration_error(e):
    """Returns an `EmptyDuration` exception if the given exception is due to the duration being empty."""
    if e.pgcode == psycopg2.errorcodes.CHECK_VIOLATION:
        match = PATTERN_SHORT_DURATION.search(str(e))
        if match:
            return EmptyDuration()


# ERRORS

class MalformedTimestamp(errors.RequestError):
    message_template = "The value given for 'until' ('{timestamp}') is invalid."
    note = 'Legal values are all strings that PostgreSQL can parse as a timestamp with time zone that lies ' \
        'at least one minute in the future. Examples include "2014-11-14 16:03:00", "2014-11-14 17:03:00+01:00", ' \
        '"2014-11-14 17:03:00 CET", and "November 14, 2014 AD, at 17:03:00 (Europe/Berlin)" (except that those will ' \
        'be in the past by the time you read this).'


class MalformedInterval(errors.RequestError):
    message_template = "The value given for 'for' ('{interval}') is invalid."
    note = 'Legal values are all strings that PostgreSQL can parse as an interval with a (positive) length ' \
        'of at least one minute. Examples include "8h", "1 day", "2.5w", "1 year 1 day", and "P1Y2M3DT4H5M6S".'


class EmptyDuration(errors.RequestError):
    message = 'The time period the blacklist entry is to be active for is already over.'


class CannotTalkToDatabase(errors.EnvironmentError):
    message = 'There was an issue connecting to the database. Please contact the Database team.'
    parameters_to_add_to_response = ['original_message']


### REGISTER ADAPTERS ###

# Tell psycopg2 how to deal with `ipaddress` classes that are passed as parameters to queries.

def str_adapter(o):
    return psycopg2.extensions.QuotedString(str(o))


psycopg2.extensions.register_adapter(ipaddress.IPv4Network, str_adapter)
psycopg2.extensions.register_adapter(ipaddress.IPv6Network, str_adapter)


### CONVENIENCE IMPORTS ###

import db.common
import db.whitelist
import db.blacklist
import db.history

