'''
File: relays.py

Relays class object consisting of relays (list of dict) and onionoo fetch
timestamp
'''

import hashlib
import json
import os
import re
import time
import urllib.request
from shutil import rmtree
from jinja2 import Environment, FileSystemLoader

ABS_PATH = os.path.dirname(os.path.abspath(__file__))
ENV = Environment(loader=FileSystemLoader(os.path.join(ABS_PATH, '../templates')),
                  trim_blocks=True, lstrip_blocks=True)

class Relays():
    '''
    Relay class consisting of processing routines and onionoo data
    '''
    def __init__(self, output_dir, onionoo_url):
        self.output_dir = output_dir
        self.onionoo_url = onionoo_url
        self.ts_file = os.path.join(os.path.dirname(ABS_PATH), "timestamp")
        self.json = self._fetch_onionoo_details()
        if self.json == None:
            return
        self.timestamp = self._write_timestamp()

        self._fix_missing_observed_bandwidth()
        self._sort_by_bandwidth()
        self._trim_platform()
        self._add_hashed_contact()
        self._categorize()

    def _fetch_onionoo_details(self):
        '''
        Make request to onionoo to retrieve details document, return  JSON
        response
        '''
        if os.path.isfile(self.ts_file):
            with open(self.ts_file, 'r') as ts_file:
                prev_timestamp = ts_file.read()
            headers = {"If-Modified-Since": prev_timestamp}
            conn = urllib.request.Request(self.onionoo_url, headers=headers)
        else:
            conn = urllib.request.Request(self.onionoo_url)

        try:
            api_response = urllib.request.urlopen(conn).read()
        except urllib.error.HTTPError as err:
            if err.code == 304:
                print("no onionoo update since last run, dying peacefully...")
                return
            else:
                raise(err)

        return json.loads(api_response.decode('utf-8'))

    def _trim_platform(self):
        '''
        Trim platform to retain base operating system without version number or
        unnecessary classification which could affect sorting

        e.g. "Tor 0.3.4.9 on Linux" -> "Linux"
        '''
        for relay in self.json['relays']:
            if relay.get('platform'):
                relay['platform'] = relay['platform'].split(' on ', 1)[1].split(' ')[0]
                relay['platform'] = relay['platform'].split('/')[-1] # GNU/*

    def _fix_missing_observed_bandwidth(self):
        '''
        Set the observed_bandwidth parameter value for any relay missing the
        parameter to 0; the observed_bandwidth parameter is (apparently)
        optional, I hadn't run into an instance of it missing until 2019-10-03

        "[...] Missing if router descriptor containing this information cannot be
        found."
        --https://metrics.torproject.org/onionoo.html#details_relay_observed_bandwidth

        '''
        for idx, relay in enumerate(self.json['relays']):
            if not relay.get('observed_bandwidth'):
                self.json['relays'][idx]['observed_bandwidth'] = 0

    def _add_hashed_contact(self):
        '''
        Adds a hashed contact key/value for every relay
        '''
        for idx, relay in enumerate(self.json['relays']):
            c = relay.get('contact', '').encode('utf-8')
            self.json['relays'][idx]['contact_md5'] = hashlib.md5(c).hexdigest()

    def _sort_by_bandwidth(self):
        '''
        Sort full JSON list by highest observed_bandwidth, retain this order
        during subsequent sorting (country, AS, etc)
        '''
        self.json['relays'].sort(key=lambda x: x['observed_bandwidth'],
                                 reverse=True)

    def _write_timestamp(self):
        '''
        Store encoded timestamp in a file to retain time of last request, passed
        to onionoo via If-Modified-Since header during fetch() if exists
        '''
        timestamp = time.time()
        f_timestamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT',
                                    time.gmtime(timestamp))
        if self.json is not None:
            with open(self.ts_file, 'w', encoding='utf8') as ts_file:
                ts_file.write(f_timestamp)

        return f_timestamp

    def _sort(self, relay, idx, k, v):
        '''
        Populate self.sorted dictionary with values from :relay:

        Args:
            relay: relay from which values are derived
            idx:   index at which the relay can be found in self.json['relays']
            k:     the name of the key to use in self.sorted
            v:     the name of the subkey to use in self.sorted[k]
        '''
        if not v or not re.match(r'^[A-Za-z0-9_-]+$', v):
            return

        if not k in self.json['sorted']:
            self.json['sorted'][k] = dict()

        if not v in self.json['sorted'][k]:
            self.json['sorted'][k][v] = {
                'relays':       list(),
                'bandwidth':    0,
                'exit_count':   0,
                'middle_count': 0
            }

        bw = relay['observed_bandwidth']
        self.json['sorted'][k][v]['relays'].append(idx)
        self.json['sorted'][k][v]['bandwidth'] += bw

        if 'Exit' in relay['flags']:
            self.json['sorted'][k][v]['exit_count'] += 1
        else:
            self.json['sorted'][k][v]['middle_count'] += 1

        if k == 'as':
            self.json['sorted'][k][v]['country'] = relay.get('country')
            self.json['sorted'][k][v]['country_name'] = relay.get('country')
            self.json['sorted'][k][v]['as_name'] = relay.get('as_name')

        if k == 'family':
            self.json['sorted'][k][v]['contact'] = relay.get('contact')
            self.json['sorted'][k][v]['contact_md5'] = relay.get('contact_md5')

            # update the first_seen parameter to always contain the oldest
            # relay's first_seen date
            if not self.json['sorted'][k][v].get('first_seen'):
                self.json['sorted'][k][v]['first_seen'] = relay['first_seen']
            elif self.json['sorted'][k][v]['first_seen'] > relay['first_seen']:
                self.json['sorted'][k][v]['first_seen'] = relay['first_seen']

    def _categorize(self):
        '''
        Iterate over self.json['relays'] set and call self._sort() against
        discovered relays with attributes we use to generate static sets
        '''
        self.json['sorted'] = dict()

        for idx, relay in enumerate(self.json['relays']):
            keys = ['as', 'country', 'platform']
            for key in keys:
                self._sort(relay, idx, key, relay.get(key))

            for flag in relay['flags']:
                self._sort(relay, idx, 'flag', flag)

            for member in relay['effective_family']:
                if not len(relay['effective_family']) > 1:
                    continue
                self._sort(relay, idx, 'family', member)

            self._sort(relay, idx, 'first_seen', relay['first_seen'].split(' ')[0])

            c_str = relay.get('contact', '').encode('utf-8')
            c_hash = hashlib.md5(c_str).hexdigest()
            self._sort(relay, idx, 'contact', c_hash)

    def create_output_dir(self):
        '''
        Ensure self.output_dir exists (required for write functions)
        '''
        os.makedirs(self.output_dir,exist_ok=True)

    def write_misc(self, template, path, path_prefix='../', sorted_by=None,
            reverse=True, is_index=False):
        '''
        Render and write unsorted HTML listings to disk

        Args:
            template:    jinja template name
            path:        path to generate HTML document
            path_prefix: path to prefix other docs/includes
            sorted_by:   key to sort by, used in family and networks pages
            reverse:     passed to sort() function in family and networks pages
            is_index:    whether document is main index listing, limits list to 500
        '''
        template = ENV.get_template(template)
        self.json['relay_subset'] = self.json['relays']
        template_render = template.render(
            relays      = self,
            sorted_by   = sorted_by,
            reverse     = reverse,
            is_index    = is_index,
            path_prefix = path_prefix
        )
        output = os.path.join(self.output_dir, path)
        os.makedirs(os.path.dirname(output), exist_ok=True)

        with open(output, 'w', encoding='utf8') as html:
            html.write(template_render)

    def write_pages_by_key(self, k):
        '''
        Render and write sorted HTML relay listings to disk

        Args:
            k: onionoo key to sort by (as, country, platform...)
        '''
        template = ENV.get_template(k + '.html')
        output_path = os.path.join(self.output_dir, k)

        # the "royal the" must be gramatically recognized
        the_prefixed = [
            "Dominican Republic",
            "Ivory Coast",
            "Marshall Islands",
            "Northern Marianas Islands",
            "Solomon Islands",
            "United Arab Emirates",
            "United Kingdom",
            "United States",
            "United States of America",
            "Vatican City",
            "Czech Republic",
            "Bahamas",
            "Gambia",
            "Netherlands",
            "Philippines",
            "Seychelles",
            "Sudan",
            "Ukraine"
        ]

        if os.path.exists(output_path):
            rmtree(output_path)

        for v in self.json['sorted'][k]:
            i = self.json['sorted'][k][v]
            members = []

            for m_relay in i['relays']:
                members.append(self.json['relays'][m_relay])
            if k == 'flag':
                dir_path = os.path.join(output_path, v.lower())
            else:
                dir_path = os.path.join(output_path, v)

            os.makedirs(dir_path)
            self.json['relay_subset'] = members
            rendered = template.render(
                relays       = self,
                bandwidth    = round(i['bandwidth'] / 1000000, 2),
                exit_count   = i['exit_count'],
                middle_count = i['middle_count'],
                is_index     = False,
                path_prefix  = '../../',
                key          = k,
                value        = v,
                sp_countries = the_prefixed
            )

            with open(os.path.join(dir_path, 'index.html'), 'w',
                      encoding='utf8') as html:
                html.write(rendered)

    def write_relay_info(self):
        '''
        Render and write per-relay HTML info documents to disk
        '''
        relay_list = self.json['relays']
        template = ENV.get_template('relay-info.html')
        output_path = os.path.join(self.output_dir, 'relay')

        if os.path.exists(output_path):
            rmtree(output_path)
        os.makedirs(output_path)

        for relay in relay_list:
            if not relay['fingerprint'].isalnum():
                continue
            rendered = template.render(
                relay       = relay,
                path_prefix = '../',
                relays      = self
            )
            with open(os.path.join(output_path, '%s.html' % relay['fingerprint']),
                      'w', encoding='utf8') as html:
                html.write(rendered)
