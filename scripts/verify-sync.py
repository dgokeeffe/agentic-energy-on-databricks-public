#!/usr/bin/env python3
"""Compare identical bounded column projections exported from Delta and Lakebase."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import re
from pathlib import Path


def canonical(value):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}[T ]', value):
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise ValueError('Timestamp export must include timezone offsets')
            return parsed.astimezone(timezone.utc).isoformat()
        except ValueError:
            raise ValueError(f'Invalid offset-bearing timestamp: {value}')
    if isinstance(value, (str, int, float)):
        try:
            number = Decimal(str(value))
            if number.is_finite():
                return number
        except InvalidOperation:
            pass
    return value


def keyed(rows, keys):
    if not rows:
        raise ValueError('An empty export does not verify a sync')
    result = {}
    for row in rows:
        normalized = {key: canonical(value) for key, value in row.items()}
        key = tuple(normalized[k] for k in keys)
        if None in key or key in result:
            raise ValueError('Export contains null or duplicate keys')
        result[key] = normalized
    return result


def compare(source, synced, keys):
    left, right = keyed(source, keys), keyed(synced, keys)
    if left != right:
        raise ValueError('Source and synced exports differ in keys, columns or values')
    return len(left)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('synced', type=Path)
    parser.add_argument('--keys', nargs='+', required=True)
    args = parser.parse_args()
    count = compare(json.loads(args.source.read_text()), json.loads(args.synced.read_text()), args.keys)
    print(f'Verified {count} rows with identical keys, columns and values')
