# Copyright (C) 2016 O.S. Systems Software LTDA.
# This software is released under the MIT License

import json
import copy
from unittest.mock import Mock, patch

from efu.repl.repl import EFURepl
from efu.repl import functions, helpers
from efu.utils import SERVER_URL_VAR

from utils import (
    HTTPTestCaseMixin, EFUTestCase, EnvironmentFixtureMixin,
    BasePullTestCase, BasePushTestCase)


class PackageStatusTestCase(
        EnvironmentFixtureMixin, HTTPTestCaseMixin, EFUTestCase):

    def setUp(self):
        self.repl = EFURepl()
        self.set_env_var(SERVER_URL_VAR, self.httpd.url(''))
        self.product = '1' * 64
        self.pkg_uid = '1'

    def test_can_get_package_status(self):
        path = '/products/{}/packages/{}/status'.format(
            self.product, self.pkg_uid)
        self.httpd.register_response(
            path, status_code=200, body=json.dumps({'status': 'success'}))

        builtins = copy.deepcopy(functions.__builtins__)
        builtins['print'] = Mock()
        with patch.dict(functions.__builtins__, builtins):
            self.repl.package.product = self.product
            self.repl.arg = self.pkg_uid
            functions.get_package_status(self.repl)
            functions.__builtins__['print'].assert_called_once_with('success')

    def test_get_package_status_raises_error_if_missing_product(self):
        self.assertIsNone(self.repl.package.product)
        with self.assertRaises(ValueError):
            functions.get_package_status(self.repl)

    def test_get_package_status_raises_error_if_missing_package_uid(self):
        self.repl.package.product = '1'
        self.assertIsNone(self.repl.arg)
        with self.assertRaises(ValueError):
            functions.get_package_status(self.repl)


class PushTestCase(BasePushTestCase):

    def setUp(self):
        super().setUp()
        self.repl = EFURepl()

    def test_can_push_package(self):
        self.repl.package.objects.add_list()
        self.repl.package.objects.add(__file__, 'raw', {'target-device': '/'})
        self.repl.package.product = self.product
        self.repl.package.version = '2.0'
        self.set_push(self.repl.package, '100')
        self.assertIsNone(self.repl.package.uid)
        functions.push_package(self.repl)
        self.assertEqual(self.repl.package.uid, '100')

    def test_push_raises_error_if_missing_product(self):
        self.repl.package.version = '2.0'
        with self.assertRaises(ValueError):
            functions.push_package(self.repl)

    def test_push_raises_error_if_missing_version(self):
        self.repl.package.product = self.product
        with self.assertRaises(ValueError):
            functions.push_package(self.repl)


class PullTestCase(BasePullTestCase):

    def setUp(self):
        super().setUp()
        self.repl = EFURepl()
        helpers.prompt = Mock()

    def test_can_pull_package_fully(self):
        self.repl.package.product = self.product
        self.repl.package.pull = Mock()
        helpers.prompt.side_effect = [self.pkg_uid, 'yes']
        functions.pull_package(self.repl)
        self.repl.package.pull.assert_called_once_with(True)

    def test_can_pull_package_metadata_only(self):
        self.repl.package.product = self.product
        self.repl.package.pull = Mock()
        helpers.prompt.side_effect = [self.pkg_uid, 'no']
        functions.pull_package(self.repl)
        self.repl.package.pull.assert_called_once_with(False)

    def test_pull_raises_error_if_missing_product(self):
        self.repl.package.version = '2.0'
        with self.assertRaises(ValueError):
            functions.pull_package(self.repl)

    def test_pull_raises_error_if_missing_uid(self):
        self.repl.package.product = self.product
        functions.prompt.side_effect = ['']
        with self.assertRaises(ValueError):
            functions.pull_package(self.repl)

    def test_pull_raises_error_if_invalid_pull_mode_answer(self):
        self.repl.package.product = self.product
        functions.prompt.side_effect = [self.pkg_uid, 'invalid']
        with self.assertRaises(ValueError):
            functions.pull_package(self.repl)