"""Strict JSON shared by the compiler, command protocol, and skill runtime."""

import json
import math


def loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON field: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Non-finite JSON value: ' + value)
    def finite(raw):
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError('Non-finite JSON number: ' + raw)
        return value
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite)
