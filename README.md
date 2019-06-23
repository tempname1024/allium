# Tor Metrics :: [yui.cat](https://yui.cat/) source

Network-oriented Tor metrics and statistics made with love (not javascript).

* No javascript
* Static HTML/CSS generation at runtime
* Minimal library dependence (jinja2)
* Sort by ASN, country, and platform
* Respectful Onionoo queries (If-Modified-Since)

```bash
# Requirements: python3, jinja2 (pip install jinja2)

git clone https://github.com/tempname1024/tor-metrics.git
cd tor-metrics/tor-metrics
python3 generate.py

# Files are written to www/ by default
```

```
TODO:
* Per-relay page generation (display contact, exit policy, etc)
* Sort by effective family, show member count globally
* Top exit/guard/relay families (see https://nusenu.github.io/OrNetStats/)
* Interesting statistics (ASN exit concentration, IPv6-supporting relays, etc)
* Implement something similar to https://metrics.torproject.org/bubbles.html
```

This project includes country flags by [GoSquared](https://github.com/gosquared/flags) and relay flags by the [Tor Project](https://www.torproject.org/).

