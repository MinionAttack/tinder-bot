# -*- coding: utf-8 -*-
import logging.config
import os
import pathlib

import yaml

from resources.constants import LOG_MODE

file_path = pathlib.Path(__file__).parent.absolute()
log_files_path = os.path.join(str(file_path), 'logs')

pathlib.Path(log_files_path).mkdir(exist_ok=True)

path_critical_log_file = os.path.join(log_files_path, 'critical.txt')
path_debug_log_file = os.path.join(log_files_path, 'debug.txt')
path_errors_log_file = os.path.join(log_files_path, 'error.txt')
path_info_log_file = os.path.join(log_files_path, 'information.txt')
path_warn_log_file = os.path.join(log_files_path, 'warning.txt')

log_files = [path_critical_log_file, path_debug_log_file, path_errors_log_file, path_info_log_file, path_warn_log_file]

for log_file in log_files:
    if not os.path.exists(log_file):
        try:
            created_file = open(log_file, encoding='utf-8', mode='a+')
        except (IOError, EOFError) as error:
            print('Unable to create log file: {}'.format(log_file))
            print(error)

path_log_file = os.path.join(file_path, 'resources', 'log_configuration.yaml')

if os.path.exists(file_path):
    if os.path.isfile(path_log_file):
        with open(path_log_file, 'r') as config_file:
            config = yaml.safe_load(config_file.read())
            logging.config.dictConfig(config)
            config_file.close()
    else:
        print('The path to the log configuration file must be a file not a directory: {}'.format(path_log_file))
else:
    print('The path to the log configuration file do not exist: {}'.format(path_log_file))

logger = logging.getLogger(LOG_MODE)
