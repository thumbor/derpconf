# derpconf

[![unittests](https://github.com/thumbor/derpconf/actions/workflows/test.yml/badge.svg)](https://github.com/thumbor/derpconf/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/derpconf.svg)](https://pypi.org/project/derpconf/)

derpconf loads Python-syntax configuration files for your application. You
declare each setting once, with a default value, a description and a group.
derpconf then reads values from a file, a directory of files or the
environment, and can write a fully commented sample file from those
declarations. It was extracted from
[thumbor](https://github.com/thumbor/thumbor), which still builds all of its
settings on it.

## Installation

```
pip install derpconf
```

derpconf supports Python 3.11 to 3.15.

## Quick start

Declare your settings, usually in a `config.py` module of your application.
The group is optional and defaults to `"General"`:

```python
from derpconf.config import Config

Config.define("HOST", "127.0.0.1", "Address the server listens on", "Server")
Config.define("PORT", 8888, "Port the server listens on", "Server")
```

Write a configuration file. It is plain Python, and every top-level name
written in uppercase becomes a setting; lowercase names are ignored:

```python
# /etc/myapp.conf
PORT = 9000
ALLOWED_SOURCES = ["example.com", "cdn.example.com"]
```

Load it and read the values:

```python
conf = Config.load("/etc/myapp.conf")

conf.PORT                 # 9000, from the file
conf.HOST                 # "127.0.0.1", the declared default
conf["PORT"]              # 9000, item access works too
conf.get("TIMEOUT", 30)   # 30, the fallback for an unknown setting
```

Reading a setting that has neither a value nor a default raises
`AttributeError`, or `KeyError` when you use `conf["..."]`.

A file that cannot be read as UTF-8, fails to compile or raises while it
runs makes `Config.load` raise `ConfigurationError`, with a message naming
the file and the original exception as its `__cause__`. Inside the file,
`__file__` holds the path it was loaded from.

> Configuration files are executed as Python code with the privileges of your
> process. Only load files from locations you trust. See
> [SECURITY.md](https://github.com/thumbor/derpconf/blob/master/SECURITY.md).

## Where values come from

When you read a setting, derpconf checks, in order:

1. an environment variable with the same name, after the prefix if you gave
   one, if you called `Config.allow_environment_variables()`;
2. the value assigned in the loaded configuration file;
3. the `defaults` dict passed to `Config.load`;
4. the default declared with `Config.define`.

Defaults are looked up every time a setting is read, so a module that calls
`Config.define` after the file was loaded still sees its default.

## Loading configuration

### Searching for the file

```python
import os

conf = Config.load(
    None,
    conf_name="myapp.conf",
    lookup_paths=["/etc", os.path.expanduser("~"), os.curdir],
)
```

With `path=None`, derpconf uses the first directory in `lookup_paths` that
contains `conf_name`, so list them from most to least trusted: above, a
`myapp.conf` under `/etc` wins over one in the working directory, and a
file dropped into the working directory cannot shadow it. If none contains
it, or if you pass neither, you get a `Config` that holds only defaults. A
`path` that does not exist raises `ConfigurationError`.

`conf_name` is joined to each directory as given, so keep it a plain file
name: a value with `..` escapes the directory, and an absolute value
replaces it.

### Loading a directory

When `path` is a directory, every file in it whose name ends in `.conf` is
loaded in alphabetical order, and later files override earlier ones:

```
/etc/myapp.d/
  10-base.conf
  20-production.conf    # wins for every setting both files assign
```

### Per-load defaults

```python
conf = Config.load("/etc/myapp.conf", defaults={"HOST": "0.0.0.0"})
```

Values in `defaults` take precedence over the `Config.define` defaults for
this instance only, and values from the file still win over both.

## Environment variables

```python
Config.allow_environment_variables()
conf = Config.load("/etc/myapp.conf")
```

```
$ PORT=9100 python app.py
```

Any environment variable whose name matches a setting now overrides it. The
value is converted to the type of the default given to `Config.define`:

| Default type | Accepted values |
| --- | --- |
| `int`, `float` | anything `int()` or `float()` accepts |
| `bool` | `true`, `yes`, `y`, `on`, `1` and `false`, `no`, `n`, `off`, `0`, in any case; any other value stays a string |
| `list`, `tuple`, `set` | a JSON array, such as `'["a.com", "b.com"]'` |
| `dict` | a JSON object |

With `Config.define("PORT", 8888, ...)`, `conf.PORT` above is `9100`, not
`"9100"`. An empty value stays the empty string, whatever the type. Any other
value that does not parse raises `ConfigurationError` naming the variable,
without echoing the value. Settings defined with a `str` or `None`
default, or any other type, and settings that were never defined keep the raw
string. The switch applies to every `Config` in the process, and there is no
public call to turn it off again.

To keep your settings apart from variables that other programs read, pass a
prefix:

```python
Config.allow_environment_variables(prefix="MYAPP_")
```

```
$ MYAPP_PORT=9100 python app.py
```

Now `MYAPP_PORT` overrides `PORT`, and a plain `PORT` in the environment is
ignored. Like the switch, the prefix applies to every `Config` in the process.
Calling `Config.allow_environment_variables()` again without a prefix drops
it, and plain names override settings again.

## Reloading

`conf.reload()` executes the file `conf` was loaded from again, picking up
values that changed on disk. After loading a directory, it re-reads every
`*.conf` file in it, including files added since. A setting that is no longer
in any file falls back to its default, or is gone when it has none, while
values assigned in code to names the files never set are kept. If a file now
fails, `reload()` raises `ConfigurationError` and keeps every value it had.
You do not need to reload to see defaults declared later.

## Renaming settings

```python
Config.define("STORAGE", "file", "Storage backend", "Storage")
Config.alias("OLD_STORAGE", "STORAGE")
```

Reading or assigning `OLD_STORAGE`, in code or in a configuration file, logs a
deprecation warning on the `derpconf.config` logger and uses `STORAGE`
instead. The generated sample lists `OLD_STORAGE` among the aliases of
`STORAGE`.

## Requiring settings

```python
conf.validates_presence_of("SECRET_KEY", "DATABASE_URL")
```

Raises `ConfigurationError` when any of the given settings has neither a value
nor a default.

## Generating a sample file

```python
from derpconf.config import Config, generate_config

Config.define("HOST", "127.0.0.1", "Address the server listens on", "Server")
Config.define("PORT", 8888, "Port the server listens on", "Server")

generate_config()
```

`generate_config()` prints the sample below to standard output, and
`Config.get_config_text()` returns it as a string:

```
#################################### Server ####################################

## Address the server listens on
## Defaults to: '127.0.0.1'
#HOST = '127.0.0.1'

## Port the server listens on
## Defaults to: 8888
#PORT = 8888

################################################################################
```

When a default is made of strings, finite numbers, booleans, `None`, lists,
tuples, sets and dicts, uncommenting its lines gives it back exactly: strings
are written with `repr()`, so quotes, backslashes and line breaks are escaped,
and sets keep their braces. Any other value is written with `str()`, which is
not always valid Python: `float("inf")` comes out as `inf`.

Every default ends up in the sample, so never use a secret as a default value.
For a real-world example, see
[thumbor's settings](https://github.com/thumbor/thumbor/blob/master/thumbor/config.py).

## Checking a file for missing settings

```python
from derpconf.config import verify_config

verify_config("/etc/myapp.conf")
```

Prints one line for each declared setting the file does not assign, colored
when standard output is a terminal:

```
Configuration "HOST" not found in file /etc/myapp.conf. Using "127.0.0.1" instead.
```

Called without a path, `verify_config()` takes it from `sys.argv[1]`.
`Config.verify(path)` returns the same information as a list of
`(name, default)` tuples. Both execute the file, like `Config.load`.

## Development

```
make setup               # uv sync: .venv with the dev dependency group
make pre-commit-install  # run the linters on every commit
make test                # pytest suite with coverage
make lint                # black, flake8, isort and pylint
```

CI runs the suite on Python 3.11 to 3.15 and the linters on Python 3.11. See
[AGENTS.md](https://github.com/thumbor/derpconf/blob/master/AGENTS.md) for the
layout of the code and how settings are resolved.

## Security

Please report vulnerabilities privately, as described in
[SECURITY.md](https://github.com/thumbor/derpconf/blob/master/SECURITY.md),
never in a public issue.

## License

derpconf is released under the MIT License. See
[LICENSE](https://github.com/thumbor/derpconf/blob/master/LICENSE).

Copyright (c) 2012 globo.com
