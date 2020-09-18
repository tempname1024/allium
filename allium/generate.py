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
    RELAY_SET.write_misc(
        template    = 'index.html',
        path        = 'index.html',
        path_prefix = './',
        is_index    = True,
    )
    RELAY_SET.write_misc(
        template  = 'all.html',
        path      = 'misc/all.html'
    )
    RELAY_SET.write_misc(
        template  = 'misc-families.html',
        path      = 'misc/families-by-bandwidth.html',
        sorted_by = '1.bandwidth'
    )
    RELAY_SET.write_misc(
        template  = 'misc-families.html',
        path      = 'misc/families-by-exit-count.html',
        sorted_by = '1.exit_count,1.bandwidth'
    )
    RELAY_SET.write_misc(
        template  = 'misc-families.html',
        path      = 'misc/families-by-middle-count.html',
        sorted_by = '1.middle_count,1.bandwidth'
    )
    RELAY_SET.write_misc(
        template  = 'misc-families.html',
        path      = 'misc/families-by-first-seen.html',
        sorted_by = '1.first_seen,1.bandwidth'
    )
    RELAY_SET.write_misc(
        template  = 'misc-networks.html',
        path      = 'misc/networks-by-bandwidth.html',
        sorted_by = '1.bandwidth'
    )
    RELAY_SET.write_misc(
        template  = 'misc-networks.html',
        path      = 'misc/networks-by-exit-count.html',
        sorted_by = '1.exit_count,1.bandwidth'
    )
    RELAY_SET.write_misc(
        template  = 'misc-networks.html',
        path      = 'misc/networks-by-middle-count.html',
        sorted_by = '1.middle_count,1.bandwidth'
    )
    RELAY_SET.write_misc(
        template  = 'misc-networks.html',
        path      = 'misc/networks-by-first-seen.html',
        sorted_by = '1.first_seen,1.bandwidth'
    )
    RELAY_SET.write_pages_by_key('as')
    RELAY_SET.write_pages_by_key('contact')
    RELAY_SET.write_pages_by_key('country')
    RELAY_SET.write_pages_by_key('family')
    RELAY_SET.write_pages_by_key('flag')
    RELAY_SET.write_pages_by_key('platform')
    RELAY_SET.write_pages_by_key('first_seen')
    RELAY_SET.write_relay_info()

    # copy static directory and its contents
    STATIC_SRC_PATH = os.path.join(ABS_PATH, 'static')
    STATIC_DEST_PATH = os.path.join(config.CONFIG['output_root'], 'static')
    if not os.path.exists(STATIC_DEST_PATH):
        copytree(STATIC_SRC_PATH, STATIC_DEST_PATH)
