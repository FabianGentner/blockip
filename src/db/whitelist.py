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
    return db.execute_query(connection, GET_ACTIVE_WHITELIST_ENTRIES_QUERY, (), dict_from_active_whitelist_entry_row)


GET_ACTIVE_WHITELIST_ENTRIES_QUERY = """
    SELECT we_address,
           we_created,
           we_created_by,
           we_creation_comment
      FROM zbi_data.whitelist_entry
     WHERE we_nullification_type IS NULL;
"""


# ADD WHITELIST ENTRY

@db.with_connection
def add_whitelist_entry(connection, address, user, comment):
    """Adds a whitelist entry for the given address to the database."""
    check_for_conflicting_blacklist_entries(connection, address)
    check_for_existing_whitelist_entries(connection, address)
    new_id, entry = add_whitelist_entry_simple(connection, address, user, comment)
    overlapping_whitelist_entries = get_overlapping_whitelist_entries(connection, address, new_id)
    return entry, overlapping_whitelist_entries


def add_whitelist_entry_simple(connection, address, user, comment):
    """Creates the actual whitelist entry and returns its ID and a dict describing it."""
    query = ADD_WHITELIST_ENTRY_QUERY
    parameters = {'address': address, 'user': user, 'comment': comment}
    row = db.execute_query(connection, query, parameters)[0]
    return row.we_id, dict_from_active_whitelist_entry_row(row)


ADD_WHITELIST_ENTRY_QUERY = """
    INSERT INTO zbi_data.whitelist_entry
                (we_address,
                 we_created_by,
                 we_creation_comment)
         VALUES (%(address)s,
                 %(user)s,
                 %(comment)s)
      RETURNING we_id,
                we_address,
                we_created,
                we_created_by,
                we_creation_comment;
"""


# CANCEL WHITELIST ENTRIES

@db.with_connection
def cancel_whitelist_entries(connection, address, user, comment):
    """Cancels all whitelist entries for the given address."""
    canceled_whitelist_entries = cancel_whitelist_entries_simple(connection, address, user, comment)
    if not canceled_whitelist_entries:
        raise AddressNotWhitelisted(address=address)
    overlapping_whitelist_entries = get_overlapping_whitelist_entries(connection, address)
    return canceled_whitelist_entries, overlapping_whitelist_entries


def cancel_whitelist_entries_simple(connection, address, user, comment):
    """Performs the actual cancelation of the whitelist entries for the given address."""
    query = CANCEL_WHITELIST_ENTRIES
    parameters = {'address': address, 'user': user, 'comment': comment}
    return db.execute_query(connection, query, parameters, dict_from_canceled_whitelist_entry_row)


CANCEL_WHITELIST_ENTRIES = """
       UPDATE zbi_data.whitelist_entry
          SET we_nullified = zbi_data.utcnow(),
              we_nullified_by = %(user)s,
              we_nullification_type = 'CANCELED',
              we_nullification_comment = %(comment)s
        WHERE we_address = %(address)s
          AND we_nullification_type IS NULL
    RETURNING we_address,
              we_created,
              we_created_by,
              we_creation_comment,
              we_nullified,
              we_nullified_by,
              we_nullification_comment;
"""

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
    return db.execute_query(connection, query, parameters, dict_from_active_whitelist_entry_row)


GET_EXISTING_WHITELIST_ENTRIES_QUERY = """
    SELECT we_address,
           we_created,
           we_created_by,
           we_creation_comment
      FROM zbi_data.whitelist_entry
     WHERE we_address = %(address)s
       AND we_nullification_type IS NULL;
"""

class AddressAlreadyWhitelisted(errors.NothingToDo):
    message_template = 'The address {address} is already whitelisted.'
    parameters_to_add_to_response = ['existing_whitelist_entries']


# OVERLAPPING WHITELIST ENTRIES

@db.with_connection
def get_overlapping_whitelist_entries(connection, address, excluded_id=-1):
    """Returns all active whitelist entries that are have at least one IP address in common with the given address."""
    query = GET_OVERLAPPING_WHITELIST_ENTRIES_QUERY
    parameters = {'address': address, 'excluded_id': excluded_id}
    return db.execute_query(connection, query, parameters, dict_from_active_whitelist_entry_row)


GET_OVERLAPPING_WHITELIST_ENTRIES_QUERY = """
    SELECT we_address,
           we_created,
           we_created_by,
           we_creation_comment
      FROM zbi_data.whitelist_entry
     WHERE we_nullification_type IS NULL
       AND (we_address >> %(address)s OR we_address <<= %(address)s)
       AND we_id != %(excluded_id)s;
"""


# CONFLICTING BLACKLIST ENTRIES

def check_for_conflicting_blacklist_entries(connection, address):
    """Raises `AddressCannotBeWhitelisted` if there is a blacklist entry that overlaps with the given address."""
    conflicting_blacklist_entries = db.blacklist.get_overlapping_blacklist_entries(connection, address)
    if any(conflicting_blacklist_entries):
        raise AddressCannotBeWhitelisted(address=address, conflicting_blacklist_entries=conflicting_blacklist_entries)


class AddressCannotBeWhitelisted(errors.IntegrityError):
    message_template = 'The address {address} cannot be whitelisted because it\'s already blacklisted.'
    parameters_to_add_to_response = ['conflicting_blacklist_entries']


### FORMATTING RESULTS ###

def dict_from_active_whitelist_entry_row(row):
    return {
        'address': row.we_address,
        'status': 'ACTIVE',
        'created': {
            'at': row.we_created,
            'by': row.we_created_by,
            'comment': row.we_creation_comment,
        }
    }


def dict_from_canceled_whitelist_entry_row(row):
    return {
        'address': row.we_address,
        'status': 'CANCELED',
        'created': {
            'at': row.we_created,
            'by': row.we_created_by,
            'comment': row.we_creation_comment,
        },
        'nullified': {
            'at': row.we_nullified,
            'by': row.we_nullified_by,
            'comment': row.we_nullification_comment,
        },
    }

