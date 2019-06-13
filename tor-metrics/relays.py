import os, json, requests, time
import config

abs_path = os.path.dirname(os.path.abspath(__file__))

class Relays:
    def __init__(self):
        self.statuscode = None
        self.url = config.CONFIG['onionoo_url']
        self.ts_file = os.path.join(abs_path, "timestamp")
        self.json = self.fetch()
        self.timestamp = self.timestamp()

    def fetch(self):
        if os.path.isfile(self.ts_file):
            with open(self.ts_file, 'r') as ts_file:
                prev_timestamp = ts_file.read()
            try:
                api_response = requests.get(self.url,
                        headers={"If-Modified-Since": prev_timestamp})
            except requests.exceptions.RequestException:
                return(None)
        else:
            try:
                api_response = requests.get(self.url)
            except requests.exceptions.RequestException:
                return(None)
        
        self.statuscode = api_response.status_code
        if self.statuscode != 200:
            return(None)
        
        json_data = api_response.json()
        sorted_json = self.sort_by_bandwidth(json_data)
        trimmed_json = self.trim_platform(sorted_json)
        return(trimmed_json)

    def trim_platform(self, json):
        for relay in json['relays']:
            relay['platform'] = relay['platform'].split(' on ', 1)[1].split(' ')[0]
        return(json)

    def sort_by_bandwidth(self, json):
        json['relays'].sort(key=lambda x: x['observed_bandwidth'], reverse=True)
        return(json)

    def timestamp(self):
        timestamp = time.time()
        f_timestamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(timestamp))
        if self.json is not None:
            with open(self.ts_file, 'w', encoding='utf8') as ts_file:
                    ts_file.write(f_timestamp)
        return(f_timestamp)
