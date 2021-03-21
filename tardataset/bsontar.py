# !/usr/bin/env python3


"""
@author: xi
"""

import io

import numpy as np
from bson import BSON
from bson.binary import Binary, USER_DEFINED_SUBTYPE
from bson.codec_options import TypeCodec, CodecOptions, TypeRegistry

from .tarfile import TarWriter, TarReader


def encode_ndarray(a: np.ndarray) -> bytes:
    buf = io.BytesIO()
    buf.write(a.dtype.str.encode())
    buf.write(str(a.shape).encode())
    buf.write(a.tobytes('C'))
    return buf.getvalue()


def decode_ndarray(data: bytes) -> np.ndarray:
    dtype_end = data.find(b'(')
    shape_start = dtype_end + 1
    shape_end = data.find(b')', shape_start)
    dtype = data[:dtype_end]
    shape = tuple(int(size) for size in data[shape_start:shape_end].split(b',') if size)
    buffer = data[shape_end + 1:]
    a = np.ndarray(dtype=dtype, shape=shape, buffer=buffer)
    return np.array(a)


class NumpyCodec(TypeCodec):
    sub_type = USER_DEFINED_SUBTYPE + 1
    python_type = np.ndarray
    bson_type = Binary

    def transform_python(self, a: np.ndarray):
        data = encode_ndarray(a)
        return Binary(data, NumpyCodec.sub_type)

    def transform_bson(self, data: Binary):
        if data.subtype == NumpyCodec.sub_type:
            return decode_ndarray(data)
        return data


CODEC_OPTIONS = CodecOptions(type_registry=TypeRegistry([NumpyCodec()]))


class BSONTar(object):

    def __init__(self, path: str, mode: str, check_index=False):
        self._path = path
        self._mode = mode
        self._check_index = check_index

        self._init()

    def _init(self):
        if self._mode == 'r':
            self._impl = self._impl_reader = TarReader(self._path, check_index=self._check_index)
        elif self._mode == 'w':
            self._impl = self._impl_writer = TarWriter(self._path)
        else:
            raise RuntimeError()

    def close(self):
        self._impl.close()

    def write(self, doc):
        name = f'{len(self._impl)}.bson'
        data = BSON.encode(doc, codec_options=CODEC_OPTIONS)
        self._impl_writer.write(name, data)

    def read(self, i: int) -> dict:
        data = self._impl_reader.read(i)
        # noinspection PyTypeChecker
        return BSON(data).decode(codec_options=CODEC_OPTIONS)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._impl.__exit__(exc_type, exc_val, exc_tb)

    def __getitem__(self, i: int):
        return self.read(i)

    def __len__(self):
        return self._impl.__len__()
