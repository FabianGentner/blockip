"""
Defines the /blacklist endpoints.
"""

import flask

import context
import db
import endpoints


### CONFIGURATION ###

DEFAULT_BLACKLIST_DURATION = '8 hours'


### ENDPOINTS ###

@endpoints.endpoint('/blacklist', 'GET', 'reader')
def get_active_blacklist_entries():
    """List all active blacklist entries."""
    return flask.jsonify({'blacklist_entries': db.blacklist.get_active_blacklist_entries()})


@endpoints.endpoint('/blacklist/<path:address>', 'GET', 'reader')
def get_active_blacklist_entries_for_address(address):
    """List all active blacklist entries that overlap the given IP address."""
    return flask.jsonify({
        'blacklist_entries': db.blacklist.get_overlapping_blacklist_entries(address)
    })


@endpoints.endpoint('/blacklist/<path:address>', 'POST', 'blacklister')
def add_blacklist_entry(address):
    """Adds an IP address to the blacklist."""
    duration, duration_type = endpoints.get_duration()
    user_name, comment = endpoints.get_user_name(), endpoints.get_comment()
    results = db.blacklist.add_blacklist_entry(address, (duration, duration_type), user_name, comment)
    new_blacklist_entry, superseded_blacklist_entries, overlapping_blacklist_entries = results
    context.logger.info('Added %s to the blacklist.', address)
    response = flask.jsonify({
        'message': 'The IP address {address} has been added to the blacklist.'.format(address=address),
        'new_blacklist_entry': new_blacklist_entry,
        'superseded_blacklist_entries': superseded_blacklist_entries,
        'overlapping_blacklist_entries': overlapping_blacklist_entries,
    })
    response.status_code = 201
    return response


@endpoints.endpoint('/blacklist/<path:address>', 'DELETE', 'unblacklister')
def remove_blacklist_entry(address):
    """Removes an IP address from the blacklist."""
    result = db.blacklist.cancel_blacklist_entry(address, endpoints.get_user_name(), endpoints.get_comment())
    removed_blacklist_entries, overlapping_blacklist_entries = result
    context.logger.info('Removed %s from the blacklist.', address)
    but = ', but the overlapping blacklist entries listed below are still in effect'
    but = but if overlapping_blacklist_entries else ''
    return flask.jsonify({
        'message': 'The IP address {} has been removed from the blacklist{}.'.format(address, but),
        'removed_blacklist_entries': removed_blacklist_entries,
        'overlapping_blacklist_entries': overlapping_blacklist_entries,
    })

