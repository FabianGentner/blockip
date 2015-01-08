CREATE TABLE __SCHEMA__.blocking_rule (
    br_id serial PRIMARY KEY,
    br_type __SCHEMA__.blocking_rule_type NOT NULL,
    br_address cidr NOT NULL,
    br_end timestamp(0),
    br_created timestamp(0) NOT NULL DEFAULT __SCHEMA__.utcnow(),
    br_created_by text NOT NULL,
    br_creation_comment text NOT NULL,
    br_nullified timestamp(0),
    br_nullified_by text,
    br_nullification_type __SCHEMA__.nullification_type,
    br_nullification_comment text,

    -- Blacklist entries must have an end; whitelist entries must not.
    CONSTRAINT br_appropriate_end_for_type
         CHECK ((br_type = 'WHITELIST') = (br_end IS NULL)),
    -- If a rule has an end, it must be after the rule's creation.
    CONSTRAINT br_valid_duration
         CHECK (br_end IS NULL OR br_end > br_created),
    -- Whitelist entries cannot be superseded.
    CONSTRAINT br_valid_nullification_type
         CHECK (br_type != 'WHITELIST' OR br_nullification_type IS NULL OR br_nullification_type != 'SUPERSEDED'),
    -- All nullification-relared columns must or must not be NULL depending on whether the rule has been nullified.
    CONSTRAINT br_valid_nullified
         CHECK ((br_nullification_type IS NULL) = (br_nullified IS NULL)),
    CONSTRAINT br_valid_nullified_by
         CHECK ((br_nullification_type IS NULL) = (br_nullified_by IS NULL)),
    CONSTRAINT br_nullification_comment
         CHECK ((br_nullification_type = 'CANCELED') = (br_nullification_comment IS NOT NULL))
);

