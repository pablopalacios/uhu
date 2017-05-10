# Copyright (C) 2017 O.S. Systems Software LTDA.
# This software is released under the MIT License

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from efu.http.auth import EFOTAV1Signature


class EFOTAV1SignatureTestCase(unittest.TestCase):

    def setUp(self):
        self.request = Mock()
        self.request.headers = {
            'foo': 'bar',
            'Host': 'localhost',
            'Timestamp': '0',
            'bar': 'foo',
        }
        self.request.canonical.return_value = '000'
        self.request.date = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_hashed_canonical_request(self):
        # sha256 of 000 in hex:
        expected = '2ac9a6746aca543af8dff39894cfe8173afba21eb01c6fae33d52947222855ef'  # nopep8
        signature = EFOTAV1Signature(self.request, '', '')
        observed = signature._hashed_canonical_request()
        self.assertEqual(observed, expected)

    def test_signed_headers(self):
        expected = 'bar;foo;host;timestamp'
        signature = EFOTAV1Signature(self.request, '', '')
        observed = signature._signed_headers()
        self.assertEqual(observed, expected)

    def test_message(self):
        '''
        The expected value here is a string with 3 lines. The first line
        is the signature version. The second line is the request
        timestamp in ISO 8601 format. The third line is a sha256 hash
        of the canonical request in hexadecimal format. In this test,
        the value hashed was 000.
        '''
        expected = '''EFOTA-V1
19700101T000000Z
2ac9a6746aca543af8dff39894cfe8173afba21eb01c6fae33d52947222855ef'''
        signature = EFOTAV1Signature(self.request, '', '')
        observed = signature._message()
        self.assertEqual(observed, expected)

    def test_key(self):
        '''
        The expected value here is a hmac-sha256 hash in hexadecimal using
        EFOTA-V1-SECRET as key and 19700101 as message.
        '''
        expected = '19fbc0211973906c184462dc765703b4d44a18bbe78624bf2abfc46c49c20c29'  # nopep8
        signature = EFOTAV1Signature(self.request, '', 'SECRET')
        observed = signature._key()
        self.assertEqual(observed, expected)

    def test_signature_hash(self):
        '''
        The expected hash here comes from the previous generated ones. It
        is a hmac-sha256 using as key the expected value from the
        test_key method and as message the expected value from the
        test_message method.
        '''
        expected = 'd826360e77d1d35c16342aa3188529fefa37a63717acc391a8ccb2ec7dc053ca'  # nopep8
        signature = EFOTAV1Signature(self.request, '', 'SECRET')
        observed = signature._signature_hash()
        self.assertEqual(observed, expected)

    def test_final_signature(self):
        '''
        The signature hash used here is the same from test_signature method
        '''
        expected = 'EFOTA-V1 Credential=123ACCESSID, SignedHeaders=bar;foo;host;timestamp, Signature=d826360e77d1d35c16342aa3188529fefa37a63717acc391a8ccb2ec7dc053ca'  # nopep8
        signature = EFOTAV1Signature(self.request, '123ACCESSID', 'SECRET')
        observed = signature.signature
        self.assertEqual(observed, expected)
