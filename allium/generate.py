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
    # object containing onionoo data and processing routines
    RELAY_SET = Relays()

    # index and "all" HTML relay sets; index set limited to 500 relays
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

    # miscellaneous page filename suffixes and sorted-by keys
    misc_pages = {
        'by-bandwidth': '1.bandwidth',
        'by-exit-count': '1.exit_count,1.bandwidth',
        'by-middle-count': '1.middle_count,1.bandwidth',
        'by-first-seen': '1.first_seen,1.bandwidth'
    }

    # write miscellaneous-sorted (per misc_pages) HTML pages
    for k, v in misc_pages.items():
        RELAY_SET.write_misc(
            template  = 'misc-families.html',
            path      = 'misc/families-{}.html'.format(k),
            sorted_by = v
        )
        RELAY_SET.write_misc(
            template  = 'misc-networks.html',
            path      = 'misc/networks-{}.html'.format(k),
            sorted_by = v
        )

    # onionoo keys to generate pages by unique value
    keys = ['as', 'contact', 'country', 'family', 'flag', 'platform',
            'first_seen']

    for k in keys:
        RELAY_SET.write_pages_by_key(k)

    # per-relay info pages
    RELAY_SET.write_relay_info()

    STATIC_SRC_PATH = os.path.join(ABS_PATH, 'static')
    STATIC_DEST_PATH = os.path.join(config.CONFIG['output_root'], 'static')

    # copy static directory and its contents if it doesn't exist
    if not os.path.exists(STATIC_DEST_PATH):
        copytree(STATIC_SRC_PATH, STATIC_DEST_PATH)
