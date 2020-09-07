#!/usr/bin/env python3

'''
File: generate.py (executable)

Generate complete set of relay HTML pages and copy static files to
config.CONFIG['output_root'] defined in config.py

Default output directory: ./www
'''

import os
import sys
from shutil import copytree
import config
from relays import Relays

ABS_PATH = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    RELAY_SET = Relays()

    # generate relay HTML documents
    RELAY_SET.create_output_dir()
    RELAY_SET.write_unsorted('index.html', is_index=True)
    RELAY_SET.write_unsorted('all.html', is_index=False)
    RELAY_SET.write_unsorted('families.html', is_index=False)
    RELAY_SET.write_unsorted('networks.html', is_index=False)
    RELAY_SET.write_pages_by_key('as')
    RELAY_SET.write_pages_by_key('contact')
    RELAY_SET.write_pages_by_key('country')
    RELAY_SET.write_pages_by_key('family')
    RELAY_SET.write_pages_by_key('flag')
    RELAY_SET.write_pages_by_key('platform')
    RELAY_SET.write_relay_info()

    # copy static directory and its contents
    STATIC_SRC_PATH = os.path.join(ABS_PATH, 'static')
    STATIC_DEST_PATH = os.path.join(config.CONFIG['output_root'], 'static')
    if not os.path.exists(STATIC_DEST_PATH):
        copytree(STATIC_SRC_PATH, STATIC_DEST_PATH)
