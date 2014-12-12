"""
Defines the error handler, and a base class for exceptions raised by the blockip microservice that makes it easy to
provide the user with useful feedback in case of an error.
"""

import flask
import itertools
import psycopg2

import context
import utilities


### CONFIGURATION ###

# Attributes that the error handler will add to the JSON response if they are present on an exception instance.
# For best effect, do not use attributes that come alpabetically before 'message'. The keys in the JSON response are
# ordered alphabetically (because caching), and something like 'hint' coming before the message might be confusing.
ATTRIBUTES_TO_ADD_TO_RESPONSE = ['note', 'solution']


### EXCEPTION BASE CLASS ###

class ServiceError(Exception):
    """
    Base class for all exceptions raised by the blockip microservice.

    The error handler defined below will construct a JSON response from the exception. Subclasses should redefine the
    attributes `message_template` and `status_code`. The value of the former will be `format()`ed using the parameters
    passed to the exception's constructor to create the error message, and the value of the latter defines the HTTP
    status code that will be used for the response.

    If `status_code` is `401`, the user will be prompted for login information. If it is `200`, the response will not
    be marked as an error.

    There are two ways to add additional data to the response.

    First, if an instance of a subclass defines any of the attributes listed in `ATTRIBUTES_TO_ADD_TO_RESPONSE`, those
    attributes will be copied to the response. Also, If the instance defines any of those attributes with the suffix
    `_template`, the corresponding unsuffixed attributes will be added to the response with a value obtained by
    `format()`ing the value of the template attribute with the parameters passed to the exception's constructor.

    (Example: An instance `error` defines the attributes `note` and `solution_template`. The response will define the
    attribute `note` as `error.note`, and the attribute `solution` as `error.solution_template.format(**parameters)`,
    where `parameters` are the parameters passed to the constructor.)

    Second, if an instance of a subclass defines the attribute `parameters_to_add_to_response` as a collection of names,
    any parameter with a name in that sequence that is passed to the constructor will be added to the response as is.

    (Example: An instance defines the attribute `parameters_to_add_to_response` as `['conflicts']`. The response will
    define the attribute `conflicts` as `parameters['conflicts']`, where `parameters` are the parameters passed to the
    constructor.)
    """

    message = 'No message has been defined for this error.'
    status_code = 500
    parameters_to_add_to_response = []

    def __init__(self, **parameters):
        save_response_parameters(self, parameters)
        format_response_attribute_templates(self, parameters)
        self.perform_extra_initialization(**parameters)

    def perform_extra_initialization(self, **parameters):
        """Does nothing, but can be overridden by subclasses, should the need arise."""


class IntegrityError(ServiceError):
    """Base class for all exceptions that indicate that an operation would violate an integrity constraint."""
    status_code = 400


class RequestError(ServiceError):
    """Base class for all exceptions that indicate that the user sent a malformed request."""
    status_code = 400


class EnvironmentError(ServiceError):
    """Base class for all exceptions that indicate that there's something wrong with the application's environment."""
    status_code = 500


class NothingToDo(ServiceError):
    """Base class for all exceptions that indicate that the user's request does not require any action."""
    status_code = 200  # Note that this is not actually considered an error.


### ERROR HANDLER ###

@context.app.errorhandler(ServiceError)
def handle_service_error(error):
    """Creates the JSON response that is returned to the user if a ServiceError is raised."""
    log_error(error)
    contents = {'message': error.message}
    maybe_add_error_attribute_to_response(error, contents)
    add_extra_attributes_to_response(error, contents)
    response = flask.jsonify(contents)
    response.status_code = error.status_code
    maybe_add_authentication_request(error, response)
    return response


@context.app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Creates a JSON response that is returned if an error that isn't properly handled is raised."""
    log_error(error)
    response = flask.jsonify({
        'error': True,
        'message': 'There was an unexpected error.',
        'original_error': utilities.get_qualified_class_name(error),
        'original_message': str(error),
    })
    response.status_code = 500
    return response


### UTILITY FUNCTIONS ###

def save_response_parameters(error, parameters):
    """Saves any parameters passed to the given error's constructor that should be sent as part of the response."""
    for name in error.parameters_to_add_to_response:
        if name in parameters:
            setattr(error, name, parameters[name])


def format_response_attribute_templates(error, parameters):
    """Formats any templates for attributes that should be sent as part of the response for the given error."""
    for name in itertools.chain(['message'], ATTRIBUTES_TO_ADD_TO_RESPONSE):
        template = getattr(error, name + '_template', None)
        if template:
            setattr(error, name, template.format(**parameters))


def maybe_add_error_attribute_to_response(error, response_contents):
    """Adds the attribute `error` to the JSON response unless the exception does not actually indicate an error."""
    if error.status_code != 200:
        response_contents['error'] = True


def add_extra_attributes_to_response(error, response_contents):
    """Adds any extra attributes to the JSON response. See the documentation of `ServiceError` for details."""
    for attribute in itertools.chain(error.parameters_to_add_to_response, ATTRIBUTES_TO_ADD_TO_RESPONSE):
        value = getattr(error, attribute, None)
        if value:
            response_contents[attribute] = value


def maybe_add_authentication_request(error, response):
    """Asks the browser to ask the user for login information if the error's `status_code` is 401."""
    if error.status_code == 401:
        response.headers['WWW-Authenticate'] = 'Basic realm="You need to be logged in to access this resource."'


def log_error(error):
    """
    Logs the given error. Unexpected errors, and errors with status code 500 are logged as ERROR with stack trace,
    and user errors are logged as INFO without a stack trace.
    """
    status_code = getattr(error, 'status_code', -1)
    if status_code == 500:
        context.logger.exception('')
    elif status_code == -1:
        context.logger.exception('There was an unexpected error!')
    else:
        context.logger.info(error.message)

