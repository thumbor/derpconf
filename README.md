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
The group is optional and defaults to `'General'`:

```python
from derpconf.config import Config

Config.define('HOST', '127.0.0.1', 'Address the server listens on', 'Server')
Config.define('PORT', 8888, 'Port the server listens on', 'Server')
```

Write a configuration file. It is plain Python, and every top-level name
written in uppercase becomes a setting; lowercase names are ignored:

```python
# /etc/myapp.conf
PORT = 9000
ALLOWED_SOURCES = ['example.com', 'cdn.example.com']
```

Load it and read the values:

```python
conf = Config.load('/etc/myapp.conf')

conf.PORT                 # 9000, from the file
conf.HOST                 # '127.0.0.1', the declared default
conf['PORT']              # 9000, item access works too
conf.get('TIMEOUT', 30)   # 30, the fallback for an unknown setting
```

Reading a setting that has neither a value nor a default raises
`AttributeError`, or `KeyError` when you use `conf['...']`.

> Configuration files are executed as Python code with the privileges of your
> process. Only load files from locations you trust. See
> [SECURITY.md](https://github.com/thumbor/derpconf/blob/master/SECURITY.md).

## Where values come from

When you read a setting, derpconf checks, in order:

1. an environment variable with the same name, if you called
   `Config.allow_environment_variables()`;
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
    conf_name='myapp.conf',
    lookup_paths=[os.curdir, os.path.expanduser('~'), '/etc'],
)
```

With `path=None`, derpconf uses the first directory in `lookup_paths` that
contains `conf_name`, so list them from most to least trusted. If none
contains it, or if you pass neither, you get a `Config` that holds only
defaults. A `path` that does not exist raises `ConfigurationError`.

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
conf = Config.load('/etc/myapp.conf', defaults={'HOST': '0.0.0.0'})
```

Values in `defaults` take precedence over the `Config.define` defaults for
this instance only, and values from the file still win over both.

## Environment variables

```python
Config.allow_environment_variables()
conf = Config.load('/etc/myapp.conf')
```

```
$ PORT=9100 python app.py
```

Any environment variable whose name matches a setting now overrides it. The
value is always a string: `conf.PORT` above is `'9100'`, not `9100`, and
`DEBUG=False` gives the truthy string `'False'`, so convert values where you
use them. The switch applies to every `Config` in the process, and there is
no public call to turn it off again.

## Reloading

`conf.reload()` executes the file `conf` was loaded from again, picking up
values that changed on disk. After loading a directory, it re-reads only the
last file. You do not need to reload to see defaults declared later.

## Renaming settings

```python
Config.define('STORAGE', 'file', 'Storage backend', 'Storage')
Config.alias('OLD_STORAGE', 'STORAGE')
```

Reading or assigning `OLD_STORAGE`, in code or in a configuration file, logs a
deprecation warning and uses `STORAGE` instead. The generated sample lists
`OLD_STORAGE` among the aliases of `STORAGE`.

## Requiring settings

```python
conf.validates_presence_of('SECRET_KEY', 'DATABASE_URL')
```

Raises `ConfigurationError` when any of the given settings has neither a value
nor a default.

## Generating a sample file

```python
from derpconf.config import Config, generate_config

Config.define('HOST', '127.0.0.1', 'Address the server listens on', 'Server')
Config.define('PORT', 8888, 'Port the server listens on', 'Server')

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

Every default ends up in the sample, so never use a secret as a default value.
For a real-world example, see
[thumbor's settings](https://github.com/thumbor/thumbor/blob/master/thumbor/config.py).

## Checking a file for missing settings

```python
from derpconf.config import verify_config

verify_config('/etc/myapp.conf')
```

Prints one line, with colors, for each declared setting the file does not
assign:

```
Configuration "HOST" not found in file /etc/myapp.conf. Using "127.0.0.1" instead.
```

Called without a path, `verify_config()` takes it from `sys.argv[1]`.
`Config.verify(path)` returns the same information as a list of
`(name, default)` tuples. Both execute the file, like `Config.load`.

## Development

```
make setup    # pip install -Ue .[tests], inside a virtualenv
make test     # pyVows suite with coverage
```

CI runs the suite on Python 3.11 to 3.15. See
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
