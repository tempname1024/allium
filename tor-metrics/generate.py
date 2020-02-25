#!/usr/bin/env python3

'''
File: generate.py (executable)

Generate complete set of relay HTML pages and copy static files to
config.CONFIG['output_root'] defined in config.py

Default output directory: ./www
'''

import os
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
    if relays.json is None:
        return
    pages_by_key(relays, 'as')
    pages_by_key(relays, 'country')
    pages_by_key(relays, 'platform')
    effective_family(relays)
    pages_by_flag(relays)
    unsorted(relays, 'index.html', is_index=True)
    unsorted(relays, 'all.html', is_index=False)
    relay_info(relays)
    static_src_path = os.path.join(ABS_PATH, 'static')
    static_dest_path = os.path.join(config.CONFIG['output_root'], 'static')
    if not os.path.exists(static_dest_path):
        copytree(static_src_path, static_dest_path)

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
    q_relays = [] # qualified relays w/ > 1 effective family member
    for relay in relay_list:
        if len(relay['effective_family']) > 1:
            q_relays.append(relay)
    for relay in q_relays:
        fingerprint = relay['fingerprint']
        if not fingerprint.isalnum():
            continue
        members = []   # list of member relays (dict)
        bandwidth = 0  # total bandwidth for family subset
        for p_relay in q_relays:
            if fingerprint in p_relay['effective_family']:
                members.append(p_relay)
                bandwidth += p_relay['observed_bandwidth']
        dir_path = os.path.join(output_path, fingerprint)
        os.makedirs(dir_path)
        f_bandwidth = round(bandwidth / 1000000, 2) # convert to MB/s
        relays.json['relay_subset'] = members
        rendered = template.render(relays=relays, bandwidth=f_bandwidth,
                                   is_index=False, path_prefix='../../',
                                   deactivate='family', family=fingerprint)
        with open(os.path.join(dir_path, 'index.html'), 'w',
                  encoding='utf8') as html:
            html.write(rendered)

def pages_by_key(relays, key):
    '''
    Render and write HTML listings to disk sorted by KEY

    :relays: relays class object containing relay set (list of dict)
    :key: onionoo JSON parameter to sort by, e.g. 'platform'
    '''
    template = ENV.get_template(key + '.html')
    output_path = os.path.join(config.CONFIG['output_root'], key)
    if os.path.exists(output_path):
        rmtree(output_path)
    relay_list = relays.json['relays']
    values_processed = [] # record values we've already processed
    for idx, relay in enumerate(relay_list):
        found_relays = []
        bandwidth = 0 # total bandwidth for relay subset
        if not relay.get(key) or relay[key] in values_processed:
            continue
        if not relay[key].isalnum():
            continue
        values_processed.append(relay[key])
        # find relays w/ matching value past outer idx
        for p_relay in relay_list[idx:]:
            if p_relay.get(key) and p_relay[key] == relay[key]:
                found_relays.append(p_relay)
                bandwidth += p_relay['observed_bandwidth']
        dir_path = os.path.join(output_path, relay[key])
        os.makedirs(dir_path)
        f_bandwidth = round(bandwidth / 1000000, 2) # convert to MB/s
        relays.json['relay_subset'] = found_relays
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
    FLAGS = ['Exit','Fast','Guard','HSDir','Running','Stable','V2Dir','Valid',
             'Authority']
    template = ENV.get_template('flag.html')
    for flag in FLAGS:
        output_path = os.path.join(config.CONFIG['output_root'], 'flag',
                                   flag.lower())
        if os.path.exists(output_path):
            rmtree(output_path)
        relay_list = relays.json['relays']
        found_relays = []
        bandwidth = 0 # total bandwidth for relay subset
        for idx, relay in enumerate(relay_list):
            if not relay.get('flags'):
                continue
            if flag in relay['flags']:
                found_relays.append(relay)
                bandwidth += relay['observed_bandwidth']
        os.makedirs(output_path)
        f_bandwidth = round(bandwidth / 1000000, 2) # convert to MB/s
        relays.json['relay_subset'] = found_relays
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

RELAY_SET = Relays()
generate_html(RELAY_SET)
