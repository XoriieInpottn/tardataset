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


class BSONTarWriter(object):

    def __init__(self, path: str):
        self._path = path
        self._impl = TarWriter(path)
        self._meta_doc = {}

    def close(self):
        if self._meta_doc is not None:
            data = BSON.encode(self._meta_doc, codec_options=CODEC_OPTIONS)
            self._impl.write('meta.bson', data)
            self._meta_doc = None
        self._impl.close()

    @property
    def meta_doc(self):
        return self._meta_doc

    @meta_doc.setter
    def meta_doc(self, doc: dict):
        assert isinstance(doc, dict)
        self._meta_doc = doc

    def write(self, doc):
        name = f'{len(self._impl)}.bson'
        data = BSON.encode(doc, codec_options=CODEC_OPTIONS)
        self._impl.write(name, data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __len__(self):
        return self._impl.__len__()


class BSONTarReader(object):

    def __init__(self, path: str, block_size=1024):
        self._path = path
        self._impl = TarReader(path, block_size)
        self._count = len(self._impl)

        name, data = self._impl.read(self._count - 1)
        if name == 'meta.bson':
            self._count -= 1
            doc = BSON(data).decode(codec_options=CODEC_OPTIONS)
            # noinspection PyUnresolvedReferences
            self._meta_doc = {k: v for k, v in doc.items()}
        else:
            self._meta_doc = {}

    def close(self):
        self._impl.close()

    @property
    def meta_doc(self):
        return self._meta_doc

    def read(self, i: int) -> dict:
        name, data = self._impl.read(i)
        # noinspection PyTypeChecker
        return BSON(data).decode(codec_options=CODEC_OPTIONS)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __getitem__(self, i: int):
        return self.read(i)

    def __len__(self):
        return self._count


def BSONTar(path: str, mode: str):
    if mode == 'r':
        return BSONTarReader(path)
    elif mode == 'w':
        return BSONTarWriter(path)
    else:
        raise RuntimeError('"mode" should be one of {"r", "w"}.')
