# pytest-cppcheck

A pytest plugin that runs [cppcheck](https://cppcheck.sourceforge.io/) static
analysis on C/C++ source files. Each file is collected as a test item and
reported as a pass or failure in the normal pytest output.

Useful for Python projects with C extension modules where you already run pytest
and want cppcheck findings surfaced in the same test run.

## Requirements

- Python 3.8+
- pytest 7.0+
- cppcheck installed on PATH (install via your system package manager, e.g.
  `apt install cppcheck`, `brew install cppcheck`)

## Installation

First, install cppcheck via your system package manager:

```
# Ubuntu/Debian
apt install cppcheck

# macOS
brew install cppcheck

# Windows
choco install cppcheck
```

Then install the plugin:

```
pip install pytest-cppcheck
```

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
cppcheck flags.

```ini
[pytest]
cppcheck_args =
    --enable=warning,style,performance,portability
    --check-level=exhaustive
    --suppress=missingIncludeSystem
```

The plugin always passes `--quiet` and `--error-exitcode=1` automatically.

### `cppcheck_extensions`

File extensions to collect. Default: `.c .cpp`.

```ini
[pytest]
cppcheck_extensions = .c .cpp .h
```

## License

MIT
