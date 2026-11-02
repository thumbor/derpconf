#!/usr/bin/python
# -*- coding: utf-8 -*-

# derpconf
# https://github.com/thumbor/derpconf

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2012 globo.com timehome@corp.globo.com

import importlib
import os
import subprocess
import sys
import traceback
from collections import defaultdict
from os.path import abspath, dirname, join

import pytest

from derpconf.config import (
    Config,
    ConfigurationError,
    format_value,
    generate_config,
    verify_config,
)


def fix(name):
    return abspath(join(dirname(__file__), "fixtures", name))


# Config keeps every definition and the environment switch in class
# attributes, so each test gets fresh ones and monkeypatch restores them.
@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    monkeypatch.setattr(Config, "class_defaults", {})
    monkeypatch.setattr(Config, "class_group_items", defaultdict(list))
    monkeypatch.setattr(Config, "class_groups", [])
    monkeypatch.setattr(Config, "class_descriptions", {})
    monkeypatch.setattr(Config, "class_aliases", defaultdict(list))
    monkeypatch.setattr(Config, "class_aliased_items", {})
    monkeypatch.setattr(Config, "_allow_environment_variables", False)
    monkeypatch.setattr(Config, "_environment_variables_prefix", "")


class TestLoading:
    def test_missing_file_raises_configuration_error(self):
        with pytest.raises(ConfigurationError):
            Config.load(fix("not-existent.conf"))

    def test_file_keeps_defaults(self):
        config = Config.load(fix("sample.conf"), defaults={"PROPER": "PROPERVALUE"})

        assert config.PROPER == "PROPERVALUE"

    def test_file_sets_value(self):
        config = Config.load(fix("sample.conf"))

        assert config.FOO == "bar"

    def test_file_ignores_lower_case_names(self):
        config = Config.load(fix("sample.conf"))

        assert not hasattr(config, "baz")

    def test_conf_name_found_in_lookup_paths(self):
        config = Config.load(None, conf_name="sample.conf", lookup_paths=[fix("")])

        assert config.FOO == "bar"

    def test_conf_name_not_found_keeps_defaults(self):
        config = Config.load(
            None,
            conf_name="not-existent.conf",
            lookup_paths=[fix("")],
            defaults={"DEFAULT": "DEFAULTVALUE"},
        )

        assert config.DEFAULT == "DEFAULTVALUE"

    def test_no_path_and_no_conf_name_keeps_defaults(self):
        config = Config.load(None, defaults={"DEFAULT": "DEFAULTVALUE"})

        assert config.DEFAULT == "DEFAULTVALUE"

    def test_defaults_are_not_shared_between_loads(self):
        Config.load(None).defaults["LEAKED"] = "value"

        assert not hasattr(Config.load(None), "LEAKED")

    # six imports importlib.util as a side effect; load must not rely on it.
    def test_does_not_need_importlib_util(self, monkeypatch):
        monkeypatch.delattr(importlib, "util")

        config = Config.load(fix("sample.conf"))

        assert config.FOO == "bar"

    # LC_ALL=C without locale coercion or UTF-8 mode makes open() pick ASCII.
    def test_reads_file_as_utf8_whatever_the_locale(self, tmp_path):
        path = tmp_path / "utf8.conf"
        path.write_text("FOO = 'a\u00e7\u00e3o'\n", encoding="utf-8")
        env = dict(os.environ, LC_ALL="C", PYTHONCOERCECLOCALE="0", PYTHONUTF8="0")

        output = subprocess.check_output(
            [
                sys.executable,
                "-c",
                "from derpconf.config import Config; "
                f"path = {str(path)!r}; "
                "print(ascii(Config.load(path).FOO), Config.verify(path))",
            ],
            cwd=abspath(join(dirname(__file__), "..")),
            env=env,
            text=True,
        )

        assert output == "'a\\xe7\\xe3o' []\n"


class TestLoadingDirectory:
    @pytest.fixture
    def config(self):
        return Config.load(fix("conf.d"), defaults={"PROPER": "PROPERVALUE"})

    def test_keeps_defaults(self, config):
        assert config.PROPER == "PROPERVALUE"

    def test_later_file_overrides_earlier_one(self, config):
        assert config.FOO == "override"

    def test_later_file_adds_value(self, config):
        assert config.NEW == "thing"

    def test_ignores_lower_case_names(self, config):
        assert not hasattr(config, "baz")


class TestExecutingFile:
    def test_file_sees_its_own_path(self, tmp_path):
        path = tmp_path / "sample.conf"
        path.write_text("FILE = __file__\n", encoding="utf-8")

        assert Config.load(path).FILE == str(path)

    @pytest.mark.parametrize("operation", [Config.load, Config.verify])
    @pytest.mark.parametrize(
        "code, cause",
        [
            (b"FOO =\n", SyntaxError),
            (b"FOO = undefined_name\n", NameError),
            (b"import derpconf_missing_module\n", ModuleNotFoundError),
            (b"# coment\xe1rio em latin-1\nFOO = 1\n", UnicodeDecodeError),
        ],
    )
    def test_error_names_file_and_keeps_cause(self, tmp_path, operation, code, cause):
        path = tmp_path / "broken.conf"
        path.write_bytes(code)

        with pytest.raises(ConfigurationError) as error:
            operation(path)

        assert str(error.value).startswith(
            f"Error in configuration file {path}: {cause.__name__}: "
        )
        assert isinstance(error.value.__cause__, cause)

    @pytest.mark.filterwarnings("error")
    def test_traceback_points_at_failing_line(self, tmp_path):
        path = tmp_path / "broken.conf"
        path.write_text("FOO = 1\nBAR = undefined_name\n", encoding="utf-8")

        with pytest.raises(ConfigurationError) as error:
            Config.load(path)

        frame = traceback.extract_tb(error.value.__cause__.__traceback__)[-1]
        assert (frame.filename, frame.lineno) == (str(path), 2)

    def test_directory_error_names_failing_file(self, tmp_path):
        (tmp_path / "01-valid.conf").write_text("FOO = 1\n", encoding="utf-8")
        (tmp_path / "02-broken.conf").write_text("BAR =\n", encoding="utf-8")

        with pytest.raises(ConfigurationError, match="02-broken.conf: SyntaxError"):
            Config.load(str(tmp_path))

    def test_failed_reload_keeps_previous_values(self, tmp_path):
        path = tmp_path / "sample.conf"
        path.write_text("FOO = 1\n", encoding="utf-8")
        config = Config.load(path)
        path.write_text("FOO = 2\nraise ValueError('broken')\n", encoding="utf-8")

        with pytest.raises(ConfigurationError, match="ValueError: broken"):
            config.reload()

        assert config.FOO == 1


class TestSettingAnAlias:
    @pytest.fixture
    def config(self):
        Config.alias("OTHER_ENGINE", "ENGINE")

        return Config(OTHER_ENGINE="x")

    def test_sets_aliased_key(self, config):
        assert config.ENGINE == "x"

    def test_sets_alias(self, config):
        assert config.OTHER_ENGINE == "x"

    @pytest.mark.filterwarnings("error::DeprecationWarning")
    def test_logs_deprecation_on_set_and_get(self, caplog):
        Config.alias("OTHER_ENGINE", "ENGINE")

        config = Config(OTHER_ENGINE="x")

        assert config.OTHER_ENGINE == "x"
        assert (
            caplog.messages
            == [
                "Option OTHER_ENGINE is marked as deprecated "
                "please use ENGINE instead."
            ]
            * 2
        )
        assert {record.name for record in caplog.records} == {"derpconf.config"}


class TestSettingAnAliasedKey:
    @pytest.fixture
    def config(self):
        Config.alias("LOADER_ALIAS", "LOADER")

        return Config(LOADER="y")

    def test_sets_aliased_key(self, config):
        assert config.LOADER == "y"

    def test_alias_reads_aliased_key(self, config):
        assert config.LOADER_ALIAS == "y"


class TestAliasOfAlias:
    @pytest.fixture
    def config(self):
        Config.alias("STORAGE_ALIAS", "STORAGE")
        Config.alias("STORAGE_ALIAS_ALIAS", "STORAGE_ALIAS")

        return Config(STORAGE_ALIAS_ALIAS="z")

    def test_sets_final_key(self, config):
        assert config.STORAGE == "z"

    def test_sets_intermediate_alias(self, config):
        assert config.STORAGE_ALIAS == "z"

    def test_sets_outer_alias(self, config):
        assert config.STORAGE_ALIAS_ALIAS == "z"


def test_verify_lists_keys_missing_from_file():
    Config.define("some_key", "default", "test key")

    assert len(Config.verify(fix("missing.conf"))) == 1


class TestValidatesPresenceOf:
    def test_accepts_key_with_default(self):
        Config.define("SOME_KEY", "default", "test key")

        Config.load(fix("missing.conf")).validates_presence_of("SOME_KEY")

    def test_names_loaded_file(self):
        config = Config.load(fix("sample.conf"))

        with pytest.raises(ConfigurationError) as error:
            config.validates_presence_of("MISSING_KEY")

        assert str(error.value) == (
            "Configuration MISSING_KEY was not found and does not have a "
            f'default value. Please verify {fix("sample.conf")}'
        )

    def test_names_loaded_directory(self):
        config = Config.load(fix("conf.d"))

        with pytest.raises(ConfigurationError) as error:
            config.validates_presence_of("MISSING_KEY")

        assert str(error.value).endswith(f'Please verify {fix("conf.d")}')

    def test_without_file_does_not_name_thumbor(self):
        config = Config.load(None)

        with pytest.raises(ConfigurationError) as error:
            config.validates_presence_of("MISSING_KEY")

        assert str(error.value).endswith("Please verify your configuration file")


class TestItemAccess:
    @pytest.fixture
    def config(self):
        return Config.load(fix("sample.conf"))

    def test_get_item(self, config):
        assert config["FOO"] == "bar"

    def test_set_item(self, config):
        config["X"] = "something"

        assert config["X"] == "something"

    def test_missing_item_raises_key_error(self, config):
        with pytest.raises(KeyError):
            _ = config["INVALID_KEY"]


def test_get_description():
    Config.define("some_key", "default", "test key")

    config = Config.load(fix("missing.conf"))

    assert config.get_description("some_key") == "test key"


class TestEnvironmentVariables:
    def test_ignored_when_disabled(self, monkeypatch):
        config = Config.load(fix("sample.conf"))
        monkeypatch.setenv("FOO", "baz")

        assert config.FOO == "bar"

    def test_used_for_key_missing_from_configuration(self, monkeypatch):
        monkeypatch.setenv("SOME_CONFIGURATION", "test value")
        config = Config()

        Config.allow_environment_variables()

        assert config.SOME_CONFIGURATION == "test value"

    def test_override_value_from_file(self, monkeypatch):
        config = Config.load(fix("sample.conf"))
        Config.allow_environment_variables()
        monkeypatch.setenv("FOO", "baz")

        assert config.FOO == "baz"

    def test_prefix_is_prepended_to_name(self, monkeypatch):
        monkeypatch.setenv("MYPREFIX_SOME_CONFIGURATION", "test value")
        config = Config()

        Config.allow_environment_variables(prefix="MYPREFIX_")

        assert config.SOME_CONFIGURATION == "test value"

    def test_unprefixed_name_ignored_with_prefix(self, monkeypatch):
        config = Config.load(fix("sample.conf"))
        Config.allow_environment_variables(prefix="MYPREFIX_")
        monkeypatch.setenv("FOO", "baz")

        assert config.FOO == "bar"

    def test_call_without_prefix_resets_it(self, monkeypatch):
        config = Config.load(fix("sample.conf"))
        Config.allow_environment_variables(prefix="MYPREFIX_")
        Config.allow_environment_variables()
        monkeypatch.setenv("FOO", "baz")

        assert config.FOO == "baz"


class TestEnvironmentVariableTypes:
    @pytest.mark.parametrize(
        "default, raw, expected",
        [
            ("", "foo", "foo"),
            (0, "10", 10),
            (0.0, "10.5", 10.5),
            (False, "True", True),
            (True, "off", False),
            (True, "0", False),
            ([], '["foo", "bar"]', ["foo", "bar"]),
            ((), "[1, 2]", (1, 2)),
            (set(), "[1, 2]", {1, 2}),
            ({}, '{"foo": "bar"}', {"foo": "bar"}),
        ],
    )
    def test_follows_type_of_defined_default(self, monkeypatch, default, raw, expected):
        Config.define("SETTING", default, "Setting.")
        Config.allow_environment_variables()
        monkeypatch.setenv("SETTING", raw)

        value = Config().SETTING

        assert value == expected
        assert type(value) is type(expected)

    @pytest.mark.parametrize("raw", ["0123", "00", "no", "null", "1e3", "[1]"])
    def test_none_default_stays_string(self, monkeypatch, raw):
        Config.define("PASSWORD", None, "Password.")
        Config.allow_environment_variables()
        monkeypatch.setenv("PASSWORD", raw)

        assert Config().PASSWORD == raw

    def test_undefined_setting_stays_string(self, monkeypatch):
        Config.allow_environment_variables()
        monkeypatch.setenv("UNDEFINED", "123")

        assert Config().UNDEFINED == "123"

    def test_load_defaults_do_not_change_type(self, monkeypatch):
        config = Config.load(None, defaults={"NAME": "x"})
        Config.allow_environment_variables()
        monkeypatch.setenv("NAME", "123")

        assert config.NAME == "123"

    def test_alias_uses_type_of_target_default(self, monkeypatch):
        Config.define("PORT", 8888, "Port.")
        Config.alias("OLD_PORT", "PORT")
        Config.allow_environment_variables()
        monkeypatch.setenv("OLD_PORT", "9000")

        assert Config().OLD_PORT == 9000

    def test_prefix_casts_by_unprefixed_name(self, monkeypatch):
        Config.define("PORT", 8888, "Port.")
        Config.allow_environment_variables(prefix="MYAPP_")
        monkeypatch.setenv("MYAPP_PORT", "9000")

        assert Config().PORT == 9000

    @pytest.mark.parametrize("raw", ["*", "https://www.example.com", "disabled", ""])
    def test_unrecognized_boolean_keeps_raw_string(self, monkeypatch, raw):
        Config.define("ACCESS_CONTROL_ALLOW_ORIGIN_HEADER", False, "Header.")
        Config.allow_environment_variables()
        monkeypatch.setenv("ACCESS_CONTROL_ALLOW_ORIGIN_HEADER", raw)
        config = Config()

        assert config.get("ACCESS_CONTROL_ALLOW_ORIGIN_HEADER") == raw
        assert config.ACCESS_CONTROL_ALLOW_ORIGIN_HEADER == raw

    @pytest.mark.parametrize("default", [0, 0.0, False, [], (), set(), {}])
    def test_empty_value_stays_empty_string(self, monkeypatch, default):
        Config.define("SETTING", default, "Setting.")
        Config.allow_environment_variables()
        monkeypatch.setenv("SETTING", "")
        config = Config()

        assert config.get("SETTING") == ""
        assert config.SETTING == ""

    @pytest.mark.parametrize(
        "default, raw",
        [
            (0, "abc"),
            (0.0, "abc"),
            ([], "a.com,b.com"),
            ([], '{"foo": "bar"}'),
            ({}, "[1, 2]"),
            (set(), "[[1]]"),
        ],
    )
    def test_invalid_value_raises_configuration_error(self, monkeypatch, default, raw):
        Config.define("SETTING", default, "Setting.")
        Config.allow_environment_variables(prefix="MYAPP_")
        monkeypatch.setenv("MYAPP_SETTING", raw)
        config = Config()

        with pytest.raises(ConfigurationError, match="MYAPP_SETTING") as error:
            config.get("SETTING")

        assert raw not in str(error.value) or raw == ""
        assert error.value.__suppress_context__


def test_reload_keeps_default_defined_after_load():
    config = Config.load(fix("sample.conf"), defaults={"PROPER": "PROPERVALUE"})

    Config.define("UBERFOO", "baz", "something", "else")

    config.reload()

    assert hasattr(config, "UBERFOO")
    assert config.UBERFOO == "baz"


def test_reload_reads_file_again(tmp_path):
    path = tmp_path / "reload.conf"
    path.write_text('FOO = "bar"\n')
    config = Config.load(str(path))

    path.write_text('FOO = "baz"\n')
    config.reload()

    assert config.FOO == "baz"


@pytest.mark.parametrize(
    "default",
    [
        "plain",
        "it's",
        'say "hi"',
        "C:\\Users\\thumbor",
        "first\nsecond",
        ["it's", ("tab\there", "x")],
        {"a", "b"},
        set(),
        [set(), {("a", 1)}],
    ],
)
def test_uncommented_sample_evaluates_to_default(default):
    Config.define("SOME_KEY", default, "Some key")

    lines = Config.get_config_text().split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("#SOME_KEY ="))
    end = lines.index("", start)
    setting = "\n".join(line[1:] for line in lines[start:end])
    namespace = {}
    exec(setting, namespace)  # pylint: disable=exec-used

    assert all(line.startswith("#") for line in lines if line)
    assert namespace["SOME_KEY"] == default


def test_get_config_text_formats_tuple_default():
    Config.define(
        "SOME_TUPLE_VAR", ("foo", "bar"), "Tuple var from config", "some config"
    )

    text = Config.get_config_text()

    # pylint: disable=line-too-long
    assert text.split("\n") == [
        "################################# some config ##################################",
        "",
        "## Tuple var from config",
        "## Defaults to: (",
        "#    'foo',",
        "#    'bar',",
        "#)",
        "",
        "#SOME_TUPLE_VAR = (",
        "#    'foo',",
        "#    'bar',",
        "#)",
        "",
        "",
        "################################################################################",
        "",
        "",
    ]


class TestVerify:
    def test_none_path_returns_nothing(self):
        assert not Config.verify(None)

    def test_missing_file_raises_configuration_error(self):
        with pytest.raises(ConfigurationError):
            Config.verify(fix("not-existent.conf"))

    def test_key_set_in_file_is_not_listed(self):
        Config.define("FOO", "default", "set in sample.conf")
        Config.define("MISSING", "default", "not in sample.conf")

        assert Config.verify(fix("sample.conf")) == [("MISSING", "default")]


def test_items_merges_defaults_and_file_values():
    Config.define("DEFINED", "defined", "from define")
    Config.define("OVERRIDDEN", "defined", "overridden by load defaults")
    Config.define("FOO", "defined", "overridden by the file")

    config = Config.load(
        fix("sample.conf"),
        defaults={
            "OVERRIDDEN": "load",
            "FOO": "load",
        },
    )

    assert config.items["DEFINED"] == "defined"
    assert config.items["OVERRIDDEN"] == "load"
    assert config.items["FOO"] == "bar"


def test_reload_without_file_does_nothing():
    config = Config.load(None, defaults={"DEFAULT": "DEFAULTVALUE"})

    config.reload()

    assert config.DEFAULT == "DEFAULTVALUE"


class TestGet:
    @pytest.fixture
    def config(self):
        return Config.load(fix("sample.conf"))

    def test_returns_value(self, config):
        assert config.get("FOO") == "bar"

    def test_returns_default_for_missing_key(self, config):
        assert config.get("MISSING", "fallback") == "fallback"

    def test_returns_none_without_default(self, config):
        assert config.get("MISSING") is None


def test_get_description_of_missing_key_raises_key_error():
    config = Config.load(fix("sample.conf"))

    with pytest.raises(KeyError):
        config.get_description("MISSING")


def test_get_config_text_lists_aliases():
    Config.define("STORAGE", "file", "Storage backend", "Storage")
    Config.alias("OLD_STORAGE", "STORAGE")
    Config.alias("OLDER_STORAGE", "STORAGE")

    assert "## Aliases: OLD_STORAGE, OLDER_STORAGE\n" in Config.get_config_text()


class TestVerifyConfig:
    def test_prints_missing_keys_with_defaults(self, capsys):
        Config.define("SOME_KEY", "default", "test key")

        verify_config(fix("missing.conf"))

        assert capsys.readouterr().out == (
            f'Configuration "SOME_KEY" not found in file {fix("missing.conf")}. '
            'Using "default" instead.\n'
        )

    def test_colors_output_on_a_tty(self, capsys, monkeypatch):
        Config.define("SOME_KEY", "default", "test key")
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

        verify_config(fix("missing.conf"))

        assert capsys.readouterr().out == (
            'Configuration "\033[94mSOME_KEY\033[0m" not found in file '
            f'{fix("missing.conf")}. Using "\033[92mdefault\033[0m" instead.\n'
        )

    def test_prints_nothing_when_file_sets_every_key(self, capsys):
        Config.define("FOO", "default", "test key")

        verify_config(fix("sample.conf"))

        assert capsys.readouterr().out == ""

    def test_takes_path_from_argv(self, capsys, monkeypatch):
        Config.define("SOME_KEY", "default", "test key")
        monkeypatch.setattr(sys, "argv", ["verify", fix("missing.conf")])

        verify_config()

        assert "SOME_KEY" in capsys.readouterr().out

    def test_without_path_or_argv_raises_value_error(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["verify"])

        with pytest.raises(ValueError):
            verify_config()


def test_generate_config_prints_config_text(capsys):
    Config.define("SOME_KEY", "default", "test key")

    generate_config()

    assert capsys.readouterr().out == f"{Config.get_config_text()}\n"


class TestFormatValue:
    def test_quotes_string(self):
        assert format_value("text") == "'text'"

    @pytest.mark.parametrize("value", [1, 1.5, True, None, {"key": "value"}])
    def test_uses_str_for_other_scalars(self, value):
        assert format_value(value) == str(value)

    def test_formats_list_with_brackets(self):
        assert format_value(["a", "b"]) == "[\n#    'a',\n#    'b',\n#]\n"

    def test_indents_nested_tuple(self):
        assert format_value((("a", 1), ["b"])).split("\n") == [
            "(",
            "#    (",
            "#        'a',",
            "#        1,",
            "#    ),",
            "#    [",
            "#        'b',",
            "#    ],",
            "#)",
            "",
        ]
