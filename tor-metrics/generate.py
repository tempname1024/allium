#!/usr/bin/env python3

'''
File: generate.py (executable)

Generate complete set of relay HTML pages and copy static files to
config.CONFIG['output_root'] defined in config.py

Default output directory: ./www
'''

import os
import sys
from shutil import rmtree, copytree
import config
import countries
from jinja2 import Environment, FileSystemLoader
from relays import Relays

ABS_PATH = os.path.dirname(os.path.abspath(__file__))
ENV = Environment(loader=FileSystemLoader(os.path.join(ABS_PATH, 'templates')),
                  trim_blocks=True, lstrip_blocks=True)

def generate_html(relays):
    '''
    Render and write complete set of relay pages to disk by calling each group's
    respective function

    Files are written to 'www' by default (defined in config.py)

    :relays: relays class object containing relay set (list of dict)
    '''
    sort_relays(relays)
    pages_by_key(relays, 'as')
    pages_by_key(relays, 'country')
    pages_by_key(relays, 'platform')
    pages_by_flag(relays)
    effective_family(relays)
    unsorted(relays, 'index.html', is_index=True)
    unsorted(relays, 'all.html', is_index=False)
    relay_info(relays)
    static_src_path = os.path.join(ABS_PATH, 'static')
    static_dest_path = os.path.join(config.CONFIG['output_root'], 'static')
    if not os.path.exists(static_dest_path):
        copytree(static_src_path, static_dest_path)

def sort_relays(relays):
    '''
    Add a list of dict sorted by unique keys derived from relays as they're
    discovered, referenced by indice to the main set (relays.json['relays'])

    :relays: relays class object containing relay set (list of dict)
    '''
    keys = ['as', 'country', 'platform']
    if not relays.json.get('sorted'):
        relays.json['sorted'] = dict()

    relay_list = relays.json['relays']
    for idx, relay in enumerate(relay_list):
        for key in keys:
            v = relay.get(key)
            if not v or not v.isalnum(): continue
            if not key in relays.json['sorted']:
                relays.json['sorted'][key] = dict()
            if not v in relays.json['sorted'][key]:
                relays.json['sorted'][key][v] = dict()
                relays.json['sorted'][key][v]['relays'] = list()
                relays.json['sorted'][key][v]['bw'] = 0
            if idx not in relays.json['sorted'][key][v]['relays']:
                bw = relay['observed_bandwidth']
                relays.json['sorted'][key][v]['relays'].append(idx)
                relays.json['sorted'][key][v]['bw'] += bw

        flags = relay['flags']
        for flag in flags:
            if not flag.isalnum(): continue
            if not 'flags' in relays.json['sorted']:
                relays.json['sorted']['flags'] = dict()
            if not flag in relays.json['sorted']['flags']:
                relays.json['sorted']['flags'][flag] = dict()
                relays.json['sorted']['flags'][flag]['relays'] = list()
                relays.json['sorted']['flags'][flag]['bw'] = 0
            if idx not in relays.json['sorted']['flags'][flag]['relays']:
                bw = relay['observed_bandwidth']
                relays.json['sorted']['flags'][flag]['relays'].append(idx)
                relays.json['sorted']['flags'][flag]['bw'] += bw

        members = relay['effective_family']
        for member in members:
            if not member.isalnum() or len(members) < 2: continue
            if not 'family' in relays.json['sorted']:
                relays.json['sorted']['family'] = dict()
            if not member in relays.json['sorted']['family']:
                relays.json['sorted']['family'][member] = dict()
                relays.json['sorted']['family'][member]['relays'] = list()
                relays.json['sorted']['family'][member]['bw'] = 0
            if idx not in relays.json['sorted']['family'][member]['relays']:
                bw = relay['observed_bandwidth']
                relays.json['sorted']['family'][member]['relays'].append(idx)
                relays.json['sorted']['family'][member]['bw'] += bw

def unsorted(relays, filename, is_index):
    '''
    Render and write unsorted HTML listings to disk

    :relays: relays class object containing relay set (list of dict)
    :filename: filename to write unsorted listing (e.g. all.html)
    :is_index: whether the file is an index or not (True/False)
    '''
    template = ENV.get_template(filename)
    relays.json['relay_subset'] = relays.json['relays']
    template_render = template.render(relays=relays, is_index=is_index)
    output = os.path.join(config.CONFIG['output_root'], filename)
    with open(output, 'w', encoding='utf8') as html:
        html.write(template_render)

def effective_family(relays):
    '''
    Render and write HTML listings to disk sorted by effective family

    :relays: relays class object containing relay set (list of dict)
    '''
    template = ENV.get_template('effective_family.html')
    output_path = os.path.join(config.CONFIG['output_root'], 'family')
    if os.path.exists(output_path):
        rmtree(output_path)
    relay_list = relays.json['relays']
    for family in relays.json['sorted']['family']:
        members = []
        bandwidth = relays.json['sorted']['family'][family]['bw']
        for m_relay in relays.json['sorted']['family'][family]['relays']:
            members.append(relay_list[m_relay])
        dir_path = os.path.join(output_path, family)
        os.makedirs(dir_path)
        f_bandwidth = round(bandwidth / 1000000, 2) # convert to MB/s
        relays.json['relay_subset'] = members
        rendered = template.render(relays=relays, bandwidth=f_bandwidth,
                                   is_index=False, path_prefix='../../',
                                   deactivate='family', family=family)
        with open(os.path.join(dir_path, 'index.html'), 'w',
                  encoding='utf8') as html:
            html.write(rendered)

def pages_by_key(relays, key):
    '''
    Render and write HTML listings to disk sorted by KEY

    :relays: relays class object containing relay set (list of dict)
    :key: relays['sorted'] key (onionoo parameter) containing list of indices
          belonging to key
    '''
    template = ENV.get_template(key + '.html')
    output_path = os.path.join(config.CONFIG['output_root'], key)
    if os.path.exists(output_path):
        rmtree(output_path)
    relay_list = relays.json['relays']
    for v in relays.json['sorted'][key]:
        m_relays = list()
        for idx in relays.json['sorted'][key][v]['relays']:
            m_relays.append(relays.json['relays'][idx])
        bandwidth = relays.json['sorted'][key][v]['bw']
        dir_path = os.path.join(output_path, v)
        os.makedirs(dir_path)
        f_bandwidth = round(bandwidth / 1000000, 2) # convert to MB/s
        relays.json['relay_subset'] = m_relays
        rendered = template.render(relays=relays,
                                   bandwidth=f_bandwidth, is_index=False,
                                   path_prefix='../../', deactivate=key,
                                   special_countries=countries.THE_PREFIXED)
        with open(os.path.join(dir_path, 'index.html'), 'w',
                  encoding='utf8') as html:
            html.write(rendered)

def pages_by_flag(relays):
    '''
    Render and write HTML listings to disk sorted by FLAG

    :relays: relays class object containing relay set (list of dict)
    '''
    template = ENV.get_template('flag.html')
    for flag in relays.json['sorted']['flags']:
        output_path = os.path.join(config.CONFIG['output_root'], 'flag',
                                   flag.lower())
        if os.path.exists(output_path):
            rmtree(output_path)
        relay_list = relays.json['relays']
        m_relays = list()
        for idx in relays.json['sorted']['flags'][flag]['relays']:
            m_relays.append(relays.json['relays'][idx])
        bandwidth = relays.json['sorted']['flags'][flag]['bw']
        os.makedirs(output_path)
        f_bandwidth = round(bandwidth / 1000000, 2) # convert to MB/s
        relays.json['relay_subset'] = m_relays
        rendered = template.render(relays=relays,
                                   bandwidth=f_bandwidth, is_index=False,
                                   path_prefix='../../', deactivate=flag,
                                   special_countries=countries.THE_PREFIXED,
                                   flag=flag)
        with open(os.path.join(output_path, 'index.html'), 'w',
                  encoding='utf8') as html:
            html.write(rendered)

def relay_info(relays):
    '''
    Render and write per-relay HTML info documents to disk

    :relays: relays class object containing relay set (list of dict)
    '''
    relay_list = relays.json['relays']
    template = ENV.get_template('relay-info.html')
    output_path = os.path.join(config.CONFIG['output_root'], 'relay')
    if os.path.exists(output_path):
        rmtree(output_path)
    os.makedirs(output_path)
    for relay in relay_list:
        if not relay['fingerprint'].isalnum():
            continue
        rendered = template.render(relay=relay, path_prefix='../',
                                   relays=relays)
        with open(os.path.join(output_path, '%s.html' % relay['fingerprint']),
                  'w', encoding='utf8') as html:
            html.write(rendered)

if __name__ == '__main__':
    try:
        RELAY_SET = Relays()
    except Exception as err:
        print('error creating relays object from onionoo response, aborting...')
        print(err)
        sys.exit()

    generate_html(RELAY_SET)
