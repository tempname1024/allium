#!/usr/bin/env python3

from jinja2 import Environment, FileSystemLoader
from shutil import rmtree, copytree
from relays import Relays
import os, json
import config, countries

abs_path = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(os.path.join(abs_path, 'templates')),
        trim_blocks=True, lstrip_blocks=True)

def generate_html(relays):
    if relays.json is not None:
        pages_by_key(relays, 'as')
        pages_by_key(relays, 'country')
        pages_by_key(relays, 'platform')
        unsorted(relays, 'index.html', is_index=True)
        unsorted(relays.json['relays'], 'all.html', is_index=False)
        static_src_path = os.path.join(abs_path, 'static')
        static_dest_path = os.path.join(config.CONFIG['output_root'], 'static')
        if not os.path.exists(static_dest_path):
            copytree(static_src_path, static_dest_path)
    else:
        if relays.statuscode == 304:
            print('HTTP 304 response, no modification since last fetch')
        else:
            print('API request could not be completed')

def unsorted(relays, filename, is_index):
    template_env = env.get_template(filename)
    template_render = template_env.render(relays=relays, is_index=is_index)
    output = os.path.join(config.CONFIG['output_root'], filename)
    with open(output, 'w', encoding='utf8') as out:
        out.write(template_render)

def pages_by_key(relays, key):
    template = env.get_template(key + '.html')
    output_path = os.path.join(config.CONFIG['output_root'], key)
    if os.path.exists(output_path):
        rmtree(output_path)
    relay_list = relays.json['relays']
    values_processed = [] # record values we've already processed
    for idx, relay in enumerate(relay_list):
        found_relays = []
        bandwidth = 0 # total bandwidth for relay subset
        if relay.get(key) and relay[key] not in values_processed:
            values_processed.append(relay[key])
            # find relays w/ matching value past outer idx
            for p_relay in relay_list[idx:]:
                if p_relay.get(key) and p_relay[key] == relay[key]:
                    found_relays.append(p_relay)
                    bandwidth += p_relay['observed_bandwidth']
            bandwidth = round(bandwidth / 1000000, 2) # convert to MB/s
            dir_path = os.path.join(output_path, relay[key])
            os.makedirs(dir_path)
            rendered = template.render(relays=found_relays, bandwidth=bandwidth,
                    deactivate=key, is_index=False, path_prefix='../../',
                    special_countries=countries.the_prefixed)
            with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf8') as html:
                html.write(rendered)

relays = Relays()
generate_html(relays)

