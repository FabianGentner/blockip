import argparse
import re
import pathlib
import subprocess
import sys

sys.path.append('src/')

import utilities

SQL_IDENTIFIER_PATTERN = re.compile(r'(?ui)^(?:\w(?<![0-9])[\w$]*|"(?:[^"\0]|"")+")*$')
SQL_FILE_BASE_PATH = pathlib.Path('database')
CREATE_SCHEMA_FILE_PATH = SQL_FILE_BASE_PATH / '10_data' / '00_create_schema.sql'

LOGGER = None


### DROPPING THE SCHEMA ###

def maybe_drop_existing_schema(context):
    if context.drop_schema_even_if_the_database_is_not_local_yes_i_am_absolutely_sure_i_want_to_do_that:
        drop_existing_schema(context)
    elif context.drop_schema:
        if is_local_host(context.host):
            drop_existing_schema(context)
        else:
            template = 'I\'m not just going to drop the schema for the database running on {host}, which doesn\'t ' \
                'appear to be your localhost. If you really want me to drop that schema, use ' \
                '--drop-schema-even-if-the-database-is-not-local-yes-i-am-absolutely-sure-i-want-to-do-that ' \
                'rather than --drop-schema.'
            print(msg.format)
            sys.exit(1)


def drop_existing_schema(context):
    execute_sql(context, 'DROP SCHEMA IF EXISTS {schema} CASCADE;'.format(schema=context.schema))


### CREATING THE SCHEMA ###

def create_schema(context):
    if context.schema:
        with CREATE_SCHEMA_FILE_PATH.open() as create_schema_file:
            sql = create_schema_file.read()
    sql = sql.replace('__SCHEMA__', context.schema)
    sql = sql.replace('__MAIN_ROLE__', context.main_role)
    sql = sql.replace('__READ_ROLE__', context.read_role)
    sql = sql.replace('__WRITE_ROLE__', context.write_role)
    sql = sql.replace('__DATA_USAGE_ROLE__', context.data_usage_role)
    execute_sql(context, sql)


### CREATING THE OTHER STUFF ###

def create_other_stuff(context):
    for path in sql_files(SQL_FILE_BASE_PATH):
        with path.open() as sql_file:
            sql = sql_file.read()
        if context.schema:
            sql = sql.replace('__SCHEMA__', context.schema)
        else:
            sql = sql.replace('__SCHEMA__.', '')
        execute_sql(context, sql)


def sql_files(base_path):
    for path in base_path.iterdir():
        if path.is_dir():
            yield from sql_files(path)
        elif path.is_file() and path.suffix == '.sql' and path.name != '00_create_schema.sql':
            yield path


### CONTEXT ###

class Context:

    def __init__(self, arguments, settings):
        self.host = settings.get('db', 'host')
        self.database = settings.get('db', 'database')
        self.schema = settings.get('db', 'schema', fallback='')
        self.user = settings.get('db', 'user')
        self.password = settings.get('db', 'password', fallback='')
        self.dry_run = arguments.dry_run
        self.drop_schema = arguments.drop_schema
        self.drop_schema_even_if_the_database_is_not_local_yes_i_am_absolutely_sure_i_want_to_do_that = \
            arguments.drop_schema_even_if_the_database_is_not_local_yes_i_am_absolutely_sure_i_want_to_do_that
        self.main_role = settings.get('dbinit', 'main_role', fallback='')
        self.read_role = settings.get('dbinit', 'read_role', fallback='')
        self.write_role = settings.get('dbinit', 'write_role', fallback='')
        self.data_usage_role = settings.get('dbinit', 'data_usage_role', fallback='')
        self.check()

    def check(self):
        if self.schema:
            if not SQL_IDENTIFIER_PATTERN.search(self.schema):
                print('The schema name {} does not look like a valid PostgreSQL identifer.'.format(self.schema))
                sys.exit(2)
            for role in (self.main_role, self.read_role, self.write_role, self.data_usage_role):
                if not SQL_IDENTIFIER_PATTERN.search(role):
                    print('The role name {} does not look like a valid PostgreSQL identifer.'.format(role))
                    sys.exit(2)


### UTILITY FUNCTIONS ###

def is_local_host(host):
    # Yes, this is a simplification...
    return host in ('localhost', '127.0.0.1', '::1')

def execute_sql(context, sql):
    command = ['psql', '-h', context.host, '-U', context.user, '-c', sql, context.database]
    if context.dry_run:
        print('DRY RUN: $', subprocess.list2cmdline(command))
    else:
        subprocess.check_call(command)


### COMMAND LINE ARGUMENTS ###

def create_command_line_argument_parser():
    parser = argparse.ArgumentParser(description='Creates the database used by blockip.')
    utilities.add_config_option(parser, 'blockip')
    parser.add_argument('-D', '--drop-schema', action='store_true')
    parser.add_argument('--drop-schema-even-if-the-database-is-not-local-yes-i-am-absolutely-sure-i-want-to-do-that',
        action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--dry-run', action='store_true')
    utilities.add_log_level_options(parser)
    return parser


def parse_command_line_arguments(args=None):
    return create_command_line_argument_parser().parse_args(args)


### MAIN ENTRYPOINT ###

def main(args=None):
    global LOGGER
    command_line_arguments = parse_command_line_arguments(args)
    LOGGER = utilities.create_logger(command_line_arguments.log_level)
    configuration_settings = utilities.read_configuration_files(command_line_arguments.configuration_file_paths)
    configuration_file_paths_read = configuration_settings.configuration_file_paths_read
    LOGGER.info('Read configuration settings from %s.', utilities.and_join(configuration_file_paths_read))
    context = Context(command_line_arguments, configuration_settings)
    maybe_drop_existing_schema(context)
    create_schema(context)
    create_other_stuff(context)


if __name__ == '__main__':
    main()

