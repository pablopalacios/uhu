# Copyright (C) 2017 O.S. Systems Software LTDA.
# This software is released under the MIT License

import click

from ..config import config
from ..utils import remove_local_config
from .utils import error


@click.group(name='config')
def config_cli():
    """Configures efu utility."""


@config_cli.command(name='init')
def init_command():
    """Sets efu required initial configuration."""
    access_id = input('EasyFOTA Access Key ID: ')
    access_secret = input('EasyFota Systems Secret Access Key: ')
    config.set_initial(access_id, access_secret)


@config_cli.command(name='set')
@click.argument('entry')
@click.argument('value')
@click.option('--section', help='Section to write the configuration')
def set_command(entry, value, section):
    """Sets the given VALUE in a configuration ENTRY."""
    config.set(entry, value, section=section)


@config_cli.command(name='get')
@click.argument('entry')
@click.option('--section', help='Section to write the configuration')
def get_command(entry, section):
    """Gets the value from a given ENTRY."""
    value = config.get(entry, section=section)
    if value:
        print(value)


@click.command('cleanup')
def cleanup_command():
    """Removes efu local config file."""
    try:
        remove_local_config()
    except FileNotFoundError:
        error(1, 'Package file already deleted.')
