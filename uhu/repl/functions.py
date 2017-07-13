# Copyright (C) 2017 O.S. Systems Software LTDA.
# SPDX-License-Identifier: GPL-2.0
"""Main UHU REPL command functions."""

from ..config import config
from ..core.package import Package
from ..core.updatehub import get_package_status
from ..core.utils import dump_package
from ..ui import get_callback

from . import helpers
from .helpers import prompt


# Config

@helpers.cancellable
def set_authentication():
    """Sets user access and secret keys."""
    access = prompt('UpdateHub Access Key ID: ')
    secret = prompt('UpdateHub Systems Secret Access Key: ')
    config.set_initial(access, secret)


# Product

def set_product_uid(ctx):
    """Set product UID."""
    helpers.check_arg(ctx, 'You need to pass a product id')
    ctx.package.product = ctx.arg
    ctx.prompt = helpers.set_product_prompt(ctx.arg)


# Package

def set_package_version(ctx):
    """Sets the current package version."""
    helpers.check_arg(ctx, 'You need to pass a version number')
    ctx.package.version = ctx.arg


def show_package(ctx):
    """Prints package content."""
    print(ctx.package)


def save_package(ctx):
    """Save a local package file based in current package."""
    helpers.check_arg(ctx, 'You need to pass a filename')
    dump_package(ctx.package.to_template(), ctx.arg)


# Objects

@helpers.cancellable
def add_object(ctx):
    """Add an object into the current package."""
    obj_mode = helpers.prompt_object_mode()
    options = helpers.prompt_object_options(len(ctx.package.objects), obj_mode)
    options['mode'] = obj_mode
    ctx.package.objects.create(options)


@helpers.cancellable
def remove_object(ctx):
    """Removes an object from the current package."""
    index = helpers.prompt_object_uid(ctx.package)
    ctx.package.objects.remove(index)


@helpers.cancellable
def edit_object(ctx):
    """Edit an object within the current package."""
    index = helpers.prompt_object_uid(ctx.package, 0)
    obj = ctx.package.objects.get(index=index, installation_set=0)
    option = helpers.prompt_object_option(obj)

    installation_set = None
    if not option.symmetric:
        installation_set = helpers.prompt_installation_set(ctx.package)
        obj = ctx.package.objects.get(
            index=index, installation_set=installation_set)
    current_value = obj[option.metadata]
    default = current_value if current_value else ''
    value = helpers.prompt_object_option_value(
        option, obj.mode, default=default)
    ctx.package.objects.update(
        index, option.metadata, value, installation_set=installation_set)


# Transactions

def push_package(ctx):
    """Upload the current package to server."""
    helpers.check_product(ctx)
    helpers.check_version(ctx)
    callback = get_callback()
    ctx.package.objects.load(callback)
    ctx.package.push(callback)


@helpers.cancellable
def pull_package(ctx):
    """Download and load a package from server."""
    uid = helpers.prompt_package_uid()
    full = helpers.prompt_pull()
    metadata = ctx.package.download_metadata(uid)
    package = Package(dump=metadata)
    if full:
        package.download_objects(uid)
    ctx.package = package
    dump_package(package.to_template(), ctx.local_config)


def package_status(ctx):
    """Get the status from a package already pushed to server."""
    helpers.check_product(ctx)
    helpers.check_arg(ctx, 'You need to pass a package id')
    print(get_package_status(ctx.arg))


# Supported hardware

@helpers.cancellable
def add_hardware(ctx):
    """Adds a hardware identifier to supported hardware list."""
    identifier = prompt('Hardware identifier: ').strip()
    if identifier:
        ctx.package.supported_hardware.add(identifier)


@helpers.cancellable
def remove_hardware(ctx):
    """Removes a hardware identifier from supported hardware list."""
    identifier = prompt('Hardware identifier: ').strip()
    if identifier:
        ctx.package.supported_hardware.remove(identifier)
