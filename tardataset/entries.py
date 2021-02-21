#!/usr/bin/env python3


"""
@author: xi
"""

import argparse

import numpy as np

from .bsontar import BSONTar


def entry_bsontar():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='?')
    args = parser.parse_args()

    print(f'File: {args.input}')
    with BSONTar(args.input, 'r') as f:
        count = len(f)
        print(f'Count: {count}')
        if count > 0:
            doc = f[0]
            print('{')
            for name, value in doc.items():
                if isinstance(value, str):
                    value = f'"{value}"'
                elif isinstance(value, np.ndarray):
                    value = f'ndarray(dtype={value.dtype}, shape={value.shape})'
                print(f'    "{name}": {value}')
            print('}')

    return 0


if __name__ == '__main__':
    raise SystemExit(entry_bsontar())
