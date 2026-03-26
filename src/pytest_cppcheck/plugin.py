import subprocess
import sys

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("cppcheck", "cppcheck static analysis")
    group.addoption(
        "--cppcheck",
        action="store_true",
        default=False,
        help="run cppcheck on C/C++ source files",
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
    if not config.getoption("cppcheck"):
        return
    result = subprocess.run(
        [sys.executable, "-m", "cppcheck", "--version"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise pytest.UsageError(
            "cppcheck not found. Install it with: pip install cppcheck"
        )


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
    def runtest(self):
        args = self.config.getini("cppcheck_args")
        cmd = [sys.executable, "-m", "cppcheck", "--quiet", "--error-exitcode=1"] + args + [str(self.path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            output = result.stderr or result.stdout
            if not output:
                output = f"cppcheck exited with code {result.returncode}"
            raise CppcheckError(output)

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(CppcheckError):
            return str(excinfo.value)
        return super().repr_failure(excinfo)

    def reportinfo(self):
        return self.path, None, f"{self.path}::CPPCHECK"
