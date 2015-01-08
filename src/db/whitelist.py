"""
Defines functions that perform whitelist-related database queries.
"""

import db
import errors


### QUERIES ###

# GET WHITELIST ENTRIES

@db.with_connection
def get_active_whitelist_entries(connection):
    """Fetches the whitelist entries that are currently active from the database."""
    return db.common.get_active_rules_by_type(connection, 'WHITELIST')


# ADD WHITELIST ENTRY

@db.with_connection
def add_whitelist_entry(connection, address, user, comment):
    """Adds a whitelist entry for the given address to the database."""
    check_for_conflicting_blacklist_entries(connection, address)
    check_for_existing_whitelist_entries(connection, address)
    new_id, entry = db.common.add_rule_simple(connection, 'WHITELIST', address, None, user, comment)
    overlapping_whitelist_entries = get_overlapping_whitelist_entries(connection, address, new_id)
    return entry, overlapping_whitelist_entries


# CANCEL WHITELIST ENTRIES

@db.with_connection
def cancel_whitelist_entries(connection, address, user, comment):
    """Cancels all whitelist entries for the given address."""
    canceled_whitelist_entries = db.common.cancel_rule_simple(connection, 'WHITELIST', address, user, comment)
    if not canceled_whitelist_entries:
        raise AddressNotWhitelisted(address=address)
    overlapping_whitelist_entries = get_overlapping_whitelist_entries(connection, address)
    return canceled_whitelist_entries, overlapping_whitelist_entries


class AddressNotWhitelisted(errors.NothingToDo):
    message_template = 'The address {address} isn\'t actually whitelisted.'


# EXISTING WHITELIST ENTRIES

def check_for_existing_whitelist_entries(connection, address):
    """Raises `AddressAlreadyWhitelisted` if there's already a whitelist entry for the given exact address."""
    existing_whitelist_entries = get_existing_whitelist_entries_for_address(connection, address)
    if any(existing_whitelist_entries):
        raise AddressAlreadyWhitelisted(address=address, existing_whitelist_entries=existing_whitelist_entries)


def get_existing_whitelist_entries_for_address(connection, address):
    """Fetches existing whitelist entries for the given exact address."""
    query = GET_EXISTING_WHITELIST_ENTRIES_QUERY
    parameters = {'address': address}
    return db.execute_query(connection, query, parameters, db.common.dict_from_rule_row)


GET_EXISTING_WHITELIST_ENTRIES_QUERY = """
    SELECT 'ACTIVE' AS br_status,
           br_address,
           br_created,
           br_created_by,
           br_creation_comment
      FROM __SCHEMA__.blocking_rule
     WHERE br_type = 'WHITELIST'
       AND br_nullification_type IS NULL
       AND br_address = %(address)s;
"""

class AddressAlreadyWhitelisted(errors.NothingToDo):
    message_template = 'The address {address} is already whitelisted.'
    parameters_to_add_to_response = ['existing_whitelist_entries']


# OVERLAPPING WHITELIST ENTRIES

@db.with_connection
def get_overlapping_whitelist_entries(connection, address, excluded_id=-1):
    """Returns all active whitelist entries that are have at least one IP address in common with the given address."""
    return db.common.get_overlapping_active_rules_by_type(connection, 'WHITELIST', address, excluded_id)


# CONFLICTING BLACKLIST ENTRIES

def check_for_conflicting_blacklist_entries(connection, address):
    """Raises `AddressCannotBeWhitelisted` if there is a blacklist entry that overlaps with the given address."""
    conflicting_blacklist_entries = db.blacklist.get_overlapping_blacklist_entries(connection, address)
    if any(conflicting_blacklist_entries):
        raise AddressCannotBeWhitelisted(address=address, conflicting_blacklist_entries=conflicting_blacklist_entries)


class AddressCannotBeWhitelisted(errors.IntegrityError):
    message_template = 'The address {address} cannot be whitelisted because it\'s already blacklisted.'
    parameters_to_add_to_response = ['conflicting_blacklist_entries']

