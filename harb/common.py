from __future__ import print_function, division

import logging
import pymongo

TO_BE_PLACED = 'TO BE PLACED'


def configure_root_logger(to_stdout=True, file_out=None, level=logging.DEBUG, formatter=None):
    logger = logging.getLogger()
    logger.handlers = []
    logger.setLevel(logging.INFO)
    # create console handler and set level to debug
    if formatter is None:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    if file_out is not None:
        file_log = logging.FileHandler(file_out, mode = 'a')
        file_log.setLevel(level)
        file_log.setFormatter(formatter)
        logger.addHandler(file_log)
    if to_stdout:
        stdout_log = logging.StreamHandler()
        stdout_log.setLevel(level)
        stdout_log.setFormatter(formatter)
        logger.addHandler(stdout_log)
    return logger


def update_root_logger_formatters(formatter):
    for h in logging.getLogger().handlers:
        h.setFormatter(formatter)