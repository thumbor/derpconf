# Security Policy

## Reporting a Vulnerability

The derpconf maintainers take security vulnerabilities seriously. If you
discover a security issue in derpconf, please report it responsibly.

Please **DO NOT open a public GitHub issue** for security vulnerabilities.

Instead, please report the vulnerability privately using GitHub's
**Private Vulnerability Reporting** feature:

- Go to the repository's **Security** tab
- Click **Report a vulnerability**
- Submit the details through the GitHub Security Advisory form

Include as much information as possible to help us reproduce the issue:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- A proof of concept (PoC), if available
- Your environment (derpconf version, Python version, and how your application
  loads its configuration)

We will acknowledge receipt of your report as soon as possible and work with
you to understand and resolve the issue.

Issues in how thumbor defines or validates its own settings belong to the
[thumbor security policy](https://github.com/thumbor/thumbor/security/policy).
If you are unsure where a problem lives, report it here and we will help route
it.

## Responsible Disclosure

We ask that you follow responsible disclosure practices:

- Do not publicly disclose the vulnerability before it has been addressed.
- Allow the maintainers reasonable time to investigate and fix the issue.
- Coordinate with us before publishing advisories, blog posts, or CVEs.

Once the issue is fixed, we will publicly acknowledge your contribution unless
you prefer to remain anonymous.

## Supported Versions

Security fixes are typically provided for the most recent stable versions of
derpconf.

| Version                 | Supported      |
| ----------------------- | -------------- |
| Latest release          | ✅             |
| Previous minor versions | ⚠️ Best effort |
| Older versions          | ❌             |

Users are strongly encouraged to keep their derpconf installations up to date.

## Security Considerations When Using derpconf

derpconf configuration files are Python code. `Config.load`, `reload`,
`Config.verify` and `verify_config` execute them with the full privileges of
the process that loads them. When using derpconf in production, please
consider the following:

- Only load configuration from trusted locations. Never build the path passed
  to `Config.load` or `verify_config` from user input.
- Restrict write access to configuration files and directories to the account
  that deploys the application. When the path is a directory, every `*.conf`
  file in it is executed in alphabetical order, so anyone who can create a
  file there can run code in your application.
- Order `lookup_paths` from most to least trusted. `Config.load` uses the
  first directory that contains `conf_name`, so a writable working directory
  listed first can shadow the file under `/etc`.
- `Config.allow_environment_variables()` applies to every `Config` instance in
  the process. Any environment variable whose name matches a setting
  overrides it, so enable it only when the process environment is trusted.
- Values read from environment variables are always strings. A boolean
  setting given as `False` through the environment is the non-empty string
  `'False'`, which is truthy, so convert and validate security-sensitive
  settings before relying on them.
- Do not use secrets as default values in `Config.define`. `generate_config`
  writes every default into the sample file and `verify_config` prints the
  default used for each missing key.

Treating configuration as trusted code helps prevent issues such as an
attacker who can write a single file in a configuration directory gaining code
execution in every application that loads it.

## Acknowledgements

We appreciate the efforts of security researchers and the open-source
community in responsibly reporting vulnerabilities and helping improve the
security of derpconf.
