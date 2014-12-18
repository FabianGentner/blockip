-- Must be a superset of nullification_type.
CREATE TYPE zbi_data.blocking_rule_status AS ENUM
(
    'ACTIVE',
    'ENDED',
    'SUPERSEDED',
    'CANCELED'
);
