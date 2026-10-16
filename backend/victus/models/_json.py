"""Strict JSON decoding shared by provider wire and decision boundaries."""

import json
import math


def strict_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate key")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("Non-finite JSON")

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Non-finite JSON")
        return result

    return json.loads(
        text, object_pairs_hook=pairs, parse_constant=reject_constant, parse_float=finite_float
    )
