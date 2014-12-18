import flask

import endpoints
import db


### ENDPOINTS ###

@endpoints.endpoint('/history/<path:address>', 'GET', 'history-reader')
def get_history_for_address(address):
    """List all active and inactive black- and whitelist entries that overlap the given IP address."""
    return flask.jsonify({
        'history': db.history.get_overlapping_entries(address)
    })

