"""
Provides the `requires` decorator, which can be used to verify that the user has the necessary permissions to access
a given resource.
"""

import dogpile.cache
import flask
import functools
import inspect
import itertools
import ldap3

import context
import errors
import utilities


### CONFIGURATION ###

ROLE_CACHE_EXPIRATION_TIME = 600  # seconds


### ROLES ###

ROLES = {
    'reader',
    'blacklister',
    'network-blacklister',
    'unblacklister',
    'network-unblacklister',
    'whitelister',
    'network-whitelister',
    'unwhitelister',
    'network-unwhitelister',
}


# Maps roles to a set of roles that role implies. Transitive, for no particular reason.
IMPLIED_ROLES = {
    'blacklister': {'reader'},
    'network-blacklister': {'reader', 'blacklister'},
    'unblacklister': {'reader'},
    'network-unblacklister': {'reader', 'unblacklister'},
    'whitelister': {'reader'},
    'network-whitelister': {'reader', 'whitelister'},
    'unwhitelister': {'reader'},
    'network-unwhitelister': {'reader', 'unwhitelister'},
}


### AUTHORIZATION ###

def check_authorization(role, for_network=False):
    """Raises NotAuthorized if the user isn't logged in or lacks the given role."""
    authorization = flask.request.authorization

    if authorization and authorization.username:
        check_permission(role, for_network)
    else:
        log_access_denied('They are not logged in.')
        raise NotLoggedIn()


def check_permission(role, for_network):
    """
    Raises NotAuthorized unless the user has the given role. If `for_network` is given, and the role exists with the
    `network-` prefix, checks for that role instead.
    """
    try:
        check_permission_unsafe(role, for_network)
    except ldap3.core.exceptions.LDAPException as e:
        raise CannotTalkToLDAP(original_message=str(e))


def check_permission_unsafe(role, for_network):
    """As `check_permission()`, but does not handle LDAP exceptions."""
    authorization = flask.request.authorization

    if for_network and 'range-' + role in ROLES:
        role = 'range-' + role

    if context.arguments.no_permission_checks:
        context.logger.debug('Skipped permission check for role %s.', role)
    elif role in get_roles(authorization.username, authorization.password):
        context.logger.info('Allowed user %s access to %s.', identify_user(), identify_resource())
    else:
        log_access_denied('They lack the role {role}'.format(role=role))
        raise InsufficientRights(use_name=authorization.username, role=role)


### GETTING ROLES ###

role_cache = dogpile.cache.make_region().configure('dogpile.cache.memory', expiration_time=ROLE_CACHE_EXPIRATION_TIME)

@role_cache.cache_on_arguments()
def get_roles(user_name, password):
    """Returns a set of the blockip roles of the user with the given credentials. May raise NotAuthorized."""
    context.logger.info('Connecting to LDAP to authenticate user %s.', identify_user(use_user_name=False))
    ldap_user = context.settings.get('ldap', 'user_name_template').format(user_name=user_name)
    with get_ldap_connection(ldap_user, password) as ldap_connection:
        roles_entries = search_for_roles(ldap_connection, user_name)
    role_names = extract_role_names(roles_entries)
    role_names = get_with_implied_roles(role_names)
    return role_names


def get_with_implied_roles(roles):
    """Returns a set of all roles that are in `roles` or are (directly or indirectly) implied by a role in `roles`."""
    result = set(roles)
    roles_to_check = list(roles)
    while roles_to_check:
        role = roles_to_check.pop(0)
        for implied_role in IMPLIED_ROLES.get(role, ()):
            if implied_role not in result:
                result.add(implied_role)
                roles_to_check.add(implied_role)
    return result


def get_ldap_connection(user_dn, password):
    """Returns an (open and bound) LDAP connection for the user with the given credentials."""
    try:
        print(user_dn, password)
        return ldap3.Connection(
            ldap3.Server(context.settings.get('ldap', 'host'), use_ssl=context.settings.getboolean('ldap', 'use_ssl')),
            user=user_dn,
            password=password,
            auto_bind=ldap3.AUTO_BIND_TLS_BEFORE_BIND,
            client_strategy=ldap3.STRATEGY_SYNC
        )
    except ldap3.core.exceptions.LDAPBindError:
        log_access_denied('They provided bad credentials.', use_user_name=False)
        raise BadCredentials()


def search_for_roles(ldap_connection, user_name):
    """Searches LDAP for the blockip roles of the user with the given name. Returns the unprocessed LDAP response."""
    ldap_connection.search(
            context.settings.get('ldap', 'role_search_base'),
            context.settings.get('ldap', 'role_search_filter_template').format(user_name=user_name),
            attributes=['cn'])
    return ldap_connection.response


def extract_role_names(response):
    """Given an LDAP response as returned by `search_for_roles()`, returns the names of the roles that were found."""
    return set(itertools.chain.from_iterable(item['attributes'].get('cn', ()) for item in response))


### ERRORS ###

class NotAuthorized(errors.ServiceError):
    """The base class for exceptions that indicate that the user is not authorized to access a given resource."""


class NotLoggedIn(NotAuthorized):
    """Raised if the user is not logged in. Will trigger a log in request."""
    message = 'You need to be logged in to use this service.'
    status_code = 401


class BadCredentials(NotAuthorized):
    """Raised if the user provides an invalid user name or password. Will trigger a log in request."""
    message = 'The user name and password you provided were not valid.'
    status_code = 401


class InsufficientRights(NotAuthorized):
    """Raised if the user lacks a role that is required to access a given resource."""
    status_code = 403

    def perform_preinitialization(self, **parameters):
        # context.settings is not yet available when the class is being created...
        message_template_template = 'You do not have the role {role_path}, which is required to access this resource.'
        role_path = context.settings.get('ldap', 'role_path_template', fallback='{role}')
        self.message_template = message_template_template.format(role_path=role_path)
        self.solution_template = context.settings.get('messages', 'missing_role_solution', fallback=None)


class CannotTalkToLDAP(errors.EnvironmentError):
    """Raised if there is some error when requesting data from LDAP."""
    message = 'There was an issue connecting to LDAP. Please contact the System team.'
    parameters_to_add_to_response = ['original_message']


### UTILITY FUNCTIONS ###

def log_access_denied(reason, use_user_name=True):
    """Logs the fact that the user has been denied access to a resource for the given reason at the given level."""
    context.logger.info('Denied user %s access to %s. %s', identify_user(use_user_name), identify_resource(), reason)


def identify_user(use_user_name=True):
    """Returns a string that identifies the user ("fgentner (192.0.2.1)", "192.0.2.1")."""
    if use_user_name and flask.request.authorization:
        return '{} ({})'.format(flask.request.authorization.username, flask.request.remote_addr)
    else:
        return flask.request.remote_addr


def identify_resource():
    """Returns a string that identifies the resource the user is accessing ("GET /blocks", "POST /blocks/192.0.2.1")."""
    return '{} {}'.format(flask.request.method, flask.request.path)

