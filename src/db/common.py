import db


# GET ACTIVE RULES

def get_active_rules_by_type(connection, type):
    """Fetches the blocking rules of the given type that are currently active from the database."""
    query = GET_ACTIVE_RULES_BY_TYPE_QUERY
    parameters = {'type': type}
    return db.execute_query(connection, query, parameters, dict_from_rule_row)


GET_ACTIVE_RULES_BY_TYPE_QUERY = """
      SELECT 'ACTIVE' AS br_status,
             br_address,
             br_end,
             br_created,
             br_created_by,
             br_creation_comment
        FROM zbi_data.blocking_rule
       WHERE br_type = %(type)s
         AND (br_end IS NULL OR br_end > zbi_data.utcnow())
         AND br_nullification_type IS NULL
    ORDER BY br_created ASC,
             br_id ASC;
"""


# ADD RULE

def add_rule_simple(connection, type, address, duration, user, comment):
    """Creates a blocking rule and returns it ID and a dict describing it."""
    duration_type, duration_value = duration or (None, None)
    query = durationify(ADD_RULE_QUERY, duration_type)
    parameters = {'type': type, 'address': address, 'duration': duration_value, 'user': user, 'comment': comment}
    row = db.execute_query(connection, query, parameters)[0]
    return row.br_id, dict_from_rule_row(row)


ADD_RULE_QUERY = """
    INSERT INTO zbi_data.blocking_rule
                (br_address,
                 br_type,
                 br_end,
                 br_created_by,
                 br_creation_comment)
         VALUES (%(address)s,
                 %(type)s,
                 {duration_snippet},
                 %(user)s,
                 %(comment)s)
      RETURNING br_id,
                'ACTIVE' AS br_status,
                br_address,
                br_end,
                br_created,
                br_created_by,
                br_creation_comment;
"""


# CANCEL RULE

def cancel_rule_simple(connection, type, address, user, comment):
    """Performs the actual cancelation of the whitelist entries for the given address."""
    query = CANCEL_RULE_QUERY
    parameters = {'type': type, 'address': address, 'user': user, 'comment': comment}
    return db.execute_query(connection, query, parameters, dict_from_rule_row)


CANCEL_RULE_QUERY = """
       UPDATE zbi_data.blocking_rule
          SET br_nullified = zbi_data.utcnow(),
              br_nullified_by = %(user)s,
              br_nullification_type = 'CANCELED',
              br_nullification_comment = %(comment)s
        WHERE br_type = %(type)s
          AND (br_end IS NULL OR br_end > zbi_data.utcnow())
          AND br_nullification_type IS NULL
          AND br_address = %(address)s
    RETURNING br_address,
              'CANCELED' AS br_status,
              br_end,
              br_created,
              br_created_by,
              br_creation_comment,
              br_nullified,
              br_nullified_by,
              br_nullification_comment;
"""


# GET OVERLAPPING ACTIVE RULES

@db.with_connection
def get_overlapping_active_rules_by_type(connection, type, address, excluded_id=-1):
    """Returns all active rules that have at least one IP address in common with the given address."""
    query = GET_OVERLAPPING_ACTIVE_RULES_BY_TYPE_QUERY
    parameters = {'type': type, 'address': address, 'excluded_id': excluded_id}
    return db.execute_query(connection, query, parameters, dict_from_rule_row)


GET_OVERLAPPING_ACTIVE_RULES_BY_TYPE_QUERY = """
    SELECT 'ACTIVE' AS br_status,
           br_address,
           br_end,
           br_created,
           br_created_by,
           br_creation_comment
      FROM zbi_data.blocking_rule
     WHERE br_type = %(type)s
       AND (br_end IS NULL OR br_end > zbi_data.utcnow())
       AND br_nullification_type IS NULL
       AND (br_address >> %(address)s OR br_address <<= %(address)s)
       AND br_id != %(excluded_id)s;
"""


### FORMATTING RESULTS ###

def dict_from_rule_row(row):
    result = {
        'status': row.br_status,
        'address': row.br_address,
        'created': {
            'at': row.br_created,
            'by': row.br_created_by,
            'comment': row.br_creation_comment,
        }
    }
    if hasattr(row, 'br_type'):
        result['type'] = row.br_type
    if getattr(row, 'br_end', None):
        result['end'] = row.br_end
    if row.br_status in ('CANCELED', 'SUPERSEDED'):
        result['nullified'] = {
            'at': row.br_nullified,
            'by': row.br_nullified_by,
        }
    if row.br_status == 'CANCELED':
        result['nullified']['comment'] = row.br_nullification_comment
    return result


### GENERATING QUERIES ###

def durationify(query, duration_type):
    """Given a query with a `{duration_snippet}` placeholder, inserts the appropriate SQL snippet for the duration."""
    return query.format(duration_snippet=DURATION_QUERY_SNIPPETS[duration_type])


DURATION_QUERY_SNIPPETS = {
    None: '%(duration)s',
    'for': 'zbi_data.utcnow() + %(duration)s::interval',
    'until': '%(duration)s AT TIME ZONE \'UTC\'',
}

