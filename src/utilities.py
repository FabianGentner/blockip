"""
Provides a number of generic utility functions.
"""

import collections
import configparser
import datetime
import ipaddress
import json
import logging
import numbers
import os


### JSON ###

class ISODatetimeJSONEncoder(json.JSONEncoder):
    """A JSONEncoder that encodes datetime objects in ISO format (without the 'T')."""

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat(' ')


### TEXT FORMATTING ###

def and_join(sequence):
    """Returns a string listing the string in the given (nonempty) sequence ("A", "A and B", "A, B, and C")."""
    return ', '.join(sequence[:-1]) + ',' * (len(sequence) > 2) + ' and ' * (len(sequence) > 1) + sequence[-1]


### FUNCTIONS ###

def identity(o):
    """The identity function."""
    return o


### INTROSPECTION ###

IGNORABLE_MODULES = {'__main__', 'builtins'}

def get_qualified_class_name(o):
    """Returns the qualified name of the class of the given object, including the module it is defined in."""
    module = o.__class__.__module__
    module = '' if module in IGNORABLE_MODULES else module
    module = module + '.' if module else module
    return module + o.__class__.__qualname__


### LOGGING ###

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
LOG_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'


def create_logger(log_level):
    """Creates a logger for the given log level."""
    log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_TIMESTAMP_FORMAT)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger = logging.getLogger('blockip')
    logger.setLevel(log_level)
    logger.addHandler(console_handler)
    return logger


### COMMAND LINE ARGUMENTS ###

def add_log_level_options(argument_parser):
    """Adds the options --quiet and --verbose to the given `argparse.ArgumentParser`."""
    verbosity_group = argument_parser.add_mutually_exclusive_group()
    verbosity_group.add_argument('-q', '--quiet', action='store_const', const=logging.WARNING, dest='log_level',
                                 default=logging.INFO, help='If given, only warnings and errors are logged.')
    verbosity_group.add_argument('-v', '--verbose', action='store_const', const=logging.DEBUG, dest='log_level',
                                 default=logging.INFO, help='If given, debug messages are logged.')


def add_config_option(argument_parser, script_name):
    """Adds the option --config to the given `argparse.ArgumentParser`."""
    default_paths = [template.format(script_name) for template in ('./{}.conf', '~/.{}.conf')]
    help_message_template = 'The path to a configuration file. Can be specified multiple times. The script reads ' \
        'configuration settings from {} in order, with duplicate settings superseding existing ones.'
    help_message = help_message_template.format(and_join(default_paths + ['the specified files']))
    argument_parser.add_argument('-c', '--config', metavar='FILE', action='append', default=default_paths,
        dest='configuration_file_paths', help=help_message)


### CONFIGURATION FILES ###

def read_configuration_files(configuration_file_paths):
    """Returns a `configparser.RawConfigParser` instance that has attempted to read the given configuration files."""
    configuration_file_parser = configparser.RawConfigParser()
    configuration_file_paths = map(os.path.expanduser, configuration_file_paths)
    configuration_file_paths_read = configuration_file_parser.read(configuration_file_paths)
    configuration_file_parser.configuration_file_paths = configuration_file_paths
    configuration_file_parser.configuration_file_paths_read = configuration_file_paths_read
    return configuration_file_parser

