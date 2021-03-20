#!/usr/bin/env python3


from setuptools import setup

if __name__ == '__main__':
    with open('README.md') as file:
        long_description = file.read()
    setup(
        name='tardataset',
        packages=[
            'tardataset',
        ],
        entry_points={
            'console_scripts': [
                'bsontar = tardataset.entries:entry_bsontar'
            ]
        },
        version='0.1.2',
        keywords=('dataset', 'file format'),
        description='A dataset format based on BSON and tar file.',
        long_description_content_type='text/markdown',
        long_description=long_description,
        license='Free',
        author='xi',
        author_email='gylv@mail.ustc.edu.cn',
        url='https://github.com/XoriieInpottn/tardataset',
        platforms='any',
        classifiers=[
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
        ],
        include_package_data=True,
        zip_safe=True,
        install_requires=[
            'tqdm',
            'numpy',
            'pymongo'
        ]
    )
