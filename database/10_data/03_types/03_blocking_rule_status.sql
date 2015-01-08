-- Must be a superset of nullification_type.
CREATE TYPE __SCHEMA__.blocking_rule_status AS ENUM
(
    'ACTIVE',
    'ENDED',
    'SUPERSEDED',
    'CANCELED'
);
