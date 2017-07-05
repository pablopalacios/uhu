# Copyright (C) 2017 O.S. Systems Software LTDA.
# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from uhu.core.object import Object


class CompressedObjectTestCase(unittest.TestCase):

    def setUp(self):
        base_dir = os.path.dirname(__file__)
        self.fixtures_dir = os.path.join(base_dir, '../fixtures/compressed/')
        uncompressed_fn = os.path.join(self.fixtures_dir, 'base.txt')
        self.size = os.path.getsize(uncompressed_fn)
        self.options = {
            'mode': 'raw',
            'target-type': 'device',
            'target': '/',
        }

    def test_can_get_gzip_uncompressed_size(self):
        self.options['filename'] = os.path.join(
            self.fixtures_dir, 'base.txt.gz')
        obj = Object(self.options)
        observed = obj.to_metadata().get('required-uncompressed-size')
        self.assertEqual(observed, self.size)

    def test_can_get_lzma_uncompressed_size(self):
        self.options['filename'] = os.path.join(
            self.fixtures_dir, 'base.txt.xz')
        obj = Object(self.options)
        observed = obj.to_metadata().get('required-uncompressed-size')
        self.assertEqual(observed, self.size)

    def test_can_get_lzo_uncompressed_size(self):
        self.options['filename'] = os.path.join(
            self.fixtures_dir, 'base.txt.lzo')
        obj = Object(self.options)
        observed = obj.to_metadata().get('required-uncompressed-size')
        self.assertEqual(observed, self.size)

    def test_can_get_tar_uncompressed_size(self):
        self.options['filename'] = os.path.join(
            self.fixtures_dir, 'archive.tar.gz')
        obj = Object(self.options)
        expected = os.path.getsize(
            os.path.join(self.fixtures_dir, 'archive.tar'))
        observed = obj.to_metadata().get('required-uncompressed-size')
        self.assertEqual(observed, expected)

    def test_uncompressed_size_of_uncompressed_object_is_None(self):
        self.options['filename'] = os.path.join(
            self.fixtures_dir, 'archive.tar')
        obj = Object(self.options)
        observed = obj.to_metadata().get('required-uncompressed-size')
        self.assertIsNone(observed)

    def test_can_work_with_symbolic_links(self):
        self.options['filename'] = os.path.join(
            self.fixtures_dir, 'symbolic.gz')
        obj = Object(self.options)
        observed = obj.to_metadata().get('required-uncompressed-size')
        self.assertEqual(observed, self.size)

    def test_can_represent_compressed_object_as_metadata(self):
        self.options['filename'] = os.path.join(
            self.fixtures_dir, 'base.txt.lzo')
        obj = Object(self.options)
        metadata = obj.to_metadata()
        self.assertEqual(metadata['compressed'], True)
        self.assertEqual(metadata['required-uncompressed-size'], self.size)

    def test_can_represent_compressed_object_of_symlink_as_metadata(self):
        self.options['filename'] = os.path.join(
            self.fixtures_dir, 'symbolic.gz')
        obj = Object(self.options)
        metadata = obj.to_metadata()
        self.assertTrue(metadata['compressed'])
        self.assertEqual(metadata['required-uncompressed-size'], self.size)

    def test_cannot_overwrite_compression_properties_on_metadata(self):
        self.options['filename'] = os.path.join(
            self.fixtures_dir, 'base.txt.bz2')
        obj = Object(self.options)
        obj._compressed = True  # it's a compressed file, but not supported
        obj.compressor = 'gzip'  # and it is a bz2, not a gzip.
        metadata = obj.to_metadata()  # luckily metadata will ignore all this
        self.assertIsNone(metadata.get('compressed'))
        self.assertIsNone(metadata.get('required-uncompressed-size'))

    def test_updating_filename_cleans_compression(self):
        uncompressed_fn = os.path.join(self.fixtures_dir, 'base.txt')
        compressed_fn = os.path.join(self.fixtures_dir, 'base.txt.gz')
        self.options['filename'] = uncompressed_fn

        obj = Object(self.options)
        metadata = obj.to_metadata()
        self.assertIsNone(metadata.get('compressed'))

        obj.update('filename', compressed_fn)
        metadata = obj.to_metadata()
        self.assertEqual(metadata['compressed'], True)

        obj.update('filename', uncompressed_fn)
        metadata = obj.to_metadata()
        self.assertIsNone(metadata.get('compressed'))
