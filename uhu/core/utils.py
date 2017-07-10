# Copyright (C) 2017 O.S. Systems Software LTDA.
# SPDX-License-Identifier: GPL-2.0

import json
import os
import tarfile
import tempfile
from collections import OrderedDict

import pkgschema


def dump_package(package, fn):
    """Dumps a package into a file."""
    with open(fn, 'w') as fp:
        json.dump(package, fp, indent=4, sort_keys=True)
        fp.write('\n')


def load_package(fn):
    """Loads a package from package dump file."""
    from .package import Package
    with open(fn) as fp:
        dump = json.load(fp, object_pairs_hook=OrderedDict)
    return Package(dump=dump)


def _generate_archive_name(package, output):
    if output is not None:
        return output
    return '{0.product}-{0.version}.uhupkg'.format(package)


def dump_package_archive(package, output=None, force=False):
    """Saves package as an archive. Returns genereted archive filename.

    Generated archive is a gz compressed tar file with current package
    metadata and all objects files.

    All objects are renamed to its hash and moved to the archive
    root. Objects are included without duplication and links are
    resolved.
    """
    # Checks minimum package requirements
    if package.version is None:
        raise ValueError('Cannot generate archive without package version.')
    if package.product is None:
        raise ValueError('Cannot generate archive without product UID.')
    if not package.objects.all():
        raise ValueError('Cannot generate archive without objects.')
    # Checks metadata complience
    metadata = package.to_metadata()
    try:
        pkgschema.validate_metadata(metadata)
    except pkgschema.ValidationError:
        raise ValueError('Cannot generate archive with invalid metadata.')

    # Checks archive output
    output = _generate_archive_name(package, output)
    if os.path.exists(output) and not force:
        raise FileExistsError('Archive "{}" already exists.'.format(output))

    # Writes archive
    cache = set()
    with tempfile.NamedTemporaryFile('w') as fp:
        dump_package(metadata, fp.name)
        with tarfile.open(output, mode='w:gz') as tar:
            tar.add(fp.name, arcname='metadata')
            for obj in package.objects.all():
                sha256sum = obj['sha256sum']
                if sha256sum in cache:
                    continue
                cache.add(sha256sum)
                tar.add(os.path.realpath(obj.filename), sha256sum)
    return output
