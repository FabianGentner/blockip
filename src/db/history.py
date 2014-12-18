import db


@db.with_connection
def get_overlapping_entries(connection, address):
    query = GET_HISTORY_FOR_ADDRESS_QUERY
    parameters = {'address': address}
    return db.execute_query(connection, query, parameters, db.common.dict_from_rule_row)


GET_HISTORY_FOR_ADDRESS_QUERY = """
      SELECT br_type,
             (CASE WHEN br_nullification_type IS NOT NULL THEN br_nullification_type::text::zbi_data.blocking_rule_status
                  WHEN br_end IS NOT NULL AND br_end < zbi_data.utcnow() THEN 'ENDED'
                  ELSE 'ACTIVE'
              END) AS br_status,
             br_address,
             br_end,
             br_created,
             br_created_by,
             br_creation_comment,
             br_nullified,
             br_nullified_by,
             br_nullification_comment
        FROM zbi_data.blocking_rule
       WHERE (br_address >> %(address)s OR br_address <<= %(address)s)
    ORDER BY br_created ASC,
             br_id ASC;
"""

