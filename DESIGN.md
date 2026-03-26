# pytest-cppcheck Design Document

## Overview

`pytest-cppcheck` is a pytest plugin that integrates cppcheck static analysis
into the pytest test run. C/C++ source files are collected as test items;
each file is checked with cppcheck and reported as a pass or failure in the
normal pytest output.

The motivating use case is Python projects with C extension modules, where
the developer already runs pytest for Python tests and wants cppcheck findings
surfaced in the same run without a separate lint step.

## Prior Art

- **pytest-flake8** — primary structural reference. One test item per source
  file, opt-in via CLI flag, mtime-based caching, named ini options for a
  small number of plugin-level concerns.
- **pytest-cpp** — reference for how to model a non-Python tool's output as
  a pytest `Item` with sensible repr. (Not used for file discovery.)
- **cppcheck on PyPI** — binary dependency, installed as a Python package.
  No system-level cppcheck required.

## Architecture

### Components

**Collector (`CppcheckFile`)** — a `pytest.Collector` subclass. Registered
via `pytest_collect_file`; matches files with configured extensions. Yields
a single `CppcheckItem` per file.

**Item (`CppcheckItem`)** — a `pytest.Item` subclass. `runtest()` invokes
cppcheck on the file, captures stderr, and raises `CppcheckError` if the
exit code is non-zero. `repr_failure()` formats the captured stderr for
pytest's failure output.

**Plugin module** — registers hooks, declares ini options and CLI flags,
wires everything together.

### Flow

```
pytest_collect_file
  → CppcheckFile (per matching source file)
    → CppcheckItem
      → runtest()
        → invoke cppcheck subprocess
        → exit code 0 → pass
        → exit code non-zero → raise CppcheckError(stderr)
```

## Invocation

cppcheck is always invoked with `--quiet` to suppress progress messages
(`1/2 files checked 70% done`), leaving only findings on stderr. The plugin
captures stderr for the failure report.

```
cppcheck --quiet [cppcheck_args] <filepath>
```

`--error-exitcode=1` must be included in `cppcheck_args` for the exit code
to be non-zero on findings. This is not injected automatically by the plugin —
the user configures it explicitly along with `--enable`, `--suppress`, and
any other cppcheck flags they want. This keeps the plugin's contract simple:
it runs what the user configured, and trusts the exit code.

Severity filtering, check selection, and suppression are all delegated to
cppcheck via `cppcheck_args`. The plugin has no opinion on these.

## Configuration

### Opt-in

The plugin does nothing unless `--cppcheck` is passed on the CLI, matching
the pytest-flake8 pattern. This avoids surprising users who install the
package without intending to run cppcheck on every test invocation.

### ini Options

**`cppcheck_extensions`** — file extensions to collect. Default: `.c`.
Example: `cppcheck_extensions = .c .cpp .h`

**`cppcheck_args`** — passthrough string forwarded verbatim to every cppcheck
invocation. This is the primary configuration surface. Example:

```ini
[pytest]
cppcheck_args = --enable=warning,style,performance,portability
                --check-level=exhaustive
                --error-exitcode=1
                --suppress=missingIncludeSystem
```

## Output Format

cppcheck's default gcc-style output is human-readable and goes directly into
pytest's failure report without transformation. For example:

```
FAILED src/myext.c::CPPCHECK
  src/myext.c:42:8: error: Array 'arr[10]' accessed at index 10, which is
  out of bounds. [arrayIndexOutOfBounds]
  src/myext.c:44:6: error: Null pointer dereference: p [nullPointer]
```

## Testing

The test suite should use `pytester` (pytest's built-in plugin testing
fixture) rather than mocking subprocess calls where possible. This means
tests create real temporary `.c` files with known issues and verify that
the plugin reports them correctly.

Because there is no output parsing logic, tests focus on:
- files with known errors fail the item
- files with no errors pass the item
- `cppcheck_args` are forwarded correctly
- `cppcheck_extensions` controls which files are collected
- `--quiet` is always passed

## Python Version

Target Python 3.8+. Revisit lower bound if any dependency or language
feature requires it. pytest's own supported version floor at time of
development should inform the minimum pytest version declared in
dependencies.

## Packaging

Standard `pyproject.toml`-based packaging. Entry point:

```toml
[project.entry-points."pytest11"]
cppcheck = "pytest_cppcheck.plugin"
```

Classifiers should include `Framework :: Pytest`.

`cppcheck` (PyPI) declared as a runtime dependency.

## Out of Scope (v1)

- Whole-project mode (single cppcheck invocation across all collected files)
- `unusedFunction` check support
- Caching (add in a later release using pytest's built-in cache keyed on
  file mtime, following the pytest-flake8 pattern)
- pytest-clang-tidy, pytest-cpplint (separate future projects)

## Notes on pytest-clang-tidy (future project)

### clang-tidy is viable for Python extension projects but requires care

clang-tidy requires a `compile_commands.json` by default, which setuptools/pip
builds don't generate. However it can be invoked without one by passing
compiler flags directly after `--`. The minimum viable invocation for a Python
extension project is:

```bash
clang-tidy ./src/myext.c \
  -checks=-*,clang-analyzer-*,-clang-analyzer-cplusplus*,-clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling \
  -- -isystem$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))")
```

Key findings:

- Python headers must be passed as `-isystem`, not `-I`. Using `-I` causes
  clang-tidy to analyze CPython's own headers and report warnings in e.g.
  `PyConfig` struct layout that are not the user's problem. `-isystem` marks
  them as system headers and suppresses warnings from them automatically.
- `clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling` is
  extremely noisy for C extension code — it flags every `memset` and `memcpy`
  call as insecure, recommending `memset_s`/`memcpy_s` which are optional
  Annex K functions not available on most platforms (not in glibc, only
  recently in Apple's libc). Suppress it.
- `clang-analyzer-cplusplus*` checks are irrelevant for pure C extension code.

### Plugin design implication

A pytest-clang-tidy plugin targeting Python extension projects should
automatically inject `-isystem<python_include>` into the compiler flags using
`sysconfig.get_path('include')`, rather than requiring the user to figure this
out. This is the main value-add over a bare `cppcheck_args`-style passthrough.
