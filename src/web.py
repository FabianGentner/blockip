"""
Defines the main entrypoint for the blockip microservice.
"""

import argparse
import logging

import context
import endpoints
import utilities


### CONFIGURATION ###

DEFAULT_CONFIGURATION_FILE_PATHS = ['./blockip.conf', '~/.blockip.conf']


### COMMAND LINE ARGUMENTS ###

def create_command_line_argument_parser():
    parser = argparse.ArgumentParser(description='A RESTful microservice for blocking IP addresses.')
    utilities.add_config_option(parser, 'blockip')
    parser.add_argument('--debug', action='store_true', help='If given, Flask is started in debug mode.')
    parser.add_argument('--no-permission-checks', action='store_true', help='If given, permissions aren\'t checked.')
    utilities.add_log_level_options(parser)
    return parser


def parse_command_line_arguments(args=None):
    return create_command_line_argument_parser().parse_args(args)


### MAIN ENTRYPOINT ###

def main(args=None):
    command_line_arguments = parse_command_line_arguments(args)
    context.logger = utilities.create_logger(command_line_arguments.log_level)
    configuration_settings = utilities.read_configuration_files(command_line_arguments.configuration_file_paths)
    configuration_file_paths_read = configuration_settings.configuration_file_paths_read
    context.logger.info('Read configuration settings from %s.', utilities.and_join(configuration_file_paths_read))
    context.arguments = command_line_arguments
    context.settings = configuration_settings
    context.app.json_encoder = utilities.ISODatetimeJSONEncoder
    context.app.run(debug=command_line_arguments.debug)


if __name__ == '__main__':
    main()

