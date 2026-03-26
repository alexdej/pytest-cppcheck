import subprocess

import pytest
from cppcheck import get_cppcheck_dir

CPPCHECK_BIN = str(get_cppcheck_dir() / "cppcheck")
CACHE_KEY = "cppcheck/mtimes"


def pytest_addoption(parser):
    group = parser.getgroup("cppcheck", "cppcheck static analysis")
    group.addoption(
        "--cppcheck",
        action="store_true",
        default=False,
        help="run cppcheck on C/C++ source files",
    )
    group.addoption(
        "--no-cppcheck-cache",
        action="store_true",
        default=False,
        help="disable cppcheck caching, re-check every file",
    )
    parser.addini(
        "cppcheck_extensions",
        type="args",
        default=[".c", ".cpp"],
        help="file extensions to collect for cppcheck (default: .c .cpp)",
    )
    parser.addini(
        "cppcheck_args",
        type="args",
        default=[],
        help="extra arguments forwarded to every cppcheck invocation",
    )


def pytest_configure(config):
    if config.getoption("cppcheck"):
        config._cppcheck_mtimes = config.cache.get(CACHE_KEY, {})


def pytest_unconfigure(config):
    if hasattr(config, "_cppcheck_mtimes"):
        config.cache.set(CACHE_KEY, config._cppcheck_mtimes)


def pytest_collect_file(parent, file_path):
    if not parent.config.getoption("cppcheck"):
        return None
    extensions = parent.config.getini("cppcheck_extensions")
    if file_path.suffix in extensions:
        return CppcheckFile.from_parent(parent, path=file_path)
    return None


class CppcheckError(Exception):
    pass


class CppcheckFile(pytest.File):
    def collect(self):
        yield CppcheckItem.from_parent(self, name="CPPCHECK")


class CppcheckItem(pytest.Item):
    def setup(self):
        if self.config.getoption("no_cppcheck_cache"):
            return
        mtimes = getattr(self.config, "_cppcheck_mtimes", {})
        self._mtime = self.path.stat().st_mtime
        args = self.config.getini("cppcheck_args")
        old = mtimes.get(str(self.path))
        if old == [self._mtime, args]:
            pytest.skip("previously passed cppcheck")

    def runtest(self):
        args = self.config.getini("cppcheck_args")
        cmd = [CPPCHECK_BIN, "--quiet", "--error-exitcode=1"] + args + [str(self.path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            output = result.stderr or result.stdout
            if not output:
                output = f"cppcheck exited with code {result.returncode}"
            raise CppcheckError(output)
        # Cache only on success
        if hasattr(self.config, "_cppcheck_mtimes"):
            self._mtime = getattr(self, "_mtime", self.path.stat().st_mtime)
            self.config._cppcheck_mtimes[str(self.path)] = [
                self._mtime,
                args,
            ]

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(CppcheckError):
            return str(excinfo.value)
        return super().repr_failure(excinfo)

    def reportinfo(self):
        return self.path, None, f"{self.path}::CPPCHECK"
