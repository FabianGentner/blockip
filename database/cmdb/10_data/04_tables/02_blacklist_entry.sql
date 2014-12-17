CREATE TABLE zbi_data.blacklist_entry (
    be_id serial PRIMARY KEY,
    be_address cidr NOT NULL,
    be_end timestamp(0) NOT NULL DEFAULT zbi_data.utcnow() + '8 hours'::interval,
    be_created timestamp(0) NOT NULL DEFAULT zbi_data.utcnow(),
    be_created_by text NOT NULL,
    be_creation_comment text NOT NULL,
    be_nullified timestamp(0),
    be_nullified_by text,
    be_nullification_type zbi_data.nullification_type,
    be_nullification_comment text,
    CONSTRAINT blacklist_entry_valid_duration
         CHECK (be_end > be_created),
    CONSTRAINT blacklist_entry_valid_nullified
         CHECK ((be_nullification_type IS NULL) = (be_nullified IS NULL)),
    CONSTRAINT blacklist_entry_valid_nullified_by
         CHECK ((be_nullification_type IS NULL) = (be_nullified_by IS NULL)),
    CONSTRAINT blacklist_entry_valid_nullification_comment
         CHECK ((be_nullification_type = 'CANCELED') = (be_nullification_comment IS NOT NULL))
);
