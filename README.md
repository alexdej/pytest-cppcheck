# pytest-cppcheck

[![CI](https://github.com/alexdej/pytest-cppcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/alexdej/pytest-cppcheck/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pytest-cppcheck)](https://pypi.org/project/pytest-cppcheck/)
[![Python](https://img.shields.io/pypi/pyversions/pytest-cppcheck)](https://pypi.org/project/pytest-cppcheck/)
[![License](https://img.shields.io/pypi/l/pytest-cppcheck)](https://github.com/alexdej/pytest-cppcheck/blob/main/LICENSE)

A pytest plugin that runs [cppcheck](https://cppcheck.sourceforge.io/) static
analysis on C/C++ source files. Each file is collected as a test item and
reported as a pass or failure in the normal pytest output.

Useful for Python projects with C extension modules where you already run pytest
and want cppcheck findings surfaced in the same test run.

## Installation

```
pip install pytest-cppcheck
```

This pulls in cppcheck automatically via the
[cppcheck](https://pypi.org/project/cppcheck/) PyPI package. If you prefer a
specific version, install cppcheck yourself via your system package manager
(`apt install cppcheck`, `brew install cppcheck`, etc.) — the plugin uses
whichever `cppcheck` is on PATH.

## Usage

The plugin does nothing unless explicitly enabled:

```
pytest --cppcheck
```

This collects all `.c` and `.cpp` files and runs cppcheck on each one.
Files with findings fail; clean files pass.

```
PASSED src/clean.c::CPPCHECK
FAILED src/buggy.c::CPPCHECK
  src/buggy.c:42:8: error: Array 'arr[10]' accessed at index 10, which is
  out of bounds. [arrayIndexOutOfBounds]
```

You can combine `--cppcheck` with your normal test run — Python tests and
cppcheck items appear together in the results.

## Configuration

All options go in `pyproject.toml`, `pytest.ini`, or `setup.cfg` under `[pytest]`.

### `cppcheck_args`

Extra arguments forwarded to every cppcheck invocation. This is the main
configuration surface — use it for `--enable`, `--suppress`, and any other
cppcheck flags. The plugin always passes `--quiet` and `--error-exitcode=1`
automatically.

With no `cppcheck_args`, cppcheck runs its default checks (mostly
error-severity). Use `--enable` to broaden coverage. A good starting
configuration:

```ini
[pytest]
cppcheck_args =
    --enable=warning,style,performance,portability
    --check-level=exhaustive
```

### `cppcheck_extensions`

File extensions to collect. Default: `.c .cpp`.

```ini
[pytest]
cppcheck_extensions = .c .cpp .h
```

## Caching

Results are cached based on file modification time and `cppcheck_args`. On
subsequent runs, files that previously passed are skipped. The cache is
automatically invalidated when a file is modified or `cppcheck_args` changes.
Caching relies on pytest's built-in cache provider (the `.pytest_cache` directory).
If the cache provider is disabled (for example with `-p no:cacheprovider`), results
will not be cached and all files will be re-checked on each run.

To force a full re-check:

```
pytest --cppcheck --cache-clear
```

## License

MIT
