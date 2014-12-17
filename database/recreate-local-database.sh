#!/bin/sh

# Creates the database schema used by this script in your local_cmdb_db. Drops the schema if it already exists.
# Assumes your current working directory is blockip, not blockip/database.
PGSSLMODE=prefer psql -h localhost -U postgres -c 'DROP SCHEMA IF EXISTS zbi_data CASCADE;' local_cmdb_db
find database/cmdb -name '*.sql' | sort | xargs cat | PGSSLMODE=prefer psql -h localhost -U postgres local_cmdb_db
