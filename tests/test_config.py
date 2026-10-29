#!/usr/bin/python
# -*- coding: utf-8 -*-

# derpconf
# https://github.com/thumbor/derpconf

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2012 globo.com timehome@corp.globo.com

import importlib
from collections import defaultdict
from os.path import abspath, dirname, join

import pytest

from derpconf.config import Config, ConfigurationError


def fix(name):
    return abspath(join(dirname(__file__), 'fixtures', name))


# Config keeps every definition and the environment switch in class
# attributes, so each test gets fresh ones and monkeypatch restores them.
@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    monkeypatch.setattr(Config, 'class_defaults', {})
    monkeypatch.setattr(Config, 'class_group_items', defaultdict(list))
    monkeypatch.setattr(Config, 'class_groups', [])
    monkeypatch.setattr(Config, 'class_descriptions', {})
    monkeypatch.setattr(Config, 'class_aliases', defaultdict(list))
    monkeypatch.setattr(Config, 'class_aliased_items', {})
    monkeypatch.setattr(Config, '_allow_environment_variables', False)


class TestLoading:
    def test_missing_file_raises_configuration_error(self):
        with pytest.raises(ConfigurationError):
            Config.load(fix('not-existent.conf'))

    def test_file_keeps_defaults(self):
        config = Config.load(fix('sample.conf'), defaults={
            'PROPER': 'PROPERVALUE'
        })

        assert config.PROPER == 'PROPERVALUE'

    def test_file_sets_value(self):
        config = Config.load(fix('sample.conf'))

        assert config.FOO == 'bar'

    def test_file_ignores_lower_case_names(self):
        config = Config.load(fix('sample.conf'))

        assert not hasattr(config, 'baz')

    def test_conf_name_found_in_lookup_paths(self):
        config = Config.load(
            None, conf_name='sample.conf', lookup_paths=[fix('')]
        )

        assert config.FOO == 'bar'

    def test_conf_name_not_found_keeps_defaults(self):
        config = Config.load(
            None, conf_name='not-existent.conf',
            lookup_paths=[fix('')],
            defaults={'DEFAULT': 'DEFAULTVALUE'}
        )

        assert config.DEFAULT == 'DEFAULTVALUE'

    def test_no_path_and_no_conf_name_keeps_defaults(self):
        config = Config.load(None, defaults={'DEFAULT': 'DEFAULTVALUE'})

        assert config.DEFAULT == 'DEFAULTVALUE'

    def test_defaults_are_not_shared_between_loads(self):
        Config.load(None).defaults['LEAKED'] = 'value'

        assert not hasattr(Config.load(None), 'LEAKED')

    # six imports importlib.util as a side effect; load must not rely on it.
    def test_does_not_need_importlib_util(self, monkeypatch):
        monkeypatch.delattr(importlib, 'util')

        config = Config.load(fix('sample.conf'))

        assert config.FOO == 'bar'


class TestLoadingDirectory:
    @pytest.fixture
    def config(self):
        return Config.load(fix('conf.d'), defaults={
            'PROPER': 'PROPERVALUE'
        })

    def test_keeps_defaults(self, config):
        assert config.PROPER == 'PROPERVALUE'

    def test_later_file_overrides_earlier_one(self, config):
        assert config.FOO == 'override'

    def test_later_file_adds_value(self, config):
        assert config.NEW == 'thing'

    def test_ignores_lower_case_names(self, config):
        assert not hasattr(config, 'baz')


class TestSettingAnAlias:
    @pytest.fixture
    def config(self):
        Config.alias('OTHER_ENGINE', 'ENGINE')

        return Config(OTHER_ENGINE='x')

    def test_sets_aliased_key(self, config):
        assert config.ENGINE == 'x'

    def test_sets_alias(self, config):
        assert config.OTHER_ENGINE == 'x'

    @pytest.mark.filterwarnings('error::DeprecationWarning')
    def test_logs_deprecation_on_set_and_get(self, caplog):
        Config.alias('OTHER_ENGINE', 'ENGINE')

        config = Config(OTHER_ENGINE='x')

        assert config.OTHER_ENGINE == 'x'
        assert caplog.messages == [
            'Option OTHER_ENGINE is marked as deprecated please use ENGINE instead.',
        ] * 2


class TestSettingAnAliasedKey:
    @pytest.fixture
    def config(self):
        Config.alias('LOADER_ALIAS', 'LOADER')

        return Config(LOADER='y')

    def test_sets_aliased_key(self, config):
        assert config.LOADER == 'y'

    def test_alias_reads_aliased_key(self, config):
        assert config.LOADER_ALIAS == 'y'


class TestAliasOfAlias:
    @pytest.fixture
    def config(self):
        Config.alias('STORAGE_ALIAS', 'STORAGE')
        Config.alias('STORAGE_ALIAS_ALIAS', 'STORAGE_ALIAS')

        return Config(STORAGE_ALIAS_ALIAS='z')

    def test_sets_final_key(self, config):
        assert config.STORAGE == 'z'

    def test_sets_intermediate_alias(self, config):
        assert config.STORAGE_ALIAS == 'z'

    def test_sets_outer_alias(self, config):
        assert config.STORAGE_ALIAS_ALIAS == 'z'


def test_verify_lists_keys_missing_from_file():
    Config.define('some_key', 'default', 'test key')

    assert len(Config.verify(fix('missing.conf'))) == 1


class TestItemAccess:
    @pytest.fixture
    def config(self):
        return Config.load(fix('sample.conf'))

    def test_get_item(self, config):
        assert config['FOO'] == 'bar'

    def test_set_item(self, config):
        config['X'] = 'something'

        assert config['X'] == 'something'

    def test_missing_item_raises_key_error(self, config):
        with pytest.raises(KeyError):
            config['INVALID_KEY']


def test_get_description():
    Config.define('some_key', 'default', 'test key')

    config = Config.load(fix('missing.conf'))

    assert config.get_description('some_key') == 'test key'


class TestEnvironmentVariables:
    def test_ignored_when_disabled(self, monkeypatch):
        config = Config.load(fix('sample.conf'))
        monkeypatch.setenv('FOO', 'baz')

        assert config.FOO == 'bar'

    def test_used_for_key_missing_from_configuration(self, monkeypatch):
        monkeypatch.setenv('SOME_CONFIGURATION', 'test value')
        config = Config()

        Config.allow_environment_variables()

        assert config.SOME_CONFIGURATION == 'test value'

    def test_override_value_from_file(self, monkeypatch):
        config = Config.load(fix('sample.conf'))
        Config.allow_environment_variables()
        monkeypatch.setenv('FOO', 'baz')

        assert config.FOO == 'baz'


def test_reload_keeps_default_defined_after_load():
    config = Config.load(fix('sample.conf'), defaults={
        'PROPER': 'PROPERVALUE'
    })

    Config.define('UBERFOO', 'baz', 'something', 'else')

    config.reload()

    assert hasattr(config, 'UBERFOO')
    assert config.UBERFOO == 'baz'


def test_reload_reads_file_again(tmp_path):
    path = tmp_path / 'reload.conf'
    path.write_text('FOO = "bar"\n')
    config = Config.load(str(path))

    path.write_text('FOO = "baz"\n')
    config.reload()

    assert config.FOO == 'baz'


def test_get_config_text_formats_tuple_default():
    Config.define(
        'SOME_TUPLE_VAR',
        ('foo', 'bar'),
        'Tuple var from config',
        'some config'
    )

    text = Config.get_config_text()

    assert text.split('\n') == [
        '################################# some config ##################################',
        '',
        '## Tuple var from config',
        '## Defaults to: (',
        "#    'foo',",
        "#    'bar',",
        '#)',
        '',
        '#SOME_TUPLE_VAR = (',
        "#    'foo',",
        "#    'bar',",
        '#)',
        '',
        '',
        '################################################################################',
        '',
        ''
    ]
