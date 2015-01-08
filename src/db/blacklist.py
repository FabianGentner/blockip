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
    return db.common.get_active_rules_by_type(connection, 'BLACKLIST')


# ADD BLACKLIST ENTRY

@db.with_connection
def add_blacklist_entry(connection, address, duration, user, comment):
    """Adds a blacklist entry for the given address to the database."""
    check_for_conflicting_whitelist_entries(connection, address)
    check_for_existing_longer_blacklist_entries(connection, address, duration)
    new_id, entry = db.common.add_rule_simple(connection, 'BLACKLIST', address, duration, user, comment)
    superseded_blacklist_entries = supersede_shorter_blacklist_entries(connection, address, duration, user, new_id)
    overlapping_blacklist_entries = get_overlapping_blacklist_entries(connection, address, new_id)
    return entry, superseded_blacklist_entries, overlapping_blacklist_entries


# CANCEL BLACKLIST ENTRIES

@db.with_connection
def cancel_blacklist_entry(connection, address, user, comment):
    """Cancels all blacklist entries for the given address."""
    canceled_blacklist_entries = db.common.cancel_rule_simple(connection, 'BLACKLIST', address, user, comment)
    if not canceled_blacklist_entries:
        raise AddressNotBlacklisted(address=address)
    overlapping_blacklist_entries = get_overlapping_blacklist_entries(connection, address)
    return canceled_blacklist_entries, overlapping_blacklist_entries


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
    query = db.common.durationify(GET_EXISTING_LONGER_BLACKLIST_ENTRIES_QUERY, duration_type)
    parameters = {'address': address, 'duration': duration_value}
    return db.execute_query(connection, query, parameters, db.common.dict_from_rule_row)


GET_EXISTING_LONGER_BLACKLIST_ENTRIES_QUERY = """
    SELECT 'ACTIVE' AS br_status,
           br_address,
           br_end,
           br_created,
           br_created_by,
           br_creation_comment
      FROM __SCHEMA__.blocking_rule
     WHERE br_type = 'BLACKLIST'
       AND br_end > __SCHEMA__.utcnow()
       AND br_nullification_type IS NULL
       AND br_address = %(address)s
       AND br_end > {duration_snippet};
"""

class AddressAlreadyBlacklisted(errors.NothingToDo):
    message_template = 'The address {address} is already blacklisted for a period that exceeds the requested period.'
    parameters_to_add_to_response = ['existing_blacklist_entries']


# OVERLAPPING BLACKLIST ENTRIES

@db.with_connection
def get_overlapping_blacklist_entries(connection, address, excluded_id=-1):
    """Returns all active blacklist entries that are have at least one IP address in common with the given address."""
    return db.common.get_overlapping_active_rules_by_type(connection, 'BLACKLIST', address, excluded_id)


# SUPERSEDE BLACKLIST ENTRIES

def supersede_shorter_blacklist_entries(connection, address, duration, user, superseding_id):
    """Marks existing shorter blacklist entries for the given exact address as superseded and returns those entries."""
    duration_type, duration_value = duration
    query = db.common.durationify(SUPERSEDE_SHORTER_BLACKLIST_ENTRIES_QUERY, duration_type)
    parameters = {'address': address, 'duration': duration_value, 'user': user, 'superseding_id': superseding_id}
    return db.execute_query(connection, query, parameters, db.common.dict_from_rule_row)


SUPERSEDE_SHORTER_BLACKLIST_ENTRIES_QUERY = """
       UPDATE __SCHEMA__.blocking_rule
          SET br_nullified = __SCHEMA__.utcnow(),
              br_nullified_by = %(user)s,
              br_nullification_type = 'SUPERSEDED'
        WHERE br_type = 'BLACKLIST'
          AND br_end > __SCHEMA__.utcnow()
          AND br_nullification_type IS NULL
          AND br_address = %(address)s
          AND br_end < {duration_snippet}
          AND br_id != %(superseding_id)s
    RETURNING 'SUPERSEDED' AS br_status,
              br_address,
              br_end,
              br_created,
              br_created_by,
              br_creation_comment,
              br_nullified,
              br_nullified_by;
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


