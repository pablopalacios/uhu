# Copyright (C) 2016 O.S. Systems Software LTDA.
# This software is released under the MIT License

import json
import os

from ..utils import get_package_file
from .exceptions import (
    PackageFileExistsError, PackageFileDoesNotExistError,
    ImageDoesNotExistError
)


def load_package():
    package_fn = get_package_file()
    try:
        with open(package_fn) as fp:
            package = json.load(fp)
    except FileNotFoundError:
        raise PackageFileDoesNotExistError
    return package


def write_package(data):
    package_fn = get_package_file()
    with open(package_fn, 'w') as fp:
        json.dump(data, fp)


def create_package_file(product):
    package_fn = get_package_file()
    if os.path.exists(package_fn):
        raise PackageFileExistsError
    package = {'product': product}
    write_package(package)


def add_image(filename, options):
    package = load_package()
    options['install-mode'] = options['install_mode'].name
    del options['install_mode']

    files = package.get('files', {})
    files[filename] = options
    package['files'] = files
    write_package(package)


def remove_image(filename):
    package = load_package()
    try:
        del package['files'][filename]
    except KeyError:
        raise ImageDoesNotExistError
    write_package(package)


def list_images():
    package = load_package()
    files = package.get('files')
    for file, options in files.items():
        print('- {}'.format(file))
        for key, value in options.items():
            print('  {}: {}'.format(key, value))


def remove_package_file():
    try:
        os.remove(get_package_file())
    except FileNotFoundError:
        raise PackageFileDoesNotExistError