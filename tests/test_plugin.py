"""Tests for pytest-cppcheck using pytester."""

# C source with an out-of-bounds access that cppcheck detects.
C_ERROR = """\
#include <stdlib.h>
int main() {
    int arr[10];
    arr[10] = 0;
    return 0;
}
"""

# C source with no issues.
C_CLEAN = """\
int main() {
    return 0;
}
"""


def test_clean_file_passes(pytester):
    pytester.makefile(".c", clean=C_CLEAN)
    result = pytester.runpytest("--cppcheck", "-v")
    result.stdout.fnmatch_lines(["*PASSED*"])
    result.assert_outcomes(passed=1)


def test_error_file_fails(pytester):
    pytester.makeini(
        "[pytest]\n"
        "cppcheck_args = --enable=warning\n"
    )
    pytester.makefile(".c", bad=C_ERROR)
    result = pytester.runpytest("--cppcheck")
    result.assert_outcomes(failed=1)


def test_stderr_in_failure_output(pytester):
    pytester.makeini(
        "[pytest]\n"
        "cppcheck_args = --enable=warning\n"
    )
    pytester.makefile(".c", bad=C_ERROR)
    result = pytester.runpytest("--cppcheck")
    result.stdout.fnmatch_lines(["*arrayIndexOutOfBounds*"])


def test_not_collected_without_flag(pytester):
    pytester.makefile(".c", clean=C_CLEAN)
    result = pytester.runpytest()
    result.assert_outcomes()


def test_custom_extensions(pytester):
    pytester.makeini(
        "[pytest]\n"
        "cppcheck_extensions = .h\n"
    )
    pytester.makefile(".h", header=C_CLEAN)
    pytester.makefile(".c", also_clean=C_CLEAN)
    pytester.makefile(".cpp", also_also_clean=C_CLEAN)
    result = pytester.runpytest("--cppcheck")
    # only .h collected, not .c or .cpp
    result.assert_outcomes(passed=1)


def test_cpp_collected_by_default(pytester):
    pytester.makefile(".cpp", clean=C_CLEAN)
    result = pytester.runpytest("--cppcheck")
    result.assert_outcomes(passed=1)


def test_quiet_flag_always_passed(pytester):
    pytester.makefile(".c", clean=C_CLEAN)
    result = pytester.runpytest("--cppcheck", "-v")
    result.assert_outcomes(passed=1)


def test_cppcheck_args_forwarded(pytester):
    """Suppress the specific error so the file passes despite the bug."""
    pytester.makeini(
        "[pytest]\n"
        "cppcheck_args = --enable=warning --suppress=arrayIndexOutOfBounds\n"
    )
    pytester.makefile(".c", bad=C_ERROR)
    result = pytester.runpytest("--cppcheck")
    result.assert_outcomes(passed=1)


def test_cache_skips_on_second_run(pytester):
    pytester.makefile(".c", clean=C_CLEAN)
    # First run: passes and populates cache
    result = pytester.runpytest("--cppcheck", "-p", "cacheprovider")
    result.assert_outcomes(passed=1)
    # Second run: skipped via cache
    result = pytester.runpytest("--cppcheck", "-p", "cacheprovider")
    result.assert_outcomes(skipped=1)


def test_cache_reruns_after_file_change(pytester):
    path = pytester.makefile(".c", clean=C_CLEAN)
    # First run
    result = pytester.runpytest("--cppcheck", "-p", "cacheprovider")
    result.assert_outcomes(passed=1)
    # Touch the file to change mtime
    import time
    time.sleep(0.1)
    path.write_text(C_CLEAN)
    # Second run: re-checked because mtime changed
    result = pytester.runpytest("--cppcheck", "-p", "cacheprovider")
    result.assert_outcomes(passed=1)


def test_cache_reruns_after_args_change(pytester):
    pytester.makefile(".c", clean=C_CLEAN)
    # First run
    result = pytester.runpytest("--cppcheck", "-p", "cacheprovider")
    result.assert_outcomes(passed=1)
    # Second run with different args: re-checked
    pytester.makeini(
        "[pytest]\n"
        "cppcheck_args = --enable=warning\n"
    )
    result = pytester.runpytest("--cppcheck", "-p", "cacheprovider")
    result.assert_outcomes(passed=1)


def test_cache_does_not_skip_failures(pytester):
    pytester.makeini(
        "[pytest]\n"
        "cppcheck_args = --enable=warning\n"
    )
    pytester.makefile(".c", bad=C_ERROR)
    # First run: fails
    result = pytester.runpytest("--cppcheck", "-p", "cacheprovider")
    result.assert_outcomes(failed=1)
    # Second run: still fails (not cached)
    result = pytester.runpytest("--cppcheck", "-p", "cacheprovider")
    result.assert_outcomes(failed=1)


def test_no_cppcheck_cache_flag(pytester):
    pytester.makefile(".c", clean=C_CLEAN)
    # First run: passes and populates cache
    result = pytester.runpytest("--cppcheck", "-p", "cacheprovider")
    result.assert_outcomes(passed=1)
    # Second run with --no-cppcheck-cache: re-checked
    result = pytester.runpytest("--cppcheck", "--no-cppcheck-cache", "-p", "cacheprovider")
    result.assert_outcomes(passed=1)
