-- Yes, the 02 folder is supposed to be used for domains, but I needed some place to put this utility function...

create function zbi_data.utcnow() returns timestamp as $$
    select now() at time zone 'utc';
$$ language sql;
