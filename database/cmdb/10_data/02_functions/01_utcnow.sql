-- Yes, the 02 folder is supposed to be used for domains, but I needed some place to put this utility function...

-- This function is STABLE since now() is based on the start time of the current transaction.
CREATE FUNCTION zbi_data.utcnow()
        RETURNS timestamp
         STABLE
       LANGUAGE sql
             AS $$
                SELECT now() AT TIME ZONE 'utc';
                $$;
