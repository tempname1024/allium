'''
File: relays.py

Relays class object consisting of relays (list of dict) and onionoo fetch
timestamp
'''

import hashlib
import json
import os
import time
import urllib.request
from shutil import rmtree
import config
import countries
from jinja2 import Environment, FileSystemLoader

ABS_PATH = os.path.dirname(os.path.abspath(__file__))
ENV = Environment(loader=FileSystemLoader(os.path.join(ABS_PATH, 'templates')),
                  trim_blocks=True, lstrip_blocks=True)

def hash_filter(value, hash_type='md5'):
    '''
    Custom hash filter for jinja; defaults to "md5" if no type specified

    :param value: value to be hashed
    :param hash_type: valid hash type
    :return: computed hash as a hexadecimal string
    '''
    hash_func = getattr(hashlib, hash_type, None)

    if hash_func:
        computed_hash = hash_func(value.encode("utf-8")).hexdigest()
    else:
        raise AttributeError(
            "No hashing function named {hname}".format(hname=hash_type)
        )

    return computed_hash

ENV.filters['hash'] = hash_filter

class Relays:
    '''
    Relay class consisting of relays (list of dict) and onionoo fetch timestamp

    :ts_file: absolute path to timestamp file used in setting If-Modified_since
    :json: relay listings stored as a list of dict, derived from onionoo JSON
    :timestamp: timestamp of onionoo fetch
    '''
    def __init__(self):
        self.url = config.CONFIG['onionoo_url']
        self.ts_file = os.path.join(ABS_PATH, "timestamp")
        self.json = self._fetch_onionoo_details()
        self.timestamp = self._write_timestamp()

        self._fix_missing_observed_bandwidth()
        self._sort_by_bandwidth()
        self._trim_platform()
        self._categorize_relays()

    def _fetch_onionoo_details(self):
        '''
        Make request to onionoo to retrieve details document, return prepared
        JSON response (trimmed platform and sorted by highest observed
        bandwidth)
        '''
        if os.path.isfile(self.ts_file):
            with open(self.ts_file, 'r') as ts_file:
                prev_timestamp = ts_file.read()
            headers = {"If-Modified-Since": prev_timestamp}
            conn = urllib.request.Request(self.url, headers=headers)
        else:
            conn = urllib.request.Request(self.url)

        api_response = urllib.request.urlopen(conn).read()

        json_data = json.loads(api_response.decode('utf-8'))
        return json_data

    def _trim_platform(self):
        '''
        Trim platform to retain base operating system without version number or
        unnecessary classification which could affect sorting

        e.g. "Tor 0.3.4.9 on Linux" -> "Linux"
        '''
        for relay in self.json['relays']:
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

    def _categorize_relays(self):
        '''
        Add a list of dict sorted by unique keys derived from relays as they're
        discovered, referenced by indice to the main set (relays.json['relays'])

        This code looks (is) redundant but it saves us from multiple passes
        over the entire set... not sure how to generalize it beyond the keys
        list
        '''
        self.json['sorted'] = dict()
        for idx, relay in enumerate(self.json['relays']):
            keys = ['as', 'country', 'platform']
            for key in keys:
                v = relay.get(key)
                if not v or not v.isalnum(): continue
                if not key in self.json['sorted']:
                    self.json['sorted'][key] = dict()
                if not v in self.json['sorted'][key]:
                    self.json['sorted'][key][v] = {
                        'relays':       list(),
                        'bw':           0,
                        'exit_count':   0,
                        'middle_count': 0
                    }
                bw = relay['observed_bandwidth']
                self.json['sorted'][key][v]['relays'].append(idx)
                self.json['sorted'][key][v]['bw'] += bw
                if 'Exit' in relay['flags']:
                    self.json['sorted'][key][v]['exit_count'] += 1
                else:
                    self.json['sorted'][key][v]['middle_count'] += 1

            for flag in relay['flags']:
                if not flag.isalnum(): continue
                if not 'flags' in self.json['sorted']:
                    self.json['sorted']['flags'] = dict()
                if not flag in self.json['sorted']['flags']:
                    self.json['sorted']['flags'][flag] = {
                        'relays':       list(),
                        'bw':           0,
                        'exit_count':   0,
                        'middle_count': 0
                    }
                bw = relay['observed_bandwidth']
                self.json['sorted']['flags'][flag]['relays'].append(idx)
                self.json['sorted']['flags'][flag]['bw'] += bw
                if 'Exit' in relay['flags']:
                    self.json['sorted']['flags'][flag]['exit_count'] += 1
                else:
                    self.json['sorted']['flags'][flag]['middle_count'] += 1

            for member in relay['effective_family']:
                if not member.isalnum() or len(relay['effective_family']) < 2:
                    continue
                if not 'family' in self.json['sorted']:
                    self.json['sorted']['family'] = dict()
                if not member in self.json['sorted']['family']:
                    self.json['sorted']['family'][member] = {
                        'relays':       list(),
                        'bw':           0,
                        'exit_count':   0,
                        'middle_count': 0
                    }
                bw = relay['observed_bandwidth']
                self.json['sorted']['family'][member]['relays'].append(idx)
                self.json['sorted']['family'][member]['bw'] += bw
                if 'Exit' in relay['flags']:
                    self.json['sorted']['family'][member]['exit_count'] += 1
                else:
                    self.json['sorted']['family'][member]['middle_count'] += 1

            c_str = relay.get('contact', '').encode('utf-8')
            c_hash = hashlib.md5(c_str).hexdigest()
            if 'contact' not in self.json['sorted']:
                self.json['sorted']['contact'] = dict()
            if not c_hash in self.json['sorted']['contact']:
                self.json['sorted']['contact'][c_hash] = {
                    'relays':       list(),
                    'contact':      c_str,
                    'bw':           0,
                    'exit_count':   0,
                    'middle_count': 0
                }
            bw = relay['observed_bandwidth']
            self.json['sorted']['contact'][c_hash]['relays'].append(idx)
            self.json['sorted']['contact'][c_hash]['bw'] += bw
            if 'Exit' in relay['flags']:
                self.json['sorted']['contact'][c_hash]['exit_count'] += 1
            else:
                self.json['sorted']['contact'][c_hash]['middle_count'] += 1

    def create_output_dir(self):
        '''
        Ensure config:output_root exists (required for write functions)
        '''
        os.makedirs(config.CONFIG['output_root'],exist_ok=True)

    def write_unsorted(self, filename, is_index):
        '''
        Render and write unsorted HTML listings to disk

        :filename: filename to write unsorted listing (e.g. all.html)
        :is_index: whether the file is an index or not (True/False)
        '''
        template = ENV.get_template(filename)
        self.json['relay_subset'] = self.json['relays']
        template_render = template.render(relays=self, is_index=is_index)
        output = os.path.join(config.CONFIG['output_root'], filename)
        with open(output, 'w', encoding='utf8') as html:
            html.write(template_render)

    def write_effective_family(self):
        '''
        Render and write HTML listings to disk sorted by effective family
        '''
        template = ENV.get_template('effective_family.html')
        output_path = os.path.join(config.CONFIG['output_root'], 'family')
        if os.path.exists(output_path):
            rmtree(output_path)
        for family in self.json['sorted']['family']:
            i = self.json['sorted']['family'][family]
            members = []
            for m_relay in i['relays']:
                members.append(self.json['relays'][m_relay])
            dir_path = os.path.join(output_path, family)
            os.makedirs(dir_path)
            self.json['relay_subset'] = members
            rendered = template.render(
                relays=self,
                bandwidth=round(i['bw'] / 1000000, 2),
                exit_count=i['exit_count'],
                middle_count=i['middle_count'],
                is_index=False,
                path_prefix='../../',
                deactivate='family',
                family=family
            )
            with open(os.path.join(dir_path, 'index.html'), 'w',
                      encoding='utf8') as html:
                html.write(rendered)

    def write_pages_by_key(self, key):
        '''
        Render and write HTML listings to disk sorted by KEY

        :key: relays['sorted'] key (onionoo parameter) containing list of indices
              belonging to key
        '''
        template = ENV.get_template(key + '.html')
        output_path = os.path.join(config.CONFIG['output_root'], key)
        if os.path.exists(output_path):
            rmtree(output_path)
        for v in self.json['sorted'][key]:
            i = self.json['sorted'][key][v]
            m_relays = list()
            for idx in i['relays']:
                m_relays.append(self.json['relays'][idx])
            dir_path = os.path.join(output_path, v)
            os.makedirs(dir_path)
            self.json['relay_subset'] = m_relays
            rendered = template.render(
                relays=self,
                bandwidth=round(i['bw'] / 1000000, 2),
                exit_count=i['exit_count'],
                middle_count=i['middle_count'],
                is_index=False,
                path_prefix='../../',
                deactivate=key,
                special_countries=countries.THE_PREFIXED
            )
            with open(os.path.join(dir_path, 'index.html'), 'w',
                      encoding='utf8') as html:
                html.write(rendered)

    def write_pages_by_flag(self):
        '''
        Render and write HTML listings to disk sorted by FLAG
        '''
        template = ENV.get_template('flag.html')
        for flag in self.json['sorted']['flags']:
            i = self.json['sorted']['flags'][flag]
            output_path = os.path.join(config.CONFIG['output_root'], 'flag',
                                       flag.lower())
            if os.path.exists(output_path):
                rmtree(output_path)
            relay_list = self.json['relays']
            m_relays = list()
            for idx in i['relays']:
                m_relays.append(self.json['relays'][idx])
            os.makedirs(output_path)
            self.json['relay_subset'] = m_relays
            rendered = template.render(
                relays=self,
                bandwidth=round(i['bw'] / 1000000, 2),
                exit_count=i['exit_count'],
                middle_count=i['middle_count'],
                is_index=False,
                path_prefix='../../',
                deactivate=flag,
                special_countries=countries.THE_PREFIXED,
                flag=flag
            )
            with open(os.path.join(output_path, 'index.html'), 'w',
                      encoding='utf8') as html:
                html.write(rendered)

    def write_relay_info(self):
        '''
        Render and write per-relay HTML info documents to disk
        '''
        relay_list = self.json['relays']
        template = ENV.get_template('relay-info.html')
        output_path = os.path.join(config.CONFIG['output_root'], 'relay')
        if os.path.exists(output_path):
            rmtree(output_path)
        os.makedirs(output_path)
        for relay in relay_list:
            if not relay['fingerprint'].isalnum():
                continue
            rendered = template.render(
                relay=relay,
                path_prefix='../',
                relays=self
            )
            with open(os.path.join(output_path, '%s.html' % relay['fingerprint']),
                      'w', encoding='utf8') as html:
                html.write(rendered)
