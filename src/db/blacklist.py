"""
Defines functions that perform blacklist-related database queries.
"""

import db
import errors


### QUERIES ###

# GET BLACKLIST ENTRIES

@db.with_connection
def get_active_blacklist_entries(connection):
    """Fetches the blacklist entries that are currently active from the database."""
    return db.execute_query(connection, GET_ACTIVE_BLACKLIST_ENTRIES_QUERY, (), dict_from_active_blacklist_entry_row)


GET_ACTIVE_BLACKLIST_ENTRIES_QUERY = """
    SELECT be_address,
           be_end,
           be_created,
           be_created_by,
           be_creation_comment
      FROM zbi_data.blacklist_entry
     WHERE be_end > zbi_data.utcnow()
       AND be_nullification_type IS NULL;
"""

# ADD BLACKLIST ENTRY

@db.with_connection
def add_blacklist_entry(connection, address, duration, user, comment):
    """Adds a blacklist entry for the given address to the database."""
    check_for_conflicting_whitelist_entries(connection, address)
    check_for_existing_longer_blacklist_entries(connection, address, duration)
    new_id, entry = add_blacklist_entry_simple(connection, address, duration, user, comment)
    superseded_blacklist_entries = supersede_shorter_blacklist_entries(connection, address, duration, user, new_id)
    overlapping_blacklist_entries = get_overlapping_blacklist_entries(connection, address, new_id)
    return entry, superseded_blacklist_entries, overlapping_blacklist_entries


def add_blacklist_entry_simple(connection, address, duration, user, comment):
    """Creates the actual blacklist entry and returns it ID and a dict describing it."""
    duration_type, duration_value = duration
    query = durationify(ADD_BLACKLIST_ENTRY_QUERY, duration_type)
    parameters = {'address': address, 'duration': duration_value, 'user': user, 'comment': comment}
    row = db.execute_query(connection, query, parameters)[0]
    return row.be_id, dict_from_active_blacklist_entry_row(row)


ADD_BLACKLIST_ENTRY_QUERY = """
    INSERT INTO zbi_data.blacklist_entry
                (be_address,
                 be_end,
                 be_created_by,
                 be_creation_comment)
         VALUES (%(address)s,
                 {duration_snippet},
                 %(user)s,
                 %(comment)s)
      RETURNING be_id,
                be_address,
                be_end,
                be_created,
                be_created_by,
                be_creation_comment;
"""

# CANCEL BLACKLIST ENTRIES

@db.with_connection
def cancel_blacklist_entry(connection, address, user, comment):
    """Cancels all blacklist entries for the given address."""
    canceled_blacklist_entries = cancel_blacklist_entry_simple(connection, address, user, comment)
    if not canceled_blacklist_entries:
        raise AddressNotBlacklisted(address=address)
    overlapping_blacklist_entries = get_overlapping_blacklist_entries(connection, address)
    return canceled_blacklist_entries, overlapping_blacklist_entries


def cancel_blacklist_entry_simple(connection, address, user, comment):
    """Performs the actual cancelation of the blacklist entries for the given address."""
    query = CANCEL_BLACKLIST_ENTRIES
    parameters = {'address': address, 'user': user, 'comment': comment}
    return db.execute_query(connection, query, parameters, dict_from_canceled_blacklist_entry_row)


CANCEL_BLACKLIST_ENTRIES = """
       UPDATE zbi_data.blacklist_entry
          SET be_nullified = zbi_data.utcnow(),
              be_nullified_by = %(user)s,
              be_nullification_type = 'CANCELED',
              be_nullification_comment = %(comment)s
        WHERE be_address = %(address)s
          AND be_end > zbi_data.utcnow()
          AND be_nullification_type IS NULL
    RETURNING be_address,
              be_end,
              be_created,
              be_created_by,
              be_creation_comment,
              be_nullified,
              be_nullified_by,
              be_nullification_comment;
"""

class AddressNotBlacklisted(errors.NothingToDo):
    message_template = 'The address {address} isn\'t actually blacklisted.'


# EXISTING BLACKLIST ENTRIES

def check_for_existing_longer_blacklist_entries(connection, address, duration):
    """Raises `AddressAlreadyBlacklisted` if there's a longer-lasting blacklist entry for the given exact address."""
    existing_blacklist_entries = get_existing_longer_blacklist_entries(connection, address, duration)
    if any(existing_blacklist_entries):
        raise AddressAlreadyBlacklisted(address=address, existing_blacklist_entries=existing_blacklist_entries)


def get_existing_longer_blacklist_entries(connection, address, duration):
    """Fetches longer-lasting blacklist entries for the given exact address."""
    duration_type, duration_value = duration
    query = durationify(GET_EXISTING_LONGER_BLACKLIST_ENTRIES_QUERY, duration_type)
    parameters = {'address': address, 'duration': duration_value}
    return db.execute_query(connection, query, parameters, dict_from_active_blacklist_entry_row)


GET_EXISTING_LONGER_BLACKLIST_ENTRIES_QUERY = """
    SELECT be_address,
           be_end,
           be_created,
           be_created_by,
           be_creation_comment
      FROM zbi_data.blacklist_entry
     WHERE be_address = %(address)s
       AND be_end >= {duration_snippet}
       AND be_nullification_type IS NULL;
"""

class AddressAlreadyBlacklisted(errors.NothingToDo):
    message_template = 'The address {address} is already blacklisted for a period that exceeds the requested period.'
    parameters_to_add_to_response = ['existing_blacklist_entries']


# OVERLAPPING BLACKLIST ENTRIES

@db.with_connection
def get_overlapping_blacklist_entries(connection, address, excluded_id=-1):
    """Returns all active blacklist entries that are have at least one IP address in common with the given address."""
    query = GET_OVERLAPPING_BLACKLIST_ENTRIES_QUERY
    parameters = {'address': address, 'excluded_id': excluded_id}
    return db.execute_query(connection, query, parameters, dict_from_active_blacklist_entry_row)


GET_OVERLAPPING_BLACKLIST_ENTRIES_QUERY = """
    SELECT be_address,
           be_end,
           be_created,
           be_created_by,
           be_creation_comment
      FROM zbi_data.blacklist_entry
     WHERE be_end > zbi_data.utcnow()
       AND be_nullification_type IS NULL
       AND (be_address >> %(address)s OR be_address <<= %(address)s)
       AND be_id != %(excluded_id)s;
"""

# SUPERSEDE BLACKLIST ENTRIES

def supersede_shorter_blacklist_entries(connection, address, duration, user, superseding_id):
    """Marks existing shorter blacklist entries for the given exact address as superseded and returns those entries."""
    duration_type, duration_value = duration
    query = durationify(SUPERSEDE_SHORTER_BLACKLIST_ENTRIES_QUERY, duration_type)
    parameters = {'address': address, 'duration': duration_value, 'user': user, 'superseding_id': superseding_id}
    return db.execute_query(connection, query, parameters, dict_from_superseded_blacklist_entry_row)


SUPERSEDE_SHORTER_BLACKLIST_ENTRIES_QUERY = """
       UPDATE zbi_data.blacklist_entry
          SET be_nullified = zbi_data.utcnow(),
              be_nullified_by = %(user)s,
              be_nullification_type = 'SUPERSEDED'
        WHERE be_address = %(address)s
          AND be_end > zbi_data.utcnow()
          AND be_end < {duration_snippet}
          AND be_nullification_type IS NULL
          AND be_id != %(superseding_id)s
    RETURNING be_address,
              be_end,
              be_created,
              be_created_by,
              be_creation_comment,
              be_nullified,
              be_nullified_by;
"""

# CONFLICTING WHITELIST ENTRIES

def check_for_conflicting_whitelist_entries(connection, address):
    """Raises `AddressCannotBeBlacklisted` if there is a whitelist entry that overlaps with the given address."""
    conflicting_whitelist_entries = db.whitelist.get_overlapping_whitelist_entries(connection, address)
    if any(conflicting_whitelist_entries):
        raise AddressCannotBeBlacklisted(address=address, conflicting_whitelist_entries=conflicting_whitelist_entries)


class AddressCannotBeBlacklisted(errors.IntegrityError):
    message_template = 'The address {address} cannot be blacklisted because it\'s already whitelisted.'
    note_template = 'The System team can specify that certain IP addresses cannot be blacklisted by explicitely ' \
        'whitelisting them. The whitelist entries listed under "conflicting_whitelist_entries" prevent the IP ' \
        'address {address} from being blacklisted.'
    parameters_to_add_to_response = ['conflicting_whitelist_entries']


### FORMATTING RESULTS ###

def dict_from_active_blacklist_entry_row(row):
    return {
        'address': row.be_address,
        'status': 'ACTIVE',
        'end': row.be_end,
        'created': {
            'at': row.be_created,
            'by': row.be_created_by,
            'comment': row.be_creation_comment,
        },
    }


def dict_from_superseded_blacklist_entry_row(row):
    return {
        'address': row.be_address,
        'status': 'SUPERSEDED',
        'end': row.be_end,
        'created': {
            'at': row.be_created,
            'by': row.be_created_by,
            'comment': row.be_creation_comment,
        },
        'nullified': {
            'at': row.be_nullified,
            'by': row.be_nullified_by,
        },
    }

def dict_from_canceled_blacklist_entry_row(row):
    return {
        'address': row.be_address,
        'status': 'CANCELED',
        'end': row.be_end,
        'created': {
            'at': row.be_created,
            'by': row.be_created_by,
            'comment': row.be_creation_comment,
        },
        'nullified': {
            'at': row.be_nullified,
            'by': row.be_nullified_by,
            'comment': row.be_nullification_comment,
        },
    }


### GENERATING QUERIES ###

def durationify(query, duration_type):
    """Given a query with a `{duration_snippet}` placeholder, inserts the appropriate SQL snippet for the duration."""
    return query.format(duration_snippet=DURATION_QUERY_SNIPPETS[duration_type])


DURATION_QUERY_SNIPPETS = {
    'for': 'zbi_data.utcnow() + %(duration)s::interval',
    'until': '%(duration)s AT TIME ZONE \'UTC\'',
}

