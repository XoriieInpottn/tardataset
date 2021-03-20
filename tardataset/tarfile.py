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

from tqdm import tqdm

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
            index_start = f.tell()
            index_count = len(self._index)
            checksum = hashlib.md5()
            for pos in self._index:
                pos_bin = UINT64.pack(pos)
                checksum.update(pos_bin)
                f.write(pos_bin)
            f.write(b'TARINDEX')
            f.write(UINT64.pack(index_start))
            f.write(UINT64.pack(index_count))
            f.write(checksum.digest())

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __len__(self):
        return len(self._index)


class BufferedIndex(object):

    def __init__(self, path, block_size=100):
        self._path = path
        self._block_size = block_size

        self._f = io.open(path, 'rb')
        self._f.seek(-(8 + UINT64.size * 2 + 16), io.SEEK_END)
        if self._f.read(8) != b'TARINDEX':
            raise RuntimeError('No tar index found.')
        self._start = UINT64.unpack(self._f.read(UINT64.size))[0]
        self._count = UINT64.unpack(self._f.read(UINT64.size))[0]

        self.block_dict = {}

    def close(self):
        if hasattr(self, '_f'):
            self._f.close()
            delattr(self, '_f')

    def __del__(self):
        self.close()

    def __len__(self):
        return self._count

    def __getitem__(self, i):
        block_index = i // self._block_size
        offset = i % self._block_size
        if block_index not in self.block_dict:
            self._load_block(block_index)
        return self.block_dict[block_index][offset]

    def __setitem__(self, i, value):
        block_index = i // self._block_size
        offset = i % self._block_size
        if block_index not in self.block_dict:
            self._load_block(block_index)
        self.block_dict[block_index][offset] = value

    def _load_block(self, block_index):
        block_start = block_index * self._block_size
        self._f.seek(self._start + UINT64.size * block_start, io.SEEK_SET)
        self.block_dict[block_index] = [
            UINT64.unpack(self._f.read(UINT64.size))[0]
            for _ in range(block_start, min(block_start + self._block_size, self._count))
        ]


class TarReader(object):

    def __init__(self, path: str, check_index=False):
        self._path = path
        self._check_index = check_index
        self._index = None

        self._read_index()
        self._tar = None

    def close(self):
        if hasattr(self, '_tar'):
            if self._tar is not None:
                self._tar.close()
            delattr(self, '_tar')

    def read(self, i):
        if self._tar is None:
            self._tar = tarfile.open(self._path, 'r')
        info = self._index[i]
        if isinstance(info, int):
            self._tar.fileobj.seek(info, io.SEEK_SET)
            info = tarfile.TarInfo.fromtarfile(self._tar)
            self._index[i] = info
        return self._tar.extractfile(info).read()

    def _read_index(self):
        try:
            self._index = self._load_full_index() if self._check_index else BufferedIndex(self._path)
        except RuntimeError as e:
            print(str(e), 'It will take some time to build from scratch.', file=sys.stderr)
            self._index = []
            with tarfile.open(self._path, 'r') as tar:
                for info in tqdm(tar, leave=False):
                    self._index.append(info)

    def _load_full_index(self):
        index = []
        with io.open(self._path, 'rb') as f:
            f.seek(-(8 + UINT64.size * 2 + 16), io.SEEK_END)
            if f.read(8) != b'TARINDEX':
                raise RuntimeError('No tar index found.')
            index_start = UINT64.unpack(f.read(UINT64.size))[0]
            index_count = UINT64.unpack(f.read(UINT64.size))[0]
            checksum_bin = f.read(16)
            f.seek(index_start, io.SEEK_SET)
            checksum = hashlib.md5()
            for _ in range(index_count):
                start_bin = f.read(UINT64.size)
                checksum.update(start_bin)
                start = UINT64.unpack(start_bin)[0]
                index.append(start)
            if checksum.digest() != checksum_bin:
                raise RuntimeError('Corrupted tar index.')

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
