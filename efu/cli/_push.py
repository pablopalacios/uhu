# Copyright (C) 2016 O.S. Systems Software LTDA.
# This software is released under the MIT License

from math import ceil

from progress.bar import Bar

from ..core.object import ObjectUploadResult


GREEN = '\033[92m'
RED = '\033[91m'
END = '\033[0m'

SUCCESS_MSG = '{}SUCCESS{}'.format(GREEN, END)
FAIL_MSG = '{}FAIL{}'.format(RED, END)


class PushCallback:

    def __init__(self):
        self.progress = None

    def pre_package_load(self):
        print('Calculating objects checksums:')

    def package_load(self):
        pass

    def post_package_load(self):
        pass

    def pre_object_read(self, obj):
        size = ceil(obj.size / obj.chunk_size)
        self.progress = Bar(obj.filename, max=size)

    def object_read(self):
        self.progress.next()

    def post_object_read(self):
        self.progress.finish()

    def post_object_upload(self, obj, status):
        if status == ObjectUploadResult.EXISTS:
            print(obj.filename, 'already uploaded', flush=True, end='')
            self.progress.finish()

    def push_start(self, response):
        print('Starting push: ', end='')
        if response.ok:
            print(SUCCESS_MSG)
        else:
            print(FAIL_MSG)

    def push_finish(self, pkg, response):
        print('Finishing push: ', end='')
        if response.ok:
            print(SUCCESS_MSG)
            print('Package UID: {}'.format(pkg.uid))
        else:
            print(FAIL_MSG)
