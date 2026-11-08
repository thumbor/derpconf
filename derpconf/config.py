# -*- coding: utf-8 -*-

# derpconf
# https://github.com/thumbor/derpconf

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2012 globo.com timehome@corp.globo.com

import json
import logging
import os
import sys
from collections import defaultdict
from os.path import abspath, exists, isdir, join
from textwrap import fill

logger = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    pass


TRUE_VALUES = ("true", "yes", "y", "on", "1")
FALSE_VALUES = ("false", "no", "n", "off", "0")


def parse_bool(value):
    lowered = value.strip().lower()

    if lowered in TRUE_VALUES:
        return True

    if lowered in FALSE_VALUES:
        return False

    # A False default often switches off a setting that otherwise holds a
    # string, such as an allowed origin, so anything else stays as it is.
    return value


def json_parser(target_type):
    source_type = dict if target_type is dict else list

    def parse(value):
        parsed = json.loads(value)

        if not isinstance(parsed, source_type):
            raise ValueError(f"not a JSON {source_type.__name__}")

        return target_type(parsed)

    return parse


# Environment values are cast to the type of the default given to
# Config.define. Any other type, None included, keeps the raw string.
ENVIRONMENT_PARSERS = {
    bool: parse_bool,
    int: int,
    float: float,
    list: json_parser(list),
    tuple: json_parser(tuple),
    set: json_parser(set),
    dict: json_parser(dict),
}


class Config:
    class_defaults = {}
    class_group_items = defaultdict(list)
    class_groups = []
    class_descriptions = {}

    class_aliases = defaultdict(list)
    class_aliased_items = {}
    _allow_environment_variables = False
    _environment_variables_prefix = ""

    @classmethod
    def define(cls, key, value, description, group="General"):
        cls.class_defaults[key] = value
        cls.class_descriptions[key] = description
        cls.class_group_items[group].append(key)

        if group not in cls.class_groups:
            cls.class_groups.append(group)

    @classmethod
    def alias(cls, new_key, aliased_key):
        if aliased_key in cls.class_aliased_items:
            aliased_key = cls.class_aliased_items[aliased_key]
        cls.class_aliases[aliased_key].append(new_key)
        cls.class_aliased_items[new_key] = aliased_key

    @classmethod
    def _resolve_alias(cls, name):
        while name in cls.class_aliased_items:
            name = cls.class_aliased_items[name]

        return name

    @classmethod
    def get_conf_file(cls, conf_name, lookup_paths):
        for conf_path in lookup_paths:
            conf_path_file = abspath(join(conf_path, conf_name))

            if exists(conf_path_file):
                return conf_path_file

        return None

    @classmethod
    def allow_environment_variables(cls, prefix=""):
        cls._allow_environment_variables = True
        cls._environment_variables_prefix = prefix

    @classmethod
    def load(cls, path, conf_name=None, lookup_paths=None, defaults=None):
        if defaults is None:
            defaults = {}

        if path is None and conf_name is not None and lookup_paths:
            path = cls.get_conf_file(conf_name, lookup_paths)

        if path is None:
            return cls(defaults=defaults)

        if not exists(path):
            raise ConfigurationError(f"Configuration file not found at path {path}")

        conf = cls(defaults=defaults)

        if isdir(path):
            conf.config_folder = path  # pylint: disable=attribute-defined-outside-init
        else:
            conf.config_file = path  # pylint: disable=attribute-defined-outside-init

        conf.reload()

        return conf

    @classmethod
    def _read_settings(cls, path):
        if not isdir(path):
            return [(path, cls._read_file(path))]

        files = []

        for name in sorted(os.listdir(path)):
            file = path + os.sep + name

            # Not isfile: a dangling *.conf symlink must keep failing the load
            # instead of silently dropping the settings it was meant to hold.
            if name.endswith(".conf") and not isdir(file):
                files.append((file, cls._read_file(file)))

        return files

    @classmethod
    def _read_file(cls, path):
        namespace = cls._execute(path)

        return {
            name: value for name, value in namespace.items() if name.upper() == name
        }

    @staticmethod
    def _execute(path):
        # Not a ModuleType: its __spec__ = None makes linecache warn on Python
        # 3.15 when a traceback frame names a real file instead of <string>.
        namespace = {"__name__": "configuration", "__file__": os.fspath(path)}

        try:
            with open(path, encoding="utf-8") as config_file:
                code = config_file.read()

            exec(compile(code, path, "exec"), namespace)  # pylint: disable=exec-used
        except Exception as error:
            raise ConfigurationError(
                f"Error in configuration file {path}: {type(error).__name__}: {error}"
            ) from error

        return namespace

    @classmethod
    def verify(cls, path):
        if path is None:
            return []

        if not exists(path):
            raise ConfigurationError(f"Configuration file not found at path {path}")

        namespace = cls._execute(path)
        conf = cls(defaults=[])

        for name, value in namespace.items():
            if name.upper() == name:
                setattr(conf, name, value)

        not_found = []

        for key, value in cls.class_defaults.items():
            if key not in conf.__dict__:
                not_found.append((key, value))

        return not_found

    def __init__(self, **kw):
        if "defaults" in kw:
            self.defaults = kw["defaults"]

        self._items = kw
        self._loaded_names = set()

        for key, value in kw.items():
            setattr(self, key, value)

    @property
    def items(self):
        values = {}

        for key, value in self.class_defaults.items():
            values[key] = value

        for key, value in self.defaults.items():
            values[key] = value

        for key, value in self._items.items():
            values[key] = value

        return values

    def reload(self):
        # Not getattr: it also reads the environment and the defaults, and
        # neither may choose the file that gets executed.
        path = self.__dict__.get("config_folder") or self.__dict__.get("config_file")

        if path is None:
            return

        files = self._read_settings(path)
        names = {name for _, settings in files for name in settings}

        for name in self._loaded_names - names:
            self._items.pop(name, None)
            self.__dict__.pop(self._resolve_alias(name), None)

        for file, settings in files:
            self.config_file = file  # pylint: disable=attribute-defined-outside-init

            for name, value in settings.items():
                self._items[name] = value
                setattr(self, name, value)

        self._loaded_names = names

    def validates_presence_of(self, *args):
        source = getattr(self, "config_file", "your configuration file")
        source = getattr(self, "config_folder", source)

        for arg in args:
            if not hasattr(self, arg):
                raise ConfigurationError(
                    f"Configuration {arg} was not found and does not have a "
                    f"default value. Please verify {source}"
                )

    def get(self, name, default=None):
        if hasattr(self, name):
            return getattr(self, name)

        return default

    def get_description(self, name):
        if hasattr(self, name):
            return self.class_descriptions.get(name, None)
        raise KeyError(f"No config called '{name}'")

    def __setattr__(self, name, value):
        if name in self.__class__.class_aliased_items:
            logger.warning(
                "Option %s is marked as deprecated please use %s instead.",
                name,
                self.__class__.class_aliased_items[name],
            )
            self.__setattr__(self.__class__.class_aliased_items[name], value)
        else:
            super().__setattr__(name, value)

    def __getattribute__(self, name):
        if name in ["_allow_environment_variables", "_environment_variables_prefix"]:
            return super().__getattribute__(name)

        if self._allow_environment_variables:
            prefix = self._environment_variables_prefix
            value = os.environ.get(prefix + name, None)

            if value is not None:
                return type(self).parse_environment_value(name, prefix + name, value)

        return super().__getattribute__(name)

    @classmethod
    def parse_environment_value(cls, name, env_name, value):
        name = cls._resolve_alias(name)
        default_type = type(cls.class_defaults.get(name))
        parser = ENVIRONMENT_PARSERS.get(default_type)

        if parser is None or value == "":
            return value

        try:
            return parser(value)
        except (ValueError, TypeError):
            # The value may be a secret, so it is left out of the message.
            raise ConfigurationError(
                f"Environment variable {env_name} is not a valid "
                f"{default_type.__name__} for {name}"
            ) from None

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]

        if name in self.__class__.class_aliased_items:
            logger.warning(
                "Option %s is marked as deprecated please use %s instead.",
                name,
                self.__class__.class_aliased_items[name],
            )

            return self.__getattr__(self.__class__.class_aliased_items[name])

        if "defaults" in self.__dict__ and name in self.__dict__["defaults"]:
            return self.__dict__["defaults"][name]

        if name in self.__class__.class_defaults:
            return self.__class__.class_defaults[name]

        raise AttributeError(name)

    def __getitem__(self, name):
        if hasattr(self, name):
            return getattr(self, name)
        raise KeyError(f"No config called '{name}'")

    def __setitem__(self, name, value):
        setattr(self, name, value)

    @classmethod
    def get_config_text(cls):
        result = []
        max_len = 80
        separator = "#"

        for group in cls.class_groups:
            keys = cls.class_group_items[group]
            sep_size = int(round((max_len - len(group)) / 2, 0)) - 1
            group_name = separator * sep_size + " " + group + " " + separator * sep_size

            if len(group_name) < max_len:
                group_name += separator
            result.append(group_name)

            for key in keys:
                result.append("")
                value = cls.class_defaults[key]
                description = cls.class_descriptions[key]

                wrapped = fill(description, width=78, subsequent_indent="## ")

                result.append(f"## {wrapped}")

                if key in cls.class_aliases:
                    result.append(f'## Aliases: {", ".join(cls.class_aliases[key])}')
                result.append(f"## Defaults to: {format_value(value)}")
                result.append(f"#{key} = {format_value(value)}")
            result.append("")
            result.append(separator * max_len)
            result.append("")
            result.append("")

        return "\n".join(result)


def verify_config(path=None):
    if path is None:
        if len(sys.argv) < 2:
            raise ValueError("You need to specify a path to verify.")
        path = sys.argv[1]
    validation = Config.verify(path)

    blue, green, reset = "", "", ""
    if sys.stdout.isatty():
        blue, green, reset = "\033[94m", "\033[92m", "\033[0m"

    for key, default in validation:
        sys.stdout.write(
            f'Configuration "{blue}{key}{reset}" not found in file {path}. '
            f'Using "{green}{default}{reset}" instead.\n'
        )


def generate_config():
    sys.stdout.write(f"{Config.get_config_text()}\n")


SPACES = " " * 4


def format_tuple(value, tabs=0):
    separator = SPACES * (tabs + 0)
    item_separator = SPACES * (tabs + 1)
    if isinstance(value, tuple):
        start_delimiter, end_delimiter = "(", ")"
    elif isinstance(value, set):
        start_delimiter, end_delimiter = ("{", "}") if value else ("set(", ")")
    else:
        start_delimiter, end_delimiter = "[", "]"
    trailing_comma = "," if tabs > 0 else ""

    representation = ""

    if tabs != 0:
        representation += "#"
    representation += f"{separator}{start_delimiter}\n"

    for item in value:
        if isinstance(item, (tuple, list, set)):
            representation += format_tuple(item, tabs + 1)
        else:
            representation += f"#{item_separator}{format_value(item)},\n"
    representation += f"#{separator}{end_delimiter}{trailing_comma}\n"

    return representation


def format_value(value):
    if isinstance(value, str):
        return repr(value)

    if isinstance(value, (tuple, list, set)):
        return format_tuple(value)

    return str(value)
