CREATE TABLE zbi_data.whitelist_entry (
    we_id serial PRIMARY KEY,
    we_address cidr NOT NULL,
    we_created timestamp(0) NOT NULL DEFAULT zbi_data.utcnow(),
    we_created_by text NOT NULL,
    we_creation_comment text NOT NULL,
    we_nullified timestamp(0),
    we_nullified_by text,
    we_nullification_type zbi_data.nullification_type,
    we_nullification_comment text,
    CONSTRAINT whitelist_entry_valid_nullified
         CHECK ((we_nullification_type IS NULL) = (we_nullified IS NULL)),
    CONSTRAINT whitelist_entry_valid_nullified_by
         CHECK ((we_nullification_type IS NULL) = (we_nullified_by IS NULL)),
    CONSTRAINT whitelist_entry_valid_nullification_comment
         CHECK ((we_nullification_type = 'CANCELED') = (we_nullification_comment IS NOT NULL))
);
