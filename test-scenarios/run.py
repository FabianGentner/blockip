"""
A quick and dirty test script that runs the scenarios in scenarios/.
"""

import datetime
import os
import pathlib
import re
import subprocess
import sys


DEFAULT_URL = 'http://127.0.0.1:5000'
HERE = pathlib.Path(os.path.abspath(__name__)).parent
SCENARIO_PATH = HERE / 'scenarios'
DATABASE_CREATION_SCRIPT_PATH = HERE.parent / 'database' / 'create-database.py'

COMMAND_URL_PLACEHOLDER = '${HOST}'
COMMAND_CREDENTIALS_PLACEHOLDER = '${USER}'
RESPONSE_USER_NAME_PLACEHOLDER = 'fgentner'

DATE_PATTERN_2XXX = re.compile(r'2\d{3}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')


def main():
    url = input('URL of the blockip instance you want to test [{}] > '.format(DEFAULT_URL)) or DEFAULT_URL
    user_name = input('Your user name > ')
    password = input('Your password > ')
    print()

    for scenario_path in scenario_paths():
        recreate_database()
        print('Running scenario {}...'.format(str(scenario_path.relative_to(SCENARIO_PATH))[:-4]))
        for command, expected_response in exchanges(scenario_path, url, user_name, password):
            actual_response = run_command(command, user_name)
            print('    $', command)
            if expected_response and actual_response != expected_response:
                print('    ERROR')
                print('    Expected response:')
                print('        ' + expected_response.replace('\n', '\n        '))
                print('    Actual response:')
                print('        ' + actual_response.replace('\n', '\n        '))
                sys.exit(1)
    print()
    print('OK')


def recreate_database():
    command = ['python', str(DATABASE_CREATION_SCRIPT_PATH), '-D']
    output = subprocess.check_output(command, stderr=subprocess.STDOUT, cwd=str(HERE.parent)).decode('UTF-8')
    if 'ERROR' in output:
        print('Attempting to recreate the database caused one or more errors:')
        print('    ' + output.replace('\n', '\n    '))
        sys.exit(2)


def run_command(command, user_name):
    output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True).decode('UTF-8')
    output = DATE_PATTERN_2XXX.sub('<DATE>', output)
    output = output.replace(RESPONSE_USER_NAME_PLACEHOLDER, user_name)
    return output


def exchanges(scenario_path, url, user_name, password):
    with scenario_path.open() as scenario_file:
        scenario = scenario_file.read()
    scenario = scenario.lstrip('$ ')
    for chunk in scenario.split('\n$ '):
        if '\n' in chunk:
            command, response = chunk.split('\n', 1)
        else:
            command, response = chunk, ''
        credentials = '{}:{}'.format(user_name, password)
        tomorrow = (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat(' ')
        command = command.replace(COMMAND_URL_PLACEHOLDER, url)
        command = command.replace(COMMAND_CREDENTIALS_PLACEHOLDER, credentials)
        command = command.replace('curl', 'curl -Ss')
        command = DATE_PATTERN_2XXX.sub(tomorrow, command)
        response = response.replace(RESPONSE_USER_NAME_PLACEHOLDER, user_name)
        response = DATE_PATTERN_2XXX.sub('<DATE>', response)
        response = response.rstrip()
        yield command, response


def scenario_paths(root=SCENARIO_PATH):
    for f in root.iterdir():
        if f.is_file() and f.suffix == '.txt':
            yield f
        elif f.is_dir() and not f.is_symlink():
            yield from scenario_paths(f)


if __name__ == '__main__':
    main()

