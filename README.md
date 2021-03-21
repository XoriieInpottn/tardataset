# TarDataset

A dataset format based on BSON and tar file.

## Installation

* Install from PyPI repository.

   ```bash
   pip3 install tardataset
   ```

* Install from the development source code.

   1. Install the python dependencies.
   
   ```bash
   pip3 install tqdm numpy pymongo
   ```
   
   2. Download the code and copy the package into your project folder.
   
   ```bash
   git clone 'https://github.com/XoriieInpottn/tardataset.git'
   cd tardataset
   cp tardataset 'your/project/dir'
   ```

## Tutorial

Here, we give an example on a very simple machine learning task. Suppose we want to train a model to perform an image classification task, one important step is to construct a train dataset. To achieve this, we usually use a text file (e.g., csv, json) to store the "image path" and "label" information, and we store all the actual image files in another folder. This "text+folder" dataset can be fine in most of the situations, while it will suffer poor performance when the total number of samples is very large. The reason is that the file system is not good at reading/writing huge numbers of tiny files which are separately stored on the disk. So, storing the whole dataset in a single file is one possible way to solve this problem. 

The following examples first show how to make a tar dataset based on the "text+folder" storage, and then show how to read or iterate this tar dataset.

### Make a Tar Dataset

```python
import csv
import os

import cv2 as cv
import numpy as np

from tardataset import BSONTar

csv_path = 'train.csv'
image_dir_path = 'images'
tar_path = 'train.tar'

with csv.DictReader(csv_path) as reader, BSONTar(tar_path, 'w') as tar:
    for row in reader:
        image_path = os.path.join(image_dir_path, row['filename'])
        image = cv.imread(image_path, cv.IMREAD_COLOR)  # load the image as ndarray
        doc = {
            'feature': image.astype(np.float32) / 255.0,  # convert the image into [0, 1] range
            'label': row['label']
        }  # a data sample is represented by dict, ndarray can be used directly
        tar.write(doc)

```

### Read the Tar Dataset

```python
from tardataset import BSONTar

tar_path = 'train.tar'

with BSONTar(tar_path, 'r') as tar:
    print(len(tar), 'samples')
    doc = tar[0]  # the sample can be access by subscript, a dict will be returned
    print('feature shape', doc['feature'].shape)
    print('feature dtype', doc['feature'].dtype)
    print('label', doc['label'])

```

### Integrate with Pytorch

```python
from torch.utils.data import Dataset, DataLoader

from tardataset import BSONTar


class TarDataset(Dataset):

    def __init__(self, path, fn=None):
        self._path = path
        self._fn = fn
        self._impl = BSONTar(path, 'r')

    def close(self):
        self._impl.close()

    def __len__(self):
        return self._impl.__len__()

    def __getitem__(self, i: int):
        doc = self._impl.read(i)
        if callable(self._fn):
            doc = self._fn(doc)
        return doc


tar_path = 'train.tar'

train_loader = DataLoader(
    TarDataset(tar_path),
    batch_size=256,
    shuffle=True,
    num_workers=5
)

for epoch in range(50):
    for doc in train_loader:
        feature = doc['feature']
        label = doc['label']
        # invoke the train function of the model
        # model.train(feature, label)

```

## Technical Details

To be added...