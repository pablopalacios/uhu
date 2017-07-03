# Copyright (C) 2017 O.S. Systems Software LTDA.
# SPDX-License-Identifier: GPL-2.0

import hashlib
import json
import math
import os

import requests

from ..exceptions import DownloadError, UploadError
from ..http import Request
from ..utils import (
    call, get_chunk_size, get_compressor_format, get_server_url,
    get_uncompressed_size)

from ._options import Options
from .install_condition import get_version
from .storages import STORAGES
from .upload import ObjectUploadResult
from .validators import validate_options


class Modes:
    registry = {}

    @classmethod
    def get(cls, name):
        obj_class = cls.registry.get(name)
        if obj_class is None:
            raise ValueError('There is no {} object class.'.format(name))
        return obj_class

    @classmethod
    def names(cls):
        return sorted([mode for mode in cls.registry])


class ObjectType(type):

    def __init__(cls, classname, bases, methods):
        super().__init__(classname, bases, methods)
        # register class into modes registry
        if getattr(cls, 'mode', None) is not None:
            Modes.registry[cls.mode] = cls

        if cls.allow_compression:
            cls.options.append('compressed')
            cls.options.append('required-uncompressed-size')
        if cls.allow_install_condition:
            cls.options.append('install-condition')
            cls.options.append('install-condition-version')
            cls.options.append('install-condition-pattern-type')
            cls.options.append('install-condition-pattern')
            cls.options.append('install-condition-seek')
            cls.options.append('install-condition-buffer-size')
            cls.string_template.insert(0, ('install-condition', ()))
            cls.string_template.insert(
                1, ('install-condition-pattern-type', ()))
            cls.string_template.insert(2, (
                'install-condition-pattern',
                ('install-condition-seek', 'install-condition-buffer-size')))

        # converts strings to Option classes
        cls.options = [Options.get(opt) for opt in cls.options]
        cls.required_options = [
            Options.get(opt) for opt in cls.required_options]
        cls.string_template = [
            (Options.get(opt), [Options.get(child) for child in children])
            for opt, children in cls.string_template]


class BaseObject(metaclass=ObjectType):
    mode = None
    allow_compression = False
    allow_install_condition = False
    options = []
    required_options = []
    string_template = tuple()

    @classmethod
    def is_required(cls, option):
        return option in cls.required_options

    def __init__(self, values):
        self._values = validate_options(self, values)
        self.chunk_size = get_chunk_size()
        self.md5 = None

    def template(self):
        template = {opt.metadata: value
                    for opt, value in self._values.items()
                    if not opt.volatile}
        template['mode'] = self.mode
        return template

    def metadata(self):
        self.load()
        metadata = {opt.metadata: value for opt, value in self._values.items()}
        metadata['mode'] = self.mode
        self._metadata_install_condition(metadata)
        self._metadata_compression(metadata)
        return metadata

    def _metadata_install_condition(self, metadata):
        if not self.allow_install_condition:
            return
        condition = metadata.pop('install-condition')
        if condition == 'content-diverges':
            metadata['install-if-different'] = 'sha256sum'
        elif condition == 'version-diverges':
            backend = metadata.pop('install-condition-pattern-type')
            if backend in ['linux-kernel', 'u-boot']:
                metadata['install-if-different'] = {
                    'version': get_version(self.filename, backend),
                    'pattern': backend
                }
            else:
                regexp = metadata.pop('install-condition-pattern')
                seek = metadata.pop('install-condition-seek')
                buffer_size = metadata.pop('install-condition-buffer-size')
                version = get_version(
                    self.filename, backend, pattern=regexp.encode(),
                    seek=seek, buffer_size=buffer_size)
                metadata['install-if-different'] = {
                    'version': version,
                    'pattern': {
                        'regexp': regexp,
                        'seek': seek,
                        'buffer-size': buffer_size,
                    }
                }

    def _metadata_compression(self, metadata):
        if self.allow_compression:
            compressor = get_compressor_format(self['filename'])
            size = get_uncompressed_size(self['filename'], compressor)
            if size is not None:
                metadata['compressed'] = True
                metadata['required-uncompressed-size'] = size

    @property
    def filename(self):
        """Shortcut to returns object filename option."""
        return self['filename']

    @property
    def size(self):
        """Returns the size of object file."""
        return os.path.getsize(self.filename)

    @property
    def exists(self):
        """Checks if file exsits."""
        return os.path.exists(self.filename)

    def update(self, option, value):
        """Updates a given option value."""
        self[option] = value

    def load(self, callback=None):
        """Reads object to set its size, sha256sum and MD5."""
        sha256sum = hashlib.sha256()
        md5 = hashlib.md5()
        for chunk in self:
            sha256sum.update(chunk)
            md5.update(chunk)
            call(callback, 'object_read')
        self['sha256sum'] = sha256sum.hexdigest()
        self['size'] = self.size
        self.md5 = md5.hexdigest()

    def upload(self, package_uid, callback=None):
        """Uploads object to server."""
        # First, check if we can upload the object
        url = get_server_url('/packages/{}/objects/{}'.format(
            package_uid, self['sha256sum']))
        body = json.dumps({'etag': self.md5})
        response = Request(url, 'POST', body, json=True).send()
        if response.status_code == 200:  # Object already uploaded
            result = ObjectUploadResult.EXISTS
            call(callback, 'object_read', len(self))
        elif response.status_code == 201:  # Object must be uploaded
            body = response.json()
            upload = STORAGES[body['storage']]
            success = upload(self, body['url'], callback)
            if success:
                result = ObjectUploadResult.SUCCESS
            else:
                result = ObjectUploadResult.FAIL
        else:  # It was not possible to check if we can upload
            errors = response.json().get('errors', [])
            error_msg = 'It was not possible to get url:\n{}'
            raise UploadError(error_msg.format('\n'.join(errors)))
        return result

    def download(self, url):
        """Downloads object from server."""
        if self.exists:
            return
        try:
            response = requests.get(url, stream=True)
        except requests.exceptions.ConnectionError:
            raise DownloadError('Can\'t reach the server.')
        if not response.ok:
            error_msg = 'It was not possible to download object:\n{}'
            raise DownloadError(error_msg.format(response.text))
        with open(self.filename, 'wb') as fp:
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                fp.write(chunk)

    def __setitem__(self, key, value):
        try:
            option = Options.get(key)
        except ValueError:
            raise TypeError('You must provide a registered option')
        try:
            self._values[option] = option.validate(value, self)
        except ValueError:
            raise TypeError('You must provide a valid value.')
        values = {option.metadata: value
                  for option, value in self._values.items()}
        values[key] = value
        self._values = validate_options(self, values)

    def __getitem__(self, key):
        if not isinstance(key, str):
            raise TypeError('You must provide a option metadata name')
        try:
            option = Options.get(key)
        except ValueError:
            raise TypeError('You must provide a registered option')
        if option not in self.options:
            raise ValueError(
                '{} does not support {}'.format(self.mode, option))
        return self._values.get(option)

    def __len__(self):
        """The size of a object is the number of chunks it has."""
        return math.ceil(self.size/self.chunk_size)

    def __iter__(self):
        """Yields every single chunk."""
        with open(self.filename, 'br') as fp:
            for chunk in iter(lambda: fp.read(self.chunk_size), b''):
                yield chunk

    def __str__(self):
        lines = ['{} [mode: {}]\n'.format(self.filename, self.mode)]
        for option, suboptions in self.string_template:
            value = self[option.metadata]
            if value is None:
                continue
            name = '{}:'.format(option.verbose_name)
            suboptions_value = ''
            if suboptions:
                suboptions_line = []
                for suboption in suboptions:
                    suboption_value = self[suboption.metadata]
                    if suboption_value is None:
                        continue
                    suboptions_line.append('{}: {}'.format(
                        suboption.verbose_name,
                        suboption.humanize(suboption_value)))
                if suboptions_line:
                    suboptions_value = ' [{}]'.format(
                        ', '.join(suboptions_line))
            lines.append('    {:<25}{}{}'.format(
                name, option.humanize(value), suboptions_value))
        return '\n'.join(lines)