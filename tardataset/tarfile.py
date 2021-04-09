#!/usr/bin/env python3


"""
@author: xi
"""

import hashlib
import io
import struct
import sys
import tarfile
import time

import numpy as np
from tqdm import tqdm

INDEX_HEAD = b'TARINDEX'
UINT64 = struct.Struct('<Q')


class TarWriter(object):

    def __init__(self, path: str):
        self._path = path
        self._index = []

        self._tar = tarfile.open(path, 'w')
        self._info = tarfile.TarInfo()
        self._info.uname = 'user'
        self._info.gname = 'group'

    def close(self):
        if hasattr(self, '_tar'):
            self._tar.close()
            self._write_index()
            delattr(self, '_tar')

    def write(self, name: str, data: bytes):
        start = self._tar.fileobj.tell()
        self._index.append(start)
        self._info.name = name
        self._info.size = len(data)
        self._info.mtime = time.time()
        self._tar.addfile(self._info, io.BytesIO(data))

    def _write_index(self):
        with io.open(self._path, 'ab') as f:
            # get index head info
            index_start = f.tell()
            index_count = len(self._index)

            # write index body
            for pos in self._index:
                f.write(UINT64.pack(pos))

            # write index head info
            checksum = hashlib.md5()
            checksum.update(INDEX_HEAD)
            start_bin = UINT64.pack(index_start)
            count_bin = UINT64.pack(index_count)
            checksum.update(start_bin)
            checksum.update(count_bin)
            checksum_bin = checksum.digest()
            f.write(INDEX_HEAD)
            f.write(start_bin)
            f.write(count_bin)
            f.write(checksum_bin)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __len__(self):
        return len(self._index)


class TarReader(object):

    def __init__(self, path: str, block_size=1024):
        self._path = path
        self._block_size = block_size
        self._index = None
        self._info_dict = {}

        self._fp = io.open(path, 'rb')
        self._tar = tarfile.open(fileobj=self._fp, mode='r')
        self._read_index()

    def close(self):
        if hasattr(self, '_tar'):
            if self._tar is not None:
                self._tar.close()
            delattr(self, '_tar')
        if hasattr(self, '_fp'):
            if self._fp is not None:
                self._fp.close()
            delattr(self, '_fp')

    def _read_index(self):
        head_size = len(INDEX_HEAD)
        self._fp.seek(-(16 + UINT64.size * 2 + head_size), io.SEEK_END)
        head = self._fp.read(head_size)
        if head == INDEX_HEAD:
            self._index_start = UINT64.unpack(self._fp.read(UINT64.size))[0]
            self._index_count = UINT64.unpack(self._fp.read(UINT64.size))[0]
            self._index = np.full((self._index_count,), -1, dtype='<i8')
        else:
            print('No index found. It will take some time to build from scratch.', file=sys.stderr)
            self._index_start = None
            self._index_count = None
            self._index = []
            with tarfile.open(self._path, 'r') as tar:
                for info in tqdm(tar, leave=False):
                    self._index.append(info)

    def read(self, i):
        if i not in self._info_dict:
            pos = self._index[i]
            if pos < 0:
                i_left = (i // self._block_size) * self._block_size
                i_right = min(i_left + self._block_size, self._index_count)
                self._fp.seek(self._index_start + UINT64.size * i_left, io.SEEK_SET)
                for j in range(i_left, i_right):
                    self._index[j] = UINT64.unpack(self._fp.read(UINT64.size))[0]
                pos = self._index[i]
            self._fp.seek(pos, io.SEEK_SET)
            self._info_dict[i] = tarfile.TarInfo.fromtarfile(self._tar)
        return self._tar.extractfile(self._info_dict[i]).read()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __len__(self):
        return len(self._index)


class TarFile(object):

    def __init__(self, path: str, mode: str):
        if mode == 'r':
            self._impl = self._impl_reader = TarReader(path)
        elif mode == 'w':
            self._impl = self._impl_writer = TarWriter(path)
        else:
            raise RuntimeError('Argument "mode" should be one of {"r", "w"}')

    def close(self):
        self._impl.close()

    def write(self, name, data):
        self._impl_writer.write(name, data)

    def read(self, i):
        return self._impl_reader.read(i)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._impl.__exit__(exc_type, exc_val, exc_tb)

    def __len__(self):
        return self._impl.__len__()
