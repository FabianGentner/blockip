"""
Defines the /whitelist endpoints.
"""

import flask

import context
import db
import endpoints


### ENDPOINTS ###

@endpoints.endpoint('/whitelist', 'GET', 'reader')
def get_active_whitelist_entries():
    """List all active whitelist entries."""
    return flask.jsonify({'whitelist_entries': db.whitelist.get_active_whitelist_entries()})


@endpoints.endpoint('/whitelist/<path:address>', 'GET', 'reader')
def get_active_whitelist_entries_for_address(address):
    """List all active whitelist entries that overlap the given IP address."""
    return flask.jsonify({
        'whitelist_entries': db.whitelist.get_overlapping_whitelist_entries(address)
    })


@endpoints.endpoint('/whitelist/<path:address>', 'POST', 'whitelister')
def add_whitelist_entry(address):
    """Adds an IP address to the whitelist."""
    result = db.whitelist.add_whitelist_entry(address, endpoints.get_user_name(), endpoints.get_comment())
    new_whitelist_entry, overlapping_whitelist_entries = result
    context.logger.info('Added %s to the whitelist.', address)
    response = flask.jsonify({
        'message': 'The IP address {address} has been added to the whitelist.'.format(address=address),
        'new_whitelist_entry': new_whitelist_entry,
        'overlapping_whitelist_entries': overlapping_whitelist_entries,
    })
    response.status_code = 201
    return response


@endpoints.endpoint('/whitelist/<path:address>', 'DELETE', 'unwhitelister')
def remove_whitelist_entry(address):
    """Removes an IP address from the whitelist."""
    result = db.whitelist.cancel_whitelist_entries(address, endpoints.get_user_name(), endpoints.get_comment())
    removed_whitelist_entries, overlapping_whitelist_entries = result
    context.logger.info('Removed %s from the whitelist.', address)
    but = ', but the overlapping whitelist entries listed below are still in effect'
    but = but if overlapping_whitelist_entries else ''
    return flask.jsonify({
        'message': 'The IP address {} has been removed from the whitelist{}.'.format(address, but),
        'removed_whitelist_entries': removed_whitelist_entries,
        'overlapping_whitelist_entries': overlapping_whitelist_entries,
    })

