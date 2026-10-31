"""Shared bootstrap profile contract for setup and generated documentation."""
import re


def validate(value):
    if not isinstance(value, dict) or set(value) != {'version', 'profiles'} or type(value['version']) is not int or value['version'] != 1 or not isinstance(value['profiles'], dict) or not value['profiles']:
        raise ValueError('Expected bootstrap profiles version 1')
    for name, profile in value['profiles'].items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name) or not isinstance(profile, dict) or set(profile) != {'harnesses', 'copilot'} or type(profile['copilot']) is not bool:
            raise ValueError('Invalid bootstrap profile: ' + name)
        hosts = profile['harnesses']
        if not isinstance(hosts, list) or not hosts or any(host not in ('codex', 'claude', 'cursor') for host in hosts) or len(set(hosts)) != len(hosts):
            raise ValueError('Bootstrap profiles require unique supported harnesses')
    return value['profiles']
