import argparse
import logging
import os
import platform
import subprocess
import sys
import warnings
from configparser import RawConfigParser
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from shlex import split as shlex_split
from textwrap import dedent
from typing import Generator, List

import pytest
from testfixtures import LogCapture

import bumpversion
from bumpversion import exceptions
from bumpversion.cli import DESCRIPTION, main, split_args_in_optional_and_positional

if sys.version_info >= (3, 11):
    from contextlib import chdir
else:
    from contextlib import AbstractContextManager

    class chdir(AbstractContextManager):  # copied from source code of Python3.11
        """Non thread-safe context manager to change the current working directory."""

        def __init__(self, path):
            self.path = path
            self._old_cwd = []

        def __enter__(self):
            self._old_cwd.append(os.getcwd())
            os.chdir(self.path)

        def __exit__(self, *excinfo):
            os.chdir(self._old_cwd.pop())


def _get_subprocess_env():
    env = os.environ.copy()
    env["HGENCODING"] = "utf-8"
    return env


SUBPROCESS_ENV = _get_subprocess_env()
call = partial(subprocess.call, env=SUBPROCESS_ENV, shell=True)
check_call = partial(subprocess.check_call, env=SUBPROCESS_ENV)
check_output = partial(subprocess.check_output, env=SUBPROCESS_ENV)
run = partial(subprocess.run, env=SUBPROCESS_ENV)

xfail_if_no_git = pytest.mark.xfail(
    call("git version") != 0, reason="git is not installed"
)

xfail_if_no_hg = pytest.mark.xfail(
    call("hg version") != 0, reason="hg is not installed"
)

VCS_GIT = pytest.param("git", marks=xfail_if_no_git())
VCS_MERCURIAL = pytest.param("hg", marks=xfail_if_no_hg())
COMMIT = "[bumpversion]\ncommit = True"
COMMIT_NOT_TAG = "[bumpversion]\ncommit = True\ntag = False"


@pytest.fixture(params=[VCS_GIT, VCS_MERCURIAL])
def vcs(request):
    """Return all supported VCS systems (git, hg)."""
    return request.param


@pytest.fixture(params=[VCS_GIT])
def git(request):
    """Return git as VCS (not hg)."""
    return request.param


@pytest.fixture(params=[".bumpversion.cfg", "setup.cfg"])
def configfile(request):
    """Return both config-file styles ('.bumpversion.cfg', 'setup.cfg')."""
    return request.param


@pytest.fixture(
    params=[
        "file",
        "file(suffix)",
        "file (suffix with space)",
        "file (suffix lacking closing paren",
    ]
)
def file_keyword(request):
    """Return multiple possible styles for the bumpversion:file keyword."""
    return request.param


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Generator[Path, None, None]:
    with chdir(tmp_path):
        yield tmp_path


try:
    RawConfigParser(empty_lines_in_values=False)
    using_old_configparser = False
except TypeError:
    using_old_configparser = True

xfail_if_old_configparser = pytest.mark.xfail(
    using_old_configparser, reason="configparser doesn't support empty_lines_in_values"
)


def _mock_calls_to_string(called_mock) -> List[str]:
    return [
        "{}|{}|{}".format(
            name,
            args[0] if len(args) > 0 else args,
            repr(kwargs) if len(kwargs) > 0 else "",
        )
        for name, args, kwargs in called_mock.mock_calls
    ]


EXPECTED_OPTIONS = r"""
[-h]
[--config-file FILE]
[--verbose]
[--list]
[--allow-dirty]
[--parse REGEX]
[--serialize FORMAT]
[--search SEARCH]
[--replace REPLACE]
[--current-version VERSION]
[--no-configured-files]
[--dry-run]
--new-version VERSION
[--commit | --no-commit]
[--tag | --no-tag]
[--sign-tags | --no-sign-tags]
[--tag-name TAG_NAME]
[--tag-message TAG_MESSAGE]
[--message COMMIT_MSG]
[--message-emoji MESSAGE_EMOJI]
part
[file ...]
""".strip().splitlines()

EXPECTED_USAGE = (
    r"""

%s

positional arguments:
  part                  Part of the version to be bumped.
  file                  Files to change (default: [])

options:
  -h, --help            show this help message and exit
  --config-file FILE    Config file to read most of the variables from
                        (default: .bumpversion.cfg)
  --verbose             Print verbose logging to stderr (default: 0)
  --list                List machine readable information (default: False)
  --allow-dirty         Don't abort if working directory is dirty (default:
                        False)
  --parse REGEX         Regex parsing the version string (default:
                        (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+))
  --serialize FORMAT    How to format what is parsed back to a version
                        (default: ['{major}.{minor}.{patch}'])
  --search SEARCH       Template for complete string to search (default:
                        {current_version})
  --replace REPLACE     Template for complete string to replace (default:
                        {new_version})
  --current-version VERSION
                        Version that needs to be updated (default: None)
  --no-configured-files
                        Only replace the version in files specified on the
                        command line, ignoring the files from the
                        configuration file. (default: False)
  --dry-run, -n         Don't write any files, just pretend. (default: False)
  --new-version VERSION
                        New version that should be in the files (default:
                        None)
  --commit              Commit to version control (default: False)
  --no-commit           Do not commit to version control
  --tag                 Create a tag in version control (default: False)
  --no-tag              Do not create a tag in version control
  --sign-tags           Sign tags if created (default: False)
  --no-sign-tags        Do not sign tags if created
  --tag-name TAG_NAME   Tag name (only works with --tag) (default:
                        v{new_version})
  --tag-message TAG_MESSAGE
                        Tag message (default: Bump version: {current_version}
                        → {new_version})
  --message COMMIT_MSG, -m COMMIT_MSG
                        Commit message (default: Bump version:
                        {current_version} → {new_version})
  --message-emoji MESSAGE_EMOJI
                        Prefix emoji of commit message (default: )
"""
    % DESCRIPTION
).lstrip()


def _maybe_out(out: str) -> str:
    # Usage string have diff prompt in mac os
    if EXPECTED_USAGE not in out:
        a, b = ("options:", "optional arguments:")
        if a not in out:
            a, b = b, a
        out = out.replace(a, b)
    return out


def test_usage_string(tmp_dir: Path, capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])

    out, err = capsys.readouterr()
    assert err == ""

    for option_line in EXPECTED_OPTIONS:
        assert option_line in out, "Usage string is missing {}".format(option_line)
    assert EXPECTED_USAGE in _maybe_out(out)


def test_usage_string_fork(tmp_dir):
    if platform.system() == "Windows":
        # There are encoding problems on Windows with the encoding of →
        tmp_dir.joinpath(".bumpversion.cfg").write_text(
            dedent("""
             [bumpversion]
             message: Bump version: {current_version} to {new_version}
             tag_message: 'Bump version: {current_version} to {new_version}
             """)
        )

    try:
        output = check_output(
            "bumpversion --help", shell=True, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        output = e.output

    if b"usage: bumpversion [-h]" not in output:
        print(output)

    assert b"usage: bumpversion [-h]" in output


def test_regression_help_in_work_dir(tmp_dir, capsys, vcs):
    tmp_dir.joinpath("some_source.txt").write_text("1.7.2013")
    check_call([vcs, "init"])
    check_call([vcs, "add", "some_source.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])
    check_call([vcs, "tag", "v1.7.2013"])

    with pytest.raises(SystemExit):
        main(["--help"])

    out, err = capsys.readouterr()

    for option_line in EXPECTED_OPTIONS:
        assert option_line in out, "Usage string is missing {}".format(option_line)

    if vcs == "git":
        assert "Version that needs to be updated (default: 1.7.2013)" in out
    else:
        assert EXPECTED_USAGE in _maybe_out(out)


def test_defaults_in_usage_with_config(tmp_dir, capsys):
    tmp_dir.joinpath("my_defaults.cfg").write_text("""[bumpversion]
current_version: 18
new_version: 19
[bumpversion:file:file1]
[bumpversion:file:file2]
[bumpversion:file:file3]""")
    with pytest.raises(SystemExit):
        main(["--config-file", "my_defaults.cfg", "--help"])

    out, err = capsys.readouterr()

    assert "Version that needs to be updated (default: 18)" in out
    assert "New version that should be in the files (default: 19)" in out
    assert "[--current-version VERSION]" in out
    assert "[--new-version VERSION]" in out
    assert "[file ...]" in out


def test_missing_explicit_config_file(tmp_dir):
    with pytest.raises(argparse.ArgumentTypeError):
        main(["--config-file", "missing.cfg"])


def test_simple_replacement(tmp_dir):
    tmp_dir.joinpath("VERSION").write_text("1.2.0")
    main(shlex_split("patch --current-version 1.2.0 --new-version 1.2.1 VERSION"))
    assert tmp_dir.joinpath("VERSION").read_text() == "1.2.1"


def test_simple_replacement_in_utf8_file(tmp_dir):
    version_file = tmp_dir.joinpath("VERSION")
    version_file.write_bytes("Kröt1.3.0".encode())
    cmd = f"patch --verbose --current-version 1.3.0 --new-version 1.3.1 {version_file.name}"
    main(shlex_split(cmd))
    out = version_file.read_bytes()
    assert "'Kr\\xc3\\xb6t1.3.1'" in repr(out)


def test_config_file(tmp_dir):
    tmp_dir.joinpath("file1").write_text("0.9.34")
    tmp_dir.joinpath("my_bump_config.cfg").write_text("""[bumpversion]
current_version: 0.9.34
new_version: 0.9.35
[bumpversion:file:file1]""")

    main(shlex_split("patch --config-file my_bump_config.cfg"))

    assert tmp_dir.joinpath("file1").read_text() == "0.9.35"


def test_default_config_files(tmp_dir, configfile):
    tmp_dir.joinpath("file2").write_text("0.10.2")
    tmp_dir.joinpath(configfile).write_text("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
[bumpversion:file:file2]""")

    main(["patch"])

    assert tmp_dir.joinpath("file2").read_text() == "0.10.3"


def test_glob_keyword(tmp_dir, configfile):
    tmp_dir.joinpath("file1.txt").write_text("0.9.34")
    tmp_dir.joinpath("file2.txt").write_text("0.9.34")
    tmp_dir.joinpath(configfile).write_text("""[bumpversion]
current_version: 0.9.34
new_version: 0.9.35
[bumpversion:glob:*.txt]""")

    main(["patch"])
    assert tmp_dir.joinpath("file1.txt").read_text() == "0.9.35"
    assert tmp_dir.joinpath("file2.txt").read_text() == "0.9.35"


def test_glob_keyword_recursive(tmp_dir, configfile):
    subdir = tmp_dir / "subdir"
    subdir.mkdir()
    subdir.joinpath("subdir2").mkdir()
    file1 = subdir.joinpath("file1.txt")
    file1.write_text("0.9.34")
    file2 = subdir / "subdir2" / "file2.txt"
    file2.write_text("0.9.34")
    tmp_dir.joinpath(configfile).write_text("""[bumpversion]
current_version: 0.9.34
new_version: 0.9.35
[bumpversion:glob:**/*.txt]""")

    main(["patch"])
    assert file1.read_text() == "0.9.35"
    assert file2.read_text() == "0.9.35"


def test_file_keyword_with_suffix_is_accepted(tmp_dir, configfile, file_keyword):
    tmp_dir.joinpath("file2").write_text("0.10.2")
    tmp_dir.joinpath(configfile).write_text(
        """[bumpversion]
    current_version: 0.10.2
    new_version: 0.10.3
    [bumpversion:%s:file2]
    """
        % file_keyword
    )

    main(["patch"])

    assert tmp_dir.joinpath("file2").read_text() == "0.10.3"


def test_multiple_config_files(tmp_dir):
    tmp_dir.joinpath("file2").write_text("0.10.2")
    tmp_dir.joinpath("setup.cfg").write_text("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
[bumpversion:file:file2]""")
    tmp_dir.joinpath(".bumpversion.cfg").write_text("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.4
[bumpversion:file:file2]""")

    main(["patch"])

    assert tmp_dir.joinpath("file2").read_text() == "0.10.4"


def test_single_file_processed_twice(tmp_dir):
    """
    Verify that a single file "file2" can be processed twice.

    Use two file_ entries, both with a different suffix after
    the underscore.
    Employ different parse/serialize and search/replace configs
    to verify correct interpretation.
    """
    tmp_dir.joinpath("file2").write_text("dots: 0.10.2\ndashes: 0-10-2")
    tmp_dir.joinpath("setup.cfg").write_text("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
[bumpversion:file:file2]""")
    tmp_dir.joinpath(".bumpversion.cfg").write_text(r"""[bumpversion]
current_version: 0.10.2
new_version: 0.10.4
[bumpversion:file (version with dots):file2]
search = dots: {current_version}
replace = dots: {new_version}
[bumpversion:file (version with dashes):file2]
search = dashes: {current_version}
replace = dashes: {new_version}
parse = (?P<major>\d+)-(?P<minor>\d+)-(?P<patch>\d+)
serialize = {major}-{minor}-{patch}
""")

    main(["patch"])

    assert tmp_dir.joinpath("file2").read_text() == "dots: 0.10.4\ndashes: 0-10-4"


def test_config_file_is_updated(tmp_dir):
    tmp_dir.joinpath("file3").write_text("0.0.13")
    tmp_dir.joinpath(".bumpversion.cfg").write_text("""[bumpversion]
current_version: 0.0.13
new_version: 0.0.14
[bumpversion:file:file3]""")

    main(["patch", "--verbose"])

    assert (
        tmp_dir.joinpath(".bumpversion.cfg").read_text()
        == """[bumpversion]
current_version = 0.0.14

[bumpversion:file:file3]
"""
    )


def test_dry_run(tmp_dir, vcs):
    config = """[bumpversion]
current_version = 0.12.0
tag = True
commit = True
message = DO NOT BUMP VERSIONS WITH THIS FILE
[bumpversion:file:file4]
"""

    version = "0.12.0"

    tmp_dir.joinpath("file4").write_text(version)
    tmp_dir.joinpath(".bumpversion.cfg").write_text(config)

    check_call([vcs, "init"])
    check_call([vcs, "add", "file4"])
    check_call([vcs, "add", ".bumpversion.cfg"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["patch", "--dry-run"])

    assert config == tmp_dir.joinpath(".bumpversion.cfg").read_text()
    assert version == tmp_dir.joinpath("file4").read_text()

    vcs_log = check_output([vcs, "log"]).decode("utf-8")

    assert "initial commit" in vcs_log
    assert "DO NOT" not in vcs_log


def test_dry_run_verbose_log(tmp_dir, vcs):
    version = "0.12.0"
    patch = "0.12.1"
    v_parts = version.split(".")
    p_parts = patch.split(".")
    file = "file4"
    message = "DO NOT BUMP VERSIONS WITH THIS FILE"
    config = """[bumpversion]
current_version = {version}
tag = True
commit = True
message = {message}

[bumpversion:file:{file}]

""".format(version=version, file=file, message=message)

    bumpcfg = ".bumpversion.cfg"
    tmp_dir.joinpath(file).write_text(version)
    tmp_dir.joinpath(bumpcfg).write_text(config)

    check_call([vcs, "init"])
    check_call([vcs, "add", file])
    check_call([vcs, "add", bumpcfg])
    check_call([vcs, "commit", "-m", "initial commit"])

    with LogCapture(level=logging.INFO) as log_capture:
        main(["patch", "--dry-run", "--verbose"])

    vcs_name = "Mercurial" if vcs == "hg" else "Git"
    log_capture.check_present(
        # generic --verbose entries
        ("bumpversion.cli", "INFO", "Reading config file {}:".format(bumpcfg)),
        ("bumpversion.cli", "INFO", config),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '{}' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'".format(
                version
            ),
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major={}, minor={}, patch={}".format(
                v_parts[0], v_parts[1], v_parts[2]
            ),
        ),
        ("bumpversion.cli", "INFO", "Attempting to increment part 'patch'"),
        (
            "bumpversion.cli",
            "INFO",
            "Values are now: major={}, minor={}, patch={}".format(
                p_parts[0], p_parts[1], p_parts[2]
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Dry run active, won't touch any files.",
        ),  # only in dry-run mode
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '{}' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'".format(
                patch
            ),
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major={}, minor={}, patch={}".format(
                p_parts[0], p_parts[1], p_parts[2]
            ),
        ),
        ("bumpversion.cli", "INFO", "New version will be '{}'".format(patch)),
        (
            "bumpversion.cli",
            "INFO",
            "Asserting files {} contain the version string...".format(file),
        ),
        (
            "bumpversion.utils",
            "INFO",
            "Found '{v}' in {f} at line 0: {v}".format(v=version, f=file),
        ),  # verbose
        (
            "bumpversion.utils",
            "INFO",
            "Would change file {}:".format(file),
        ),  # dry-run change to 'would'
        (
            "bumpversion.utils",
            "INFO",
            "--- a/{f}\n+++ b/{f}\n@@ -1 +1 @@\n-{v}\n+{p}".format(
                f=file, v=version, p=patch
            ),
        ),
        ("bumpversion.list", "INFO", "current_version={}".format(version)),
        ("bumpversion.list", "INFO", "tag=True"),
        ("bumpversion.list", "INFO", "commit=True"),
        ("bumpversion.list", "INFO", "message={}".format(message)),
        ("bumpversion.list", "INFO", "new_version={}".format(patch)),
        (
            "bumpversion.cli",
            "INFO",
            "Would write to config file {}:".format(bumpcfg),
        ),  # dry-run 'would'
        ("bumpversion.cli", "INFO", config.replace(version, patch)),
        # following entries are only present if both --verbose and --dry-run are specified
        # all entries use 'would do x' variants instead of 'doing x'
        ("bumpversion.cli", "INFO", "Would prepare {vcs} commit".format(vcs=vcs_name)),
        (
            "bumpversion.cli",
            "INFO",
            "Would add changes in file '{file}' to {vcs}".format(
                file=file, vcs=vcs_name
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Would add changes in file '{file}' to {vcs}".format(
                file=bumpcfg, vcs=vcs_name
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Would commit to {vcs} with message '{msg}'".format(
                msg=message, vcs=vcs_name
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Would tag 'v{p}' with message 'Bump version: {v} → {p}' in {vcs} and not signing".format(
                v=version, p=patch, vcs=vcs_name
            ),
        ),
        order_matters=True,
    )


def test_bump_version(tmp_dir):
    tmp_dir.joinpath("file5").write_text("1.0.0")
    main(["patch", "--current-version", "1.0.0", "file5"])

    assert tmp_dir.joinpath("file5").read_text() == "1.0.1"


def test_bump_version_custom_main(tmp_dir):
    tmp_dir.joinpath("file6").write_text("XXX1;0;0")
    main(
        [
            "--current-version",
            "XXX1;0;0",
            "--parse",
            r"XXX(?P<spam>\d+);(?P<blob>\d+);(?P<slurp>\d+)",
            "--serialize",
            "XXX{spam};{blob};{slurp}",
            "blob",
            "file6",
        ]
    )

    assert tmp_dir.joinpath("file6").read_text() == "XXX1;1;0"


def test_bump_version_custom_parse_serialize_configfile(tmp_dir):
    tmp_dir.joinpath("file12").write_text("ZZZ8;0;0")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(r"""[bumpversion]
current_version = ZZZ8;0;0
serialize = ZZZ{spam};{blob};{slurp}
parse = ZZZ(?P<spam>\d+);(?P<blob>\d+);(?P<slurp>\d+)
[bumpversion:file:file12]
""")

    main(["blob"])

    assert tmp_dir.joinpath("file12").read_text() == "ZZZ8;1;0"


def test_bumpversion_custom_parse_semver(tmp_dir):
    tmp_dir.joinpath("file15").write_text("XXX1.1.7-master+allan1")
    main(
        [
            "--current-version",
            "1.1.7-master+allan1",
            "--parse",
            r"(?P<major>\d+).(?P<minor>\d+).(?P<patch>\d+)(-(?P<pre_release>[^\+]+))?(\+(?P<meta>.*))?",
            "--serialize",
            "{major}.{minor}.{patch}-{pre_release}+{meta}",
            "meta",
            "file15",
        ]
    )

    assert tmp_dir.joinpath("file15").read_text() == "XXX1.1.7-master+allan2"


def test_bump_version_missing_part(tmp_dir):
    tmp_dir.joinpath("file5").write_text("1.0.0")
    with pytest.raises(
        exceptions.InvalidVersionPartException, match="No part named 'bugfix'"
    ):
        main(["bugfix", "--current-version", "1.0.0", "file5"])


def test_dirty_work_dir(tmp_dir, vcs):
    check_call([vcs, "init"])
    tmp_dir.joinpath("dirty").write_text("i'm dirty")

    check_call([vcs, "add", "dirty"])
    vcs_name = "Mercurial" if vcs == "hg" else "Git"
    vcs_output = "A dirty" if vcs == "hg" else "A  dirty"

    with pytest.raises(exceptions.WorkingDirectoryIsDirtyException):  # NOQA:SIM117
        with LogCapture() as log_capture:
            main(["patch", "--current-version", "1", "--new-version", "2", "file7"])

    log_capture.check_present(
        (
            "bumpversion.cli",
            "WARNING",
            "{} working directory is not clean:\n"
            "{}\n"
            "\n"
            "Use --allow-dirty to override this if you know what you're doing.".format(
                vcs_name, vcs_output
            ),
        )
    )


def test_force_dirty_work_dir(tmp_dir, vcs):
    check_call([vcs, "init"])
    tmp_dir.joinpath("dirty2").write_text("i'm dirty! 1.1.1")

    check_call([vcs, "add", "dirty2"])

    main(["patch", "--allow-dirty", "--current-version", "1.1.1", "dirty2"])

    assert tmp_dir.joinpath("dirty2").read_text() == "i'm dirty! 1.1.2"


def test_bump_major(tmp_dir):
    tmp_dir.joinpath("fileMAJORBUMP").write_text("4.2.8")
    main(["--current-version", "4.2.8", "major", "fileMAJORBUMP"])

    assert tmp_dir.joinpath("fileMAJORBUMP").read_text() == "5.0.0"


def test_commit_and_tag(tmp_dir, vcs):
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("47.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["patch", "--current-version", "47.1.1", "--commit", "VERSION"])

    assert tmp_dir.joinpath("VERSION").read_text() == "47.1.2"

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert "-47.1.1" in log
    assert "+47.1.2" in log
    assert "Bump version: 47.1.1 → 47.1.2" in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b"v47.1.2" not in tag_out

    main(["patch", "--current-version", "47.1.2", "--commit", "--tag", "VERSION"])

    assert tmp_dir.joinpath("VERSION").read_text() == "47.1.3"

    check_output([vcs, "log", "-p"])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b"v47.1.3" in tag_out


def test_commit_with_emoji(tmp_dir, vcs):
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("47.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(
        [
            "patch",
            "--message-emoji=1",
            "--current-version",
            "47.1.1",
            "--commit",
            "VERSION",
        ]
    )

    assert tmp_dir.joinpath("VERSION").read_text() == "47.1.2"

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert "-47.1.1" in log
    assert "+47.1.2" in log
    assert "⬆️  Bump version: 47.1.1 → 47.1.2" in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b"v47.1.2" not in tag_out

    main(
        [
            "patch",
            "--message-emoji=10",
            "--current-version",
            "47.1.1",
            "--commit",
            "VERSION",
        ]
    )

    assert tmp_dir.joinpath("VERSION").read_text() == "47.1.2"

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert "-47.1.1" in log
    assert "+47.1.2" in log
    assert "⬆️ Bump version: 47.1.1 → 47.1.2" in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b"v47.1.2" not in tag_out

    main(
        [
            "patch",
            "--message-emoji=⬆",
            "--current-version",
            "47.1.2",
            "--commit",
            "VERSION",
        ]
    )

    assert tmp_dir.joinpath("VERSION").read_text() == "47.1.3"

    log = check_output([vcs, "log", "-p"]).decode("utf-8")
    assert "⬆ Bump version: 47.1.2 → 47.1.3" in log

    # tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    # assert b"v47.1.3" in tag_out


def test_commit_and_tag_with_configfile(tmp_dir, vcs):
    cfg_file = tmp_dir.joinpath(".bumpversion.cfg")
    cfg_file.write_text("""[bumpversion]\ncommit = True\ntag = True""")

    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("48.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "add", cfg_file.name])
    check_call([vcs, "commit", "-m", "initial commit"])
    main(["patch", "--current-version", "48.1.1", "--no-tag", "VERSION"])

    assert tmp_dir.joinpath("VERSION").read_text() == "48.1.2"
    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert "-48.1.1" in log
    assert "+48.1.2" in log
    assert "Bump version: 48.1.1 → 48.1.2" in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b"v48.1.2" not in tag_out

    main(["patch", "--current-version", "48.1.2", "VERSION"])

    assert tmp_dir.joinpath("VERSION").read_text() == "48.1.3"

    check_output([vcs, "log", "-p"])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b"v48.1.3" in tag_out


@pytest.mark.parametrize("config", [COMMIT, COMMIT_NOT_TAG])
def test_commit_and_not_tag_with_configfile(tmp_dir, vcs, config):
    tmp_dir.joinpath(".bumpversion.cfg").write_text(config)

    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("48.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "add", ".bumpversion.cfg"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["patch", "--current-version", "48.1.1", "VERSION"])

    assert tmp_dir.joinpath("VERSION").read_text() == "48.1.2"

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert "-48.1.1" in log
    assert "+48.1.2" in log
    assert "Bump version: 48.1.1 → 48.1.2" in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b"v48.1.2" not in tag_out


def test_commit_explicitly_false(tmp_dir, vcs):
    tmp_dir.joinpath(".bumpversion.cfg").write_text("""[bumpversion]
current_version: 10.0.0
commit = False
tag = False""")

    check_call([vcs, "init"])
    tmp_dir.joinpath("tracked_file").write_text("10.0.0")
    check_call([vcs, "add", "tracked_file"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["patch", "tracked_file"])

    assert tmp_dir.joinpath("tracked_file").read_text() == "10.0.1"

    log = check_output([vcs, "log", "-p"]).decode("utf-8")
    assert "10.0.1" not in log

    diff = check_output([vcs, "diff"]).decode("utf-8")
    assert "10.0.1" in diff


def test_commit_configfile_true_cli_false_override(tmp_dir, vcs):
    tmp_dir.joinpath(".bumpversion.cfg").write_text("""[bumpversion]
current_version: 27.0.0
commit = True""")

    check_call([vcs, "init"])
    tmp_dir.joinpath("dont_commit_file").write_text("27.0.0")
    check_call([vcs, "add", "dont_commit_file"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["patch", "--no-commit", "dont_commit_file"])

    assert tmp_dir.joinpath("dont_commit_file").read_text() == "27.0.1"

    log = check_output([vcs, "log", "-p"]).decode("utf-8")
    assert "27.0.1" not in log

    diff = check_output([vcs, "diff"]).decode("utf-8")
    assert "27.0.1" in diff


def test_bump_version_environment(tmp_dir):
    tmp_dir.joinpath("on_jenkins").write_text("2.3.4")
    os.environ["BUILD_NUMBER"] = "567"
    main(
        [
            "--verbose",
            "--current-version",
            "2.3.4",
            "--parse",
            r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*",
            "--serialize",
            "{major}.{minor}.{patch}.pre{$BUILD_NUMBER}",
            "patch",
            "on_jenkins",
        ]
    )
    del os.environ["BUILD_NUMBER"]

    assert tmp_dir.joinpath("on_jenkins").read_text() == "2.3.5.pre567"


def test_current_version_from_tag(tmp_dir, git):
    # prepare
    tmp_dir.joinpath("update_from_tag").write_text("26.6.0")
    check_call([git, "init"])
    check_call([git, "add", "update_from_tag"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v26.6.0"])

    # don't give current-version, that should come from tag
    main(["patch", "update_from_tag"])

    assert tmp_dir.joinpath("update_from_tag").read_text() == "26.6.1"


def test_current_version_from_tag_written_to_config_file(tmp_dir, git):
    # prepare
    tmp_dir.joinpath("updated_also_in_config_file").write_text("14.6.0")

    tmp_dir.joinpath(".bumpversion.cfg").write_text("""[bumpversion]""")

    check_call([git, "init"])
    check_call([git, "add", "updated_also_in_config_file"])
    check_call([git, "add", ".bumpversion.cfg"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v14.6.0"])

    # don't give current-version, that should come from tag
    main(
        [
            "patch",
            "updated_also_in_config_file",
            "--commit",
            "--tag",
        ]
    )

    assert tmp_dir.joinpath("updated_also_in_config_file").read_text() == "14.6.1"
    assert "14.6.1" in tmp_dir.joinpath(".bumpversion.cfg").read_text()


def test_distance_to_latest_tag_as_part_of_new_version(tmp_dir, git):
    # prepare
    tmp_dir.joinpath("my_source_file").write_text("19.6.0")

    check_call([git, "init"])
    check_call([git, "add", "my_source_file"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v19.6.0"])
    check_call([git, "commit", "--allow-empty", "-m", "Just a commit 1"])
    check_call([git, "commit", "--allow-empty", "-m", "Just a commit 2"])
    check_call([git, "commit", "--allow-empty", "-m", "Just a commit 3"])

    # don't give current-version, that should come from tag
    main(
        [
            "patch",
            "--parse",
            r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*",
            "--serialize",
            "{major}.{minor}.{patch}-pre{distance_to_latest_tag}",
            "my_source_file",
        ]
    )

    assert tmp_dir.joinpath("my_source_file").read_text() == "19.6.1-pre3"


def test_override_vcs_current_version(tmp_dir, git):
    # prepare
    tmp_dir.joinpath("contains_actual_version").write_text("6.7.8")
    check_call([git, "init"])
    check_call([git, "add", "contains_actual_version"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v6.7.8"])

    # update file
    tmp_dir.joinpath("contains_actual_version").write_text("7.0.0")
    check_call([git, "add", "contains_actual_version"])

    # but forgot to tag or forgot to push --tags
    check_call([git, "commit", "-m", "major release"])

    # if we don't give current-version here we get
    # "AssertionError: Did not find string 6.7.8 in file contains_actual_version"
    main(["patch", "--current-version", "7.0.0", "contains_actual_version"])

    assert tmp_dir.joinpath("contains_actual_version").read_text() == "7.0.1"


def test_non_existing_file(tmp_dir):
    with pytest.raises(IOError):
        main(
            shlex_split(
                "patch --current-version 1.2.0 --new-version 1.2.1 does_not_exist.txt"
            )
        )


def test_non_existing_second_file(tmp_dir):
    tmp_dir.joinpath("my_source_code.txt").write_text("1.2.3")
    with pytest.raises(IOError):
        main(
            shlex_split(
                "patch --current-version 1.2.3 my_source_code.txt does_not_exist2.txt"
            )
        )

    # first file is unchanged because second didn't exist
    assert tmp_dir.joinpath("my_source_code.txt").read_text() == "1.2.3"


def test_read_version_tags_only(tmp_dir, git):
    # prepare
    tmp_dir.joinpath("update_from_tag").write_text("29.6.0")
    check_call([git, "init"])
    check_call([git, "add", "update_from_tag"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v29.6.0"])
    check_call([git, "commit", "--allow-empty", "-m", "a commit"])
    check_call([git, "tag", "jenkins-deploy-my-project-2"])

    # don't give current-version, that should come from tag
    main(["patch", "update_from_tag"])

    assert tmp_dir.joinpath("update_from_tag").read_text() == "29.6.1"


def test_tag_name(tmp_dir, vcs):
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("31.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(
        [
            "patch",
            "--current-version",
            "31.1.1",
            "--commit",
            "--tag",
            "VERSION",
            "--tag-name",
            "ReleasedVersion-{new_version}",
        ]
    )

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b"ReleasedVersion-31.1.2" in tag_out


def test_message_from_config_file(tmp_dir, vcs):
    tmp_dir.joinpath(".bumpversion.cfg").write_text("""[bumpversion]
current_version: 400.0.0
new_version: 401.0.0
commit: True
tag: True
message: {current_version} was old, {new_version} is new
tag_name: from-{current_version}-to-{new_version}""")
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("400.0.0")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "add", ".bumpversion.cfg"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["major", "VERSION"])

    log = check_output([vcs, "log", "-p"])

    assert b"400.0.0 was old, 401.0.0 is new" in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b"from-400.0.0-to-401.0.0" in tag_out


def test_all_parts_in_message_and_serialize_and_tag_name_from_config_file(tmp_dir, vcs):
    """
    Ensure that major/minor/patch *and* custom parts can be used everywhere.

    - As [part] in 'serialize'.
    - As new_[part] and previous_[part] in 'message'.
    - As new_[part] and previous_[part] in 'tag_name'.

    In message and tag_name, also ensure that new_version and
    current_version are correct.
    """
    tmp_dir.joinpath(".bumpversion.cfg").write_text(r"""[bumpversion]
current_version: 400.1.2.101
new_version: 401.2.3.102
parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).(?P<custom>\d+)
serialize = {major}.{minor}.{patch}.{custom}
commit: True
tag: True
message: {current_version}/{current_major}.{current_minor}.{current_patch} custom {current_custom} becomes {new_version}/{new_major}.{new_minor}.{new_patch} custom {new_custom}
tag_name: from-{current_version}-aka-{current_major}.{current_minor}.{current_patch}-custom-{current_custom}-to-{new_version}-aka-{new_major}.{new_minor}.{new_patch}-custom-{new_custom}

[bumpversion:part:custom]
""")
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("400.1.2.101")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "add", ".bumpversion.cfg"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["major", "VERSION"])

    log = check_output([vcs, "log", "-p"])
    assert (
        b"400.1.2.101/400.1.2 custom 101 becomes 401.2.3.102/401.2.3 custom 102" in log
    )

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])
    assert (
        b"from-400.1.2.101-aka-400.1.2-custom-101-to-401.2.3.102-aka-401.2.3-custom-102"
        in tag_out
    )


def test_all_parts_in_replace_from_config_file(tmp_dir, vcs):
    """
    Ensure that major/minor/patch *and* custom parts can be used in 'replace'.
    """

    tmp_dir.joinpath(".bumpversion.cfg").write_text(r"""[bumpversion]
current_version: 400.1.2.101
new_version: 401.2.3.102
parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).(?P<custom>\d+)
serialize = {major}.{minor}.{patch}.{custom}
commit: True
tag: False

[bumpversion:part:custom]

[bumpversion:VERSION]
search = my version is {current_version}
replace = my version is {new_major}.{new_minor}.{new_patch}.{new_custom}""")
    tmp_dir.joinpath("VERSION").write_text("my version is 400.1.2.101\n")
    check_call([vcs, "init"])
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "add", ".bumpversion.cfg"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["major", "VERSION"])
    log = check_output([vcs, "log", "-p"])
    assert b"+my version is 401.2.3.102" in log


def test_unannotated_tag(tmp_dir, vcs):
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("42.3.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(
        [
            "patch",
            "--current-version",
            "42.3.1",
            "--commit",
            "--tag",
            "VERSION",
            "--tag-name",
            "ReleasedVersion-{new_version}",
            "--tag-message",
            "",
        ]
    )

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])
    assert b"ReleasedVersion-42.3.2" in tag_out

    if vcs == "git":
        describe_out = subprocess.call([vcs, "describe"])
        assert describe_out == 128

        describe_out = subprocess.check_output([vcs, "describe", "--tags"])
        assert describe_out.startswith(b"ReleasedVersion-42.3.2")


def test_annotated_tag(tmp_dir, vcs):
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("42.4.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(
        [
            "patch",
            "--current-version",
            "42.4.1",
            "--commit",
            "--tag",
            "VERSION",
            "--tag-message",
            "test {new_version}-tag",
        ]
    )
    assert tmp_dir.joinpath("VERSION").read_text() == "42.4.2"

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])
    assert b"v42.4.2" in tag_out

    if vcs == "git":
        describe_out = subprocess.check_output([vcs, "describe"])
        assert describe_out == b"v42.4.2\n"

        describe_out = subprocess.check_output([vcs, "show", "v42.4.2"])
        assert describe_out.startswith(b"tag v42.4.2\n")
        assert b"test 42.4.2-tag" in describe_out
    elif vcs == "hg":
        describe_out = subprocess.check_output([vcs, "log"])
        assert b"test 42.4.2-tag" in describe_out
    else:
        raise ValueError("Unknown VCS")


def test_vcs_describe(tmp_dir, git):
    check_call([git, "init"])
    tmp_dir.joinpath("VERSION").write_text("42.5.1")
    check_call([git, "add", "VERSION"])
    check_call([git, "commit", "-m", "initial commit"])

    main(
        [
            "patch",
            "--current-version",
            "42.5.1",
            "--commit",
            "--tag",
            "VERSION",
            "--tag-message",
            "test {new_version}-tag",
        ]
    )
    assert tmp_dir.joinpath("VERSION").read_text() == "42.5.2"

    describe_out = subprocess.check_output([git, "describe"])
    assert describe_out == b"v42.5.2\n"

    main(
        [
            "patch",
            "--current-version",
            "42.5.2",
            "--commit",
            "--tag",
            "VERSION",
            "--tag-name",
            "ReleasedVersion-{new_version}",
            "--tag-message",
            "",
        ]
    )
    assert tmp_dir.joinpath("VERSION").read_text() == "42.5.3"

    describe_only_annotated_out = subprocess.check_output([git, "describe"])
    assert describe_only_annotated_out.startswith(b"v42.5.2-1-g")

    describe_all_out = subprocess.check_output([git, "describe", "--tags"])
    assert describe_all_out == b"ReleasedVersion-42.5.3\n"


config_parser_handles_utf8 = True
try:
    import configparser  # noqa:F401
except ImportError:
    config_parser_handles_utf8 = False


@pytest.mark.xfail(
    not config_parser_handles_utf8,
    reason="old ConfigParser uses non-utf-8-strings internally",
)
def test_utf8_message_from_config_file(tmp_dir, vcs):
    initial_config = """[bumpversion]
current_version = 500.0.0
commit = True
message = Nová verze: {current_version} ☃, {new_version} ☀
"""

    tmp_dir.joinpath(".bumpversion.cfg").write_bytes(initial_config.encode("utf-8"))
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("500.0.0")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "add", ".bumpversion.cfg"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["major", "VERSION"])
    check_output([vcs, "log", "-p"])
    expected_new_config = initial_config.replace("500", "501")
    assert (
        expected_new_config.encode()
        == tmp_dir.joinpath(".bumpversion.cfg").read_bytes()
    )


def test_utf8_message_from_config_file_2(tmp_dir, vcs):
    initial_config = """[bumpversion]
current_version = 10.10.0
commit = True
message = [{now}] [{utcnow} {utcnow:%YXX%mYY%d}]

"""
    tmp_dir.joinpath(".bumpversion.cfg").write_text(initial_config)
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("10.10.0")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "add", ".bumpversion.cfg"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(["major", "VERSION"])

    log = check_output([vcs, "log", "-p"])

    assert b"[20" in log
    assert b"] [" in log
    assert b"XX" in log
    assert b"YY" in log


def test_commit_and_tag_from_below_vcs_root(tmp_dir, vcs, monkeypatch):
    check_call([vcs, "init"])
    tmp_dir.joinpath("VERSION").write_text("30.0.3")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    subdir = tmp_dir.joinpath("subdir")
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    main(["major", "--current-version", "30.0.3", "--commit", "../VERSION"])

    assert tmp_dir.joinpath("VERSION").read_text() == "31.0.0"


def test_non_vcs_operations_if_vcs_is_not_installed(tmp_dir, vcs, monkeypatch):
    monkeypatch.setenv("PATH", "")

    tmp_dir.joinpath("VERSION").write_text("31.0.3")

    main(["major", "--current-version", "31.0.3", "VERSION"])

    assert tmp_dir.joinpath("VERSION").read_text() == "32.0.0"


def test_serialize_newline(tmp_dir):
    tmp_dir.joinpath("file_new_line").write_text("MAJOR=31\nMINOR=0\nPATCH=3\n")
    main(
        [
            "--current-version",
            "MAJOR=31\nMINOR=0\nPATCH=3\n",
            "--parse",
            "MAJOR=(?P<major>\\d+)\\nMINOR=(?P<minor>\\d+)\\nPATCH=(?P<patch>\\d+)\\n",
            "--serialize",
            "MAJOR={major}\nMINOR={minor}\nPATCH={patch}\n",
            "--verbose",
            "major",
            "file_new_line",
        ]
    )
    assert (
        tmp_dir.joinpath("file_new_line").read_text() == "MAJOR=32\nMINOR=0\nPATCH=0\n"
    )


def test_multiple_serialize_three_part(tmp_dir):
    tmp_dir.joinpath("fileA").write_text("Version: 0.9")
    main(
        [
            "--current-version",
            "Version: 0.9",
            "--parse",
            r"Version:\ (?P<major>\d+)(\.(?P<minor>\d+)(\.(?P<patch>\d+))?)?",
            "--serialize",
            "Version: {major}.{minor}.{patch}",
            "--serialize",
            "Version: {major}.{minor}",
            "--serialize",
            "Version: {major}",
            "--verbose",
            "major",
            "fileA",
        ]
    )

    assert tmp_dir.joinpath("fileA").read_text() == "Version: 1"


def test_multiple_serialize_two_part(tmp_dir):
    tmp_dir.joinpath("fileB").write_text("0.9")
    main(
        [
            "--current-version",
            "0.9",
            "--parse",
            r"(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?",
            "--serialize",
            "{major}.{minor}.{patch}",
            "--serialize",
            "{major}.{minor}",
            "minor",
            "fileB",
        ]
    )

    assert tmp_dir.joinpath("fileB").read_text() == "0.10"


def test_multiple_serialize_two_part_patch(tmp_dir):
    tmp_dir.joinpath("fileC").write_text("0.7")
    main(
        [
            "--current-version",
            "0.7",
            "--parse",
            r"(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?",
            "--serialize",
            "{major}.{minor}.{patch}",
            "--serialize",
            "{major}.{minor}",
            "patch",
            "fileC",
        ]
    )

    assert tmp_dir.joinpath("fileC").read_text() == "0.7.1"


def test_multiple_serialize_two_part_patch_configfile(tmp_dir):
    tmp_dir.joinpath("fileD").write_text("0.6")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(r"""[bumpversion]
current_version = 0.6
serialize =
  {major}.{minor}.{patch}
  {major}.{minor}
parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
[bumpversion:file:fileD]
""")

    main(["patch"])

    assert tmp_dir.joinpath("fileD").read_text() == "0.6.1"


def test_search_uses_shortest_possible_custom_search_pattern(tmp_dir):
    config = dedent(r"""
        [bumpversion]
        current_version = 0.0.0
        commit = True
        tag = True
        parse = (?P<major>\d+).(?P<minor>\d+).(?P<patch>\d+).?((?P<prerelease>.*))?
        serialize =
            {major}.{minor}.{patch}.{prerelease}
            {major}.{minor}.{patch}

        [bumpversion:file:package.json]
        search = "version": "{current_version}",
        replace = "version": "{new_version}",
    """)
    tmp_dir.joinpath(".bumpversion.cfg").write_bytes(config.encode("utf-8"))

    tmp_dir.joinpath("package.json").write_text("""{
        "version": "0.0.0",
        "package": "20.0.0",
    }""")

    main(["patch"])

    assert (
        tmp_dir.joinpath("package.json").read_text()
        == """{
        "version": "0.0.1",
        "package": "20.0.0",
    }"""
    )


def test_log_no_config_file_info_message(tmp_dir):
    tmp_dir.joinpath("a_file.txt").write_text("1.0.0")

    with LogCapture(level=logging.INFO) as log_capture:
        main(
            [
                "--verbose",
                "--verbose",
                "--current-version",
                "1.0.0",
                "patch",
                "a_file.txt",
            ]
        )

    log_capture.check_present(
        ("bumpversion.cli", "INFO", "Could not read config file at .bumpversion.cfg"),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '1.0.0' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=1, minor=0, patch=0",
        ),
        ("bumpversion.cli", "INFO", "Attempting to increment part 'patch'"),
        ("bumpversion.cli", "INFO", "Values are now: major=1, minor=0, patch=1"),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '1.0.1' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=1, minor=0, patch=1",
        ),
        ("bumpversion.cli", "INFO", "New version will be '1.0.1'"),
        (
            "bumpversion.cli",
            "INFO",
            "Asserting files a_file.txt contain the version string...",
        ),
        ("bumpversion.utils", "INFO", "Found '1.0.0' in a_file.txt at line 0: 1.0.0"),
        ("bumpversion.utils", "INFO", "Changing file a_file.txt:"),
        (
            "bumpversion.utils",
            "INFO",
            "--- a/a_file.txt\n+++ b/a_file.txt\n@@ -1 +1 @@\n-1.0.0\n+1.0.1",
        ),
        ("bumpversion.cli", "INFO", "Would write to config file .bumpversion.cfg:"),
        ("bumpversion.cli", "INFO", "[bumpversion]\ncurrent_version = 1.0.1\n\n"),
        order_matters=True,
    )


def test_log_parse_doesnt_parse_current_version(tmp_dir):
    with LogCapture() as log_capture:
        main(
            [
                "--verbose",
                "--parse",
                "xxx",
                "--current-version",
                "12",
                "--new-version",
                "13",
                "patch",
            ]
        )

    log_capture.check_present(
        ("bumpversion.cli", "INFO", "Could not read config file at .bumpversion.cfg"),
        ("bumpversion.version_part", "INFO", "Parsing version '12' using regexp 'xxx'"),
        (
            "bumpversion.version_part",
            "WARNING",
            "Evaluating 'parse' option: 'xxx' does not parse current version '12'",
        ),
        ("bumpversion.version_part", "INFO", "Parsing version '13' using regexp 'xxx'"),
        (
            "bumpversion.version_part",
            "WARNING",
            "Evaluating 'parse' option: 'xxx' does not parse current version '13'",
        ),
        ("bumpversion.cli", "INFO", "New version will be '13'"),
        ("bumpversion.cli", "INFO", "Asserting files  contain the version string..."),
        ("bumpversion.cli", "INFO", "Would write to config file .bumpversion.cfg:"),
        ("bumpversion.cli", "INFO", "[bumpversion]\ncurrent_version = 13\n\n"),
    )


def test_log_invalid_regex_exit(tmp_dir):
    with pytest.raises(SystemExit):  # NOQA:SIM117
        with LogCapture() as log_capture:
            main(
                [
                    "--parse",
                    "*kittens*",
                    "--current-version",
                    "12",
                    "--new-version",
                    "13",
                    "patch",
                ]
            )

    log_capture.check_present(
        (
            "bumpversion.version_part",
            "ERROR",
            "--parse '*kittens*' is not a valid regex",
        ),
    )


def test_complex_info_logging(tmp_dir):
    tmp_dir.joinpath("fileE").write_text("0.4")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
        [bumpversion]
        current_version = 0.4
        serialize =
          {major}.{minor}.{patch}
          {major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
        [bumpversion:file:fileE]
        """).strip()
    )

    with LogCapture() as log_capture:
        main(["patch", "--verbose"])

    log_capture.check(
        ("bumpversion.cli", "INFO", "Reading config file .bumpversion.cfg:"),
        (
            "bumpversion.cli",
            "INFO",
            "[bumpversion]\ncurrent_version = 0.4\nserialize =\n  {major}.{minor}.{patch}\n  {major}.{minor}\nparse = (?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?\n[bumpversion:file:fileE]",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '0.4' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=0, minor=4, patch=0",
        ),
        ("bumpversion.cli", "INFO", "Attempting to increment part 'patch'"),
        ("bumpversion.cli", "INFO", "Values are now: major=0, minor=4, patch=1"),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '0.4.1' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=0, minor=4, patch=1",
        ),
        ("bumpversion.cli", "INFO", "New version will be '0.4.1'"),
        (
            "bumpversion.cli",
            "INFO",
            "Asserting files fileE contain the version string...",
        ),
        ("bumpversion.utils", "INFO", "Found '0.4' in fileE at line 0: 0.4"),
        ("bumpversion.utils", "INFO", "Changing file fileE:"),
        (
            "bumpversion.utils",
            "INFO",
            "--- a/fileE\n+++ b/fileE\n@@ -1 +1 @@\n-0.4\n+0.4.1",
        ),
        ("bumpversion.list", "INFO", "current_version=0.4"),
        (
            "bumpversion.list",
            "INFO",
            "serialize=\n{major}.{minor}.{patch}\n{major}.{minor}",
        ),
        (
            "bumpversion.list",
            "INFO",
            "parse=(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?",
        ),
        ("bumpversion.list", "INFO", "new_version=0.4.1"),
        ("bumpversion.cli", "INFO", "Writing to config file .bumpversion.cfg:"),
        (
            "bumpversion.cli",
            "INFO",
            "[bumpversion]\ncurrent_version = 0.4.1\nserialize = \n\t{major}.{minor}.{patch}\n\t{major}.{minor}\nparse = (?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?\n\n[bumpversion:file:fileE]\n\n",
        ),
    )


def test_subjunctive_dry_run_logging(tmp_dir, vcs):
    tmp_dir.joinpath("dont_touch_me.txt").write_text("0.8")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
        [bumpversion]
        current_version = 0.8
        commit = True
        tag = True
        serialize =
        	{major}.{minor}.{patch}
        	{major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
        [bumpversion:file:dont_touch_me.txt]
    """).strip()
    )

    check_call([vcs, "init"])
    check_call([vcs, "add", "dont_touch_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    vcs_name = "Mercurial" if vcs == "hg" else "Git"

    with LogCapture() as log_capture:
        main(["patch", "--verbose", "--dry-run"])

    log_capture.check(
        ("bumpversion.cli", "INFO", "Reading config file .bumpversion.cfg:"),
        (
            "bumpversion.cli",
            "INFO",
            "[bumpversion]\ncurrent_version = 0.8\ncommit = True\ntag = True\nserialize =\n\t{major}.{minor}.{patch}\n\t{major}.{minor}\nparse = (?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?\n[bumpversion:file:dont_touch_me.txt]",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '0.8' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=0, minor=8, patch=0",
        ),
        ("bumpversion.cli", "INFO", "Attempting to increment part 'patch'"),
        ("bumpversion.cli", "INFO", "Values are now: major=0, minor=8, patch=1"),
        ("bumpversion.cli", "INFO", "Dry run active, won't touch any files."),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '0.8.1' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=0, minor=8, patch=1",
        ),
        ("bumpversion.cli", "INFO", "New version will be '0.8.1'"),
        (
            "bumpversion.cli",
            "INFO",
            "Asserting files dont_touch_me.txt contain the version string...",
        ),
        (
            "bumpversion.utils",
            "INFO",
            "Found '0.8' in dont_touch_me.txt at line 0: 0.8",
        ),
        ("bumpversion.utils", "INFO", "Would change file dont_touch_me.txt:"),
        (
            "bumpversion.utils",
            "INFO",
            "--- a/dont_touch_me.txt\n+++ b/dont_touch_me.txt\n@@ -1 +1 @@\n-0.8\n+0.8.1",
        ),
        ("bumpversion.list", "INFO", "current_version=0.8"),
        ("bumpversion.list", "INFO", "commit=True"),
        ("bumpversion.list", "INFO", "tag=True"),
        (
            "bumpversion.list",
            "INFO",
            "serialize=\n{major}.{minor}.{patch}\n{major}.{minor}",
        ),
        (
            "bumpversion.list",
            "INFO",
            "parse=(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?",
        ),
        ("bumpversion.list", "INFO", "new_version=0.8.1"),
        ("bumpversion.cli", "INFO", "Would write to config file .bumpversion.cfg:"),
        (
            "bumpversion.cli",
            "INFO",
            "[bumpversion]\ncurrent_version = 0.8.1\ncommit = True\ntag = True\nserialize = \n\t{major}.{minor}.{patch}\n\t{major}.{minor}\nparse = (?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?\n\n[bumpversion:file:dont_touch_me.txt]\n\n",
        ),
        ("bumpversion.cli", "INFO", "Would prepare {vcs} commit".format(vcs=vcs_name)),
        (
            "bumpversion.cli",
            "INFO",
            "Would add changes in file 'dont_touch_me.txt' to {vcs}".format(
                vcs=vcs_name
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Would add changes in file '.bumpversion.cfg' to {vcs}".format(
                vcs=vcs_name
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Would commit to {vcs} with message 'Bump version: 0.8 \u2192 0.8.1'".format(
                vcs=vcs_name
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Would tag 'v0.8.1' with message 'Bump version: 0.8 \u2192 0.8.1' in {vcs} and not signing".format(
                vcs=vcs_name
            ),
        ),
    )


def test_log_commit_message_if_no_commit_tag_but_usable_vcs(tmp_dir, vcs):
    tmp_dir.joinpath("please_touch_me.txt").write_text("0.3.3")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
        [bumpversion]
        current_version = 0.3.3
        commit = False
        tag = False
        [bumpversion:file:please_touch_me.txt]
        """).strip()
    )

    check_call([vcs, "init"])
    check_call([vcs, "add", "please_touch_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    vcs_name = "Mercurial" if vcs == "hg" else "Git"

    with LogCapture() as log_capture:
        main(["patch", "--verbose"])

    log_capture.check(
        ("bumpversion.cli", "INFO", "Reading config file .bumpversion.cfg:"),
        (
            "bumpversion.cli",
            "INFO",
            "[bumpversion]\ncurrent_version = 0.3.3\ncommit = False\ntag = False\n[bumpversion:file:please_touch_me.txt]",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '0.3.3' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=0, minor=3, patch=3",
        ),
        ("bumpversion.cli", "INFO", "Attempting to increment part 'patch'"),
        ("bumpversion.cli", "INFO", "Values are now: major=0, minor=3, patch=4"),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '0.3.4' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=0, minor=3, patch=4",
        ),
        ("bumpversion.cli", "INFO", "New version will be '0.3.4'"),
        (
            "bumpversion.cli",
            "INFO",
            "Asserting files please_touch_me.txt contain the version string...",
        ),
        (
            "bumpversion.utils",
            "INFO",
            "Found '0.3.3' in please_touch_me.txt at line 0: 0.3.3",
        ),
        ("bumpversion.utils", "INFO", "Changing file please_touch_me.txt:"),
        (
            "bumpversion.utils",
            "INFO",
            "--- a/please_touch_me.txt\n+++ b/please_touch_me.txt\n@@ -1 +1 @@\n-0.3.3\n+0.3.4",
        ),
        ("bumpversion.list", "INFO", "current_version=0.3.3"),
        ("bumpversion.list", "INFO", "commit=False"),
        ("bumpversion.list", "INFO", "tag=False"),
        ("bumpversion.list", "INFO", "new_version=0.3.4"),
        ("bumpversion.cli", "INFO", "Writing to config file .bumpversion.cfg:"),
        (
            "bumpversion.cli",
            "INFO",
            "[bumpversion]\ncurrent_version = 0.3.4\ncommit = False\ntag = False\n\n[bumpversion:file:please_touch_me.txt]\n\n",
        ),
        ("bumpversion.cli", "INFO", "Would prepare {vcs} commit".format(vcs=vcs_name)),
        (
            "bumpversion.cli",
            "INFO",
            "Would add changes in file 'please_touch_me.txt' to {vcs}".format(
                vcs=vcs_name
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Would add changes in file '.bumpversion.cfg' to {vcs}".format(
                vcs=vcs_name
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Would commit to {vcs} with message 'Bump version: 0.3.3 \u2192 0.3.4'".format(
                vcs=vcs_name
            ),
        ),
        (
            "bumpversion.cli",
            "INFO",
            "Would tag 'v0.3.4' with message 'Bump version: 0.3.3 \u2192 0.3.4' in {vcs} and not signing".format(
                vcs=vcs_name
            ),
        ),
    )


def test_listing(tmp_dir, vcs):
    tmp_dir.joinpath("please_list_me.txt").write_text("0.5.5")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
        [bumpversion]
        current_version = 0.5.5
        commit = False
        tag = False
        [bumpversion:file:please_list_me.txt]
        """).strip()
    )

    check_call([vcs, "init"])
    check_call([vcs, "add", "please_list_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    with LogCapture() as log_capture:
        main(["--list", "patch"])

    log_capture.check(
        ("bumpversion.list", "INFO", "current_version=0.5.5"),
        ("bumpversion.list", "INFO", "commit=False"),
        ("bumpversion.list", "INFO", "tag=False"),
        ("bumpversion.list", "INFO", "new_version=0.5.6"),
    )


def test_no_list_no_stdout(tmp_dir, vcs):
    tmp_dir.joinpath("please_dont_list_me.txt").write_text("0.5.5")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
        [bumpversion]
        files = please_dont_list_me.txt
        current_version = 0.5.5
        commit = False
        tag = False
        """).strip()
    )

    check_call([vcs, "init"])
    check_call([vcs, "add", "please_dont_list_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    output = run("bumpversion patch", shell=True, capture_output=True).stdout.decode()

    assert output == ""


def test_bump_non_numeric_parts(tmp_dir):
    tmp_dir.joinpath("with_pre_releases.txt").write_text("1.5.dev")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
        [bumpversion]
        current_version = 1.5.dev
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<release>[a-z]+))?
        serialize =
          {major}.{minor}.{release}
          {major}.{minor}

        [bumpversion:part:release]
        optional_value = gamma
        values =
          dev
          gamma
        [bumpversion:file:with_pre_releases.txt]
        """).strip()
    )

    main(["release", "--verbose"])

    assert tmp_dir.joinpath("with_pre_releases.txt").read_text() == "1.5"

    main(["minor", "--verbose"])

    assert tmp_dir.joinpath("with_pre_releases.txt").read_text() == "1.6.dev"


def test_optional_value_from_documentation(tmp_dir):
    tmp_dir.joinpath("optional_value_from_doc.txt").write_text("1.alpha")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
      [bumpversion]
      current_version = 1.alpha
      parse = (?P<num>\d+)(\.(?P<release>.*))?(\.)?
      serialize =
        {num}.{release}
        {num}

      [bumpversion:part:release]
      optional_value = gamma
      values =
        alpha
        beta
        gamma

      [bumpversion:file:optional_value_from_doc.txt]
      """).strip()
    )

    main(["release", "--verbose"])

    assert tmp_dir.joinpath("optional_value_from_doc.txt").read_text() == "1.beta"

    main(["release", "--verbose"])

    assert tmp_dir.joinpath("optional_value_from_doc.txt").read_text() == "1"


def test_python_pre_release_release_post_release(tmp_dir):
    tmp_dir.joinpath("python386.txt").write_text("1.0a")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
        [bumpversion]
        current_version = 1.0a

        # adapted from http://legacy.python.org/dev/peps/pep-0386/#the-new-versioning-algorithm
        parse = ^
            (?P<major>\d+)\.(?P<minor>\d+)   # minimum 'N.N'
            (?:
                (?P<prerel>[abc]|rc|dev)     # 'a' = alpha, 'b' = beta
                                             # 'c' or 'rc' = release candidate
                (?:
                    (?P<prerelversion>\d+(?:\.\d+)*)
                )?
            )?
            (?P<postdev>(\.post(?P<post>\d+))?(\.dev(?P<dev>\d+))?)?

        serialize =
          {major}.{minor}{prerel}{prerelversion}
          {major}.{minor}{prerel}
          {major}.{minor}

        [bumpversion:part:prerel]
        optional_value = d
        values =
          dev
          a
          b
          c
          rc
          d
        [bumpversion:file:python386.txt]
        """)
    )

    def file_content():
        return tmp_dir.joinpath("python386.txt").read_text()

    main(["prerel"])
    assert file_content() == "1.0b"

    main(["prerelversion"])
    assert file_content() == "1.0b1"

    main(["prerelversion"])
    assert file_content() == "1.0b2"

    main(["prerel"])  # now it's 1.0c
    main(["prerel"])
    assert file_content() == "1.0rc"

    main(["prerel"])
    assert file_content() == "1.0"

    main(["minor"])
    assert file_content() == "1.1dev"

    main(["prerel", "--verbose"])
    assert file_content() == "1.1a"


def test_part_first_value(tmp_dir):
    tmp_dir.joinpath("the_version.txt").write_text("0.9.4")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
        [bumpversion]
        current_version = 0.9.4

        [bumpversion:part:minor]
        first_value = 1

        [bumpversion:file:the_version.txt]
        """)
    )

    main(["major", "--verbose"])

    assert tmp_dir.joinpath("the_version.txt").read_text() == "1.1.0"


def test_multi_file_configuration(tmp_dir):
    tmp_dir.joinpath("FULL_VERSION.txt").write_text("1.0.3")
    tmp_dir.joinpath("MAJOR_VERSION.txt").write_text("1")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
        [bumpversion]
        current_version = 1.0.3

        [bumpversion:file:FULL_VERSION.txt]

        [bumpversion:file:MAJOR_VERSION.txt]
        serialize = {major}
        parse = \d+

        """)
    )

    main(["major", "--verbose"])
    assert "2.0.0" in tmp_dir.joinpath("FULL_VERSION.txt").read_text()
    assert "2" in tmp_dir.joinpath("MAJOR_VERSION.txt").read_text()

    main(["patch"])
    assert "2.0.1" in tmp_dir.joinpath("FULL_VERSION.txt").read_text()
    assert "2" in tmp_dir.joinpath("MAJOR_VERSION.txt").read_text()


def test_multi_file_configuration2(tmp_dir):
    tmp_dir.joinpath("setup.cfg").write_text("1.6.6")
    tmp_dir.joinpath("README.txt").write_text("MyAwesomeSoftware(TM) v1.6")
    tmp_dir.joinpath("BUILD_NUMBER").write_text("1.6.6+joe+38943")

    tmp_dir.joinpath(r".bumpversion.cfg").write_text(
        dedent(r"""
      [bumpversion]
      current_version = 1.6.6

      [something:else]

      [foo]

      [bumpversion:file:setup.cfg]

      [bumpversion:file:README.txt]
      parse = '(?P<major>\d+)\.(?P<minor>\d+)'
      serialize =
        {major}.{minor}

      [bumpversion:file:BUILD_NUMBER]
      serialize =
        {major}.{minor}.{patch}+{$USER}+{$BUILD_NUMBER}

      """)
    )

    os.environ["BUILD_NUMBER"] = "38944"
    os.environ["USER"] = "bob"
    main(["minor", "--verbose"])
    del os.environ["BUILD_NUMBER"]
    del os.environ["USER"]

    assert "1.7.0" in tmp_dir.joinpath("setup.cfg").read_text()
    assert "MyAwesomeSoftware(TM) v1.7" in tmp_dir.joinpath("README.txt").read_text()
    assert "1.7.0+bob+38944" in tmp_dir.joinpath("BUILD_NUMBER").read_text()

    os.environ["BUILD_NUMBER"] = "38945"
    os.environ["USER"] = "bob"
    main(["patch", "--verbose"])
    del os.environ["BUILD_NUMBER"]
    del os.environ["USER"]

    assert "1.7.1" in tmp_dir.joinpath("setup.cfg").read_text()
    assert "MyAwesomeSoftware(TM) v1.7" in tmp_dir.joinpath("README.txt").read_text()
    assert "1.7.1+bob+38945" in tmp_dir.joinpath("BUILD_NUMBER").read_text()


def test_search_replace_to_avoid_updating_unconcerned_lines(tmp_dir):
    tmp_dir.joinpath("requirements.txt").write_text(
        "Django>=1.5.6,<1.6\nMyProject==1.5.6"
    )
    tmp_dir.joinpath("CHANGELOG.md").write_text(
        dedent("""
    # https://keepachangelog.com/en/1.0.0/

    ## [Unreleased]
    ### Added
    - Foobar

    ## [0.0.1] - 2014-05-31
    ### Added
    - This CHANGELOG file to hopefully serve as an evolving example of a
      standardized open source project CHANGELOG.
    """)
    )

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
      [bumpversion]
      current_version = 1.5.6

      [bumpversion:file:requirements.txt]
      search = MyProject=={current_version}
      replace = MyProject=={new_version}

      [bumpversion:file:CHANGELOG.md]
      search = {#}{#} [Unreleased]
      replace = {#}{#} [Unreleased]

        {#}{#} [{new_version}] - {utcnow:%Y-%m-%d}
      """).strip()
    )

    with LogCapture() as log_capture:
        main(["minor", "--verbose"])

    utc_today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    log_capture.check(
        ("bumpversion.cli", "INFO", "Reading config file .bumpversion.cfg:"),
        (
            "bumpversion.cli",
            "INFO",
            "[bumpversion]\ncurrent_version = 1.5.6\n\n[bumpversion:file:requirements.txt]\nsearch = MyProject=={current_version}\nreplace = MyProject=={new_version}\n\n[bumpversion:file:CHANGELOG.md]\nsearch = {#}{#} [Unreleased]\nreplace = {#}{#} [Unreleased]\n\n  {#}{#} [{new_version}] - {utcnow:%Y-%m-%d}",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '1.5.6' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=1, minor=5, patch=6",
        ),
        ("bumpversion.cli", "INFO", "Attempting to increment part 'minor'"),
        ("bumpversion.cli", "INFO", "Values are now: major=1, minor=6, patch=0"),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsing version '1.6.0' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'",
        ),
        (
            "bumpversion.version_part",
            "INFO",
            "Parsed the following values: major=1, minor=6, patch=0",
        ),
        ("bumpversion.cli", "INFO", "New version will be '1.6.0'"),
        (
            "bumpversion.cli",
            "INFO",
            "Asserting files requirements.txt, CHANGELOG.md contain the version string...",
        ),
        (
            "bumpversion.utils",
            "INFO",
            "Found 'MyProject==1.5.6' in requirements.txt at line 1: MyProject==1.5.6",
        ),
        (
            "bumpversion.utils",
            "INFO",
            "Found '## [Unreleased]' in CHANGELOG.md at line 3: ## [Unreleased]",
        ),
        ("bumpversion.utils", "INFO", "Changing file requirements.txt:"),
        (
            "bumpversion.utils",
            "INFO",
            "--- a/requirements.txt\n+++ b/requirements.txt\n@@ -1,2 +1,2 @@\n Django>=1.5.6,<1.6\n-MyProject==1.5.6\n+MyProject==1.6.0",
        ),
        ("bumpversion.utils", "INFO", "Changing file CHANGELOG.md:"),
        (
            "bumpversion.utils",
            "INFO",
            "--- a/CHANGELOG.md\n+++ b/CHANGELOG.md\n@@ -2,6 +2,8 @@\n # https://keepachangelog.com/en/1.0.0/\n \n ## [Unreleased]\n+\n+## [1.6.0] - %s\n ### Added\n - Foobar\n "
            % utc_today,
        ),
        ("bumpversion.list", "INFO", "current_version=1.5.6"),
        ("bumpversion.list", "INFO", "new_version=1.6.0"),
        ("bumpversion.cli", "INFO", "Writing to config file .bumpversion.cfg:"),
        (
            "bumpversion.cli",
            "INFO",
            "[bumpversion]\ncurrent_version = 1.6.0\n\n[bumpversion:file:requirements.txt]\nsearch = MyProject=={current_version}\nreplace = MyProject=={new_version}\n\n[bumpversion:file:CHANGELOG.md]\nsearch = {#}{#} [Unreleased]\nreplace = {#}{#} [Unreleased]\n\t\n\t{#}{#} [{new_version}] - {utcnow:%Y-%m-%d}\n\n",
        ),
    )

    assert "MyProject==1.6.0" in tmp_dir.joinpath("requirements.txt").read_text()
    assert "Django>=1.5.6" in tmp_dir.joinpath("requirements.txt").read_text()


def test_search_replace_expanding_changelog(tmp_dir):
    tmp_dir.joinpath("CHANGELOG.md").write_text(
        dedent("""
    My awesome software project Changelog
    =====================================

    Unreleased
    ----------

    * Some nice feature
    * Some other nice feature

    Version v8.1.1 (2014-05-28)
    ---------------------------

    * Another old nice feature

    """)
    )

    config_content = dedent("""
      [bumpversion]
      current_version = 8.1.1

      [bumpversion:file:CHANGELOG.md]
      search =
        Unreleased
        ----------
      replace =
        Unreleased
        ----------
        Version v{new_version} ({now:%Y-%m-%d})
        ---------------------------
    """)

    tmp_dir.joinpath(".bumpversion.cfg").write_text(config_content)

    main(["minor", "--verbose"])

    predate = dedent("""
      Unreleased
      ----------
      Version v8.2.0 (20
      """).strip()

    postdate = dedent("""
      )
      ---------------------------

      * Some nice feature
      * Some other nice feature
      """).strip()

    assert predate in tmp_dir.joinpath("CHANGELOG.md").read_text()
    assert postdate in tmp_dir.joinpath("CHANGELOG.md").read_text()


def test_non_matching_search_does_not_modify_file(tmp_dir):
    changelog_content = dedent("""
    # Unreleased
    
    * bullet point A
    
    # Release v'older' (2019-09-17)
    
    * bullet point B
    """)

    config_content = dedent("""
      [bumpversion]
      current_version = 1.0.3

      [bumpversion:file:CHANGELOG.md]
      search = Not-yet-released
      replace = Release v{new_version} ({now:%Y-%m-%d})
    """)

    tmp_dir.joinpath("CHANGELOG.md").write_text(changelog_content)
    tmp_dir.joinpath(".bumpversion.cfg").write_text(config_content)

    with pytest.raises(
        exceptions.VersionNotFoundException,
        match="Did not find 'Not-yet-released' in file: 'CHANGELOG.md'",
    ):
        main(["patch", "--verbose"])

    assert changelog_content == tmp_dir.joinpath("CHANGELOG.md").read_text()
    assert config_content in tmp_dir.joinpath(".bumpversion.cfg").read_text()


def test_search_replace_cli(tmp_dir):
    tmp_dir.joinpath("file89").write_text(
        "My birthday: 3.5.98\nCurrent version: 3.5.98"
    )
    main(
        [
            "--current-version",
            "3.5.98",
            "--search",
            "Current version: {current_version}",
            "--replace",
            "Current version: {new_version}",
            "minor",
            "file89",
        ]
    )

    assert (
        tmp_dir.joinpath("file89").read_text()
        == "My birthday: 3.5.98\nCurrent version: 3.6.0"
    )


def test_deprecation_warning_files_in_global_configuration(tmp_dir):
    tmp_dir.joinpath("fileX").write_text("3.2.1")
    tmp_dir.joinpath("fileY").write_text("3.2.1")
    tmp_dir.joinpath("fileZ").write_text("3.2.1")

    tmp_dir.joinpath(".bumpversion.cfg").write_text("""[bumpversion]
current_version = 3.2.1
files = fileX fileY fileZ
""")

    warning_registry = getattr(bumpversion, "__warningregistry__", None)
    if warning_registry:
        warning_registry.clear()
    warnings.resetwarnings()
    warnings.simplefilter("always")
    with warnings.catch_warnings(record=True) as received_warnings:
        main(["patch"])

    w = received_warnings.pop()
    assert issubclass(w.category, PendingDeprecationWarning)
    assert "'files =' configuration will be deprecated, please use" in str(w.message)


def test_deprecation_warning_multiple_files_cli(tmp_dir):
    tmp_dir.joinpath("fileA").write_text("1.2.3")
    tmp_dir.joinpath("fileB").write_text("1.2.3")
    tmp_dir.joinpath("fileC").write_text("1.2.3")

    warning_registry = getattr(bumpversion, "__warningregistry__", None)
    if warning_registry:
        warning_registry.clear()
    warnings.resetwarnings()
    warnings.simplefilter("always")
    with warnings.catch_warnings(record=True) as received_warnings:
        main(["--current-version", "1.2.3", "patch", "fileA", "fileB", "fileC"])

    w = received_warnings.pop()
    assert issubclass(w.category, PendingDeprecationWarning)
    assert "Giving multiple files on the command line will be deprecated" in str(
        w.message
    )


def test_file_specific_config_inherits_parse_serialize(tmp_dir):
    tmp_dir.joinpath("todays_ice_cream").write_text("14-chocolate")
    tmp_dir.joinpath("todays_cake").write_text("14-chocolate")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
      [bumpversion]
      current_version = 14-chocolate
      parse = (?P<major>\d+)(\-(?P<flavor>[a-z]+))?
      serialize =
          {major}-{flavor}
          {major}

      [bumpversion:file:todays_ice_cream]
      serialize =
          {major}-{flavor}

      [bumpversion:file:todays_cake]

      [bumpversion:part:flavor]
      values =
          vanilla
          chocolate
          strawberry
      """)
    )

    main(["flavor"])

    assert tmp_dir.joinpath("todays_cake").read_text() == "14-strawberry"
    assert tmp_dir.joinpath("todays_ice_cream").read_text() == "14-strawberry"

    main(["major"])

    assert tmp_dir.joinpath("todays_ice_cream").read_text() == "15-vanilla"
    assert tmp_dir.joinpath("todays_cake").read_text() == "15"


def test_multi_line_search_is_found(tmp_dir):
    tmp_dir.joinpath("the_alphabet.txt").write_text(
        dedent("""
      A
      B
      C
    """)
    )

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
    [bumpversion]
    current_version = 9.8.7

    [bumpversion:file:the_alphabet.txt]
    search =
      A
      B
      C
    replace =
      A
      B
      C
      {new_version}
      """).strip()
    )

    main(["major"])

    assert (
        dedent("""
      A
      B
      C
      10.0.0
    """)
        == tmp_dir.joinpath("the_alphabet.txt").read_text()
    )


@xfail_if_old_configparser
def test_configparser_empty_lines_in_values(tmp_dir):
    tmp_dir.joinpath("CHANGES.rst").write_text(
        dedent("""
    My changelog
    ============

    current
    -------

    """)
    )

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
    [bumpversion]
    current_version = 0.4.1

    [bumpversion:file:CHANGES.rst]
    search =
      current
      -------
    replace = current
      -------


      {new_version}
      -------
      """).strip()
    )

    main(["patch"])
    assert (
        dedent("""
      My changelog
      ============
      current
      -------


      0.4.2
      -------

    """)
        == tmp_dir.joinpath("CHANGES.rst").read_text()
    )


def test_regression_tag_name_with_hyphens(tmp_dir, git):
    tmp_dir.joinpath("some_source.txt").write_text("2014.10.22")
    check_call([git, "init"])
    check_call([git, "add", "some_source.txt"])
    check_call([git, "commit", "-m", "initial commit"])
    check_call([git, "tag", "very-unrelated-but-containing-lots-of-hyphens"])

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
    [bumpversion]
    current_version = 2014.10.22
    """)
    )

    main(["patch", "some_source.txt"])


def test_unclean_repo_exception(tmp_dir, git, caplog):
    config = """[bumpversion]
current_version = 0.0.0
tag = True
commit = True
message = XXX
"""
    tmp_dir.joinpath("file1").write_text("foo")

    # If I have a repo with an initial commit
    check_call([git, "init"])
    check_call([git, "add", "file1"])
    check_call([git, "commit", "-m", "initial commit"])

    # If I add the bumpversion config, uncommitted
    tmp_dir.joinpath(".bumpversion.cfg").write_text(config)

    # I expect bumpversion patch to fail
    with pytest.raises(subprocess.CalledProcessError):
        main(["patch"])

    # And return the output of the failing command
    assert "Failed to run" in caplog.text


def test_regression_characters_after_last_label_serialize_string(tmp_dir):
    tmp_dir.joinpath("bower.json").write_text("""
    {
      "version": "1.0.0",
      "dependency1": "1.0.0",
    }
    """)

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
    [bumpversion]
    current_version = 1.0.0

    [bumpversion:file:bower.json]
    parse = "version": "(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    serialize = "version": "{major}.{minor}.{patch}"
    """)
    )

    main(["patch", "bower.json"])


def test_regression_dont_touch_capitalization_of_keys_in_config(tmp_dir):
    tmp_dir.joinpath("setup.cfg").write_text(
        dedent("""
    [bumpversion]
    current_version = 0.1.0

    [other]
    DJANGO_SETTINGS = Value
    """)
    )

    main(["patch"])

    assert (
        dedent("""
    [bumpversion]
    current_version = 0.1.1

    [other]
    DJANGO_SETTINGS = Value
    """).strip()
        == tmp_dir.joinpath("setup.cfg").read_text().strip()
    )


def test_regression_new_version_cli_in_files(tmp_dir):
    """
    Reported here: https://github.com/peritus/bumpversion/issues/60
    """

    tmp_dir.joinpath("myp___init__.py").write_text("__version__ = '0.7.2'")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
        [bumpversion]
        current_version = 0.7.2
        message = v{new_version}
        tag_name = {new_version}
        tag = true
        commit = true
        [bumpversion:file:myp___init__.py]
        """).strip()
    )

    main("patch --allow-dirty --verbose --new-version 0.9.3".split(" "))

    assert tmp_dir.joinpath("myp___init__.py").read_text() == "__version__ = '0.9.3'"
    assert "current_version = 0.9.3" in tmp_dir.joinpath(".bumpversion.cfg").read_text()


def test_correct_interpolation_for_setup_cfg_files(tmp_dir, configfile):
    """
    Reported here: https://github.com/c4urself/bump2version/issues/21
    """

    tmp_dir.joinpath("file.py").write_text("XX-XX-XXXX v. X.X.X")

    if configfile == "setup.cfg":
        tmp_dir.joinpath(configfile).write_text(
            dedent("""
            [bumpversion]
            current_version = 0.7.2
            search = XX-XX-XXXX v. X.X.X
            replace = {now:%%m-%%d-%%Y} v. {new_version}
            [bumpversion:file:file.py]
            """).strip()
        )
    else:
        tmp_dir.joinpath(configfile).write_text(
            dedent("""
            [bumpversion]
            current_version = 0.7.2
            search = XX-XX-XXXX v. X.X.X
            replace = {now:%m-%d-%Y} v. {new_version}
            [bumpversion:file:file.py]
            """).strip()
        )

    main(["major"])

    assert (
        datetime.now().strftime("%m-%d-%Y") + " v. 1.0.0"
        == tmp_dir.joinpath("file.py").read_text()
    )
    assert "current_version = 1.0.0" in tmp_dir.joinpath(configfile).read_text()


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_retain_newline(tmp_dir, configfile, newline):
    tmp_dir.joinpath("file.py").write_bytes(
        dedent("""
        0.7.2
        Some Content
        """)
        .strip()
        .encode(encoding="UTF-8")
        .replace(b"\n", newline)
    )

    tmp_dir.joinpath(configfile).write_bytes(
        dedent("""
        [bumpversion]
        current_version = 0.7.2
        search = {current_version}
        replace = {new_version}
        [bumpversion:file:file.py]
        """)
        .strip()
        .encode(encoding="UTF-8")
        .replace(b"\n", newline)
    )

    main(["major"])

    assert newline in tmp_dir.joinpath("file.py").read_bytes()
    new_config = tmp_dir.joinpath(configfile).read_bytes()
    assert newline in new_config

    # Ensure there is only a single newline (not two) at the end of the file
    # and that it is of the right type
    assert new_config.endswith(b"[bumpversion:file:file.py]" + newline)


def test_no_configured_files(tmp_dir, vcs):
    tmp_dir.joinpath("please_ignore_me.txt").write_text("0.5.5")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
        [bumpversion]
        current_version = 1.1.1
        [bumpversion:file:please_ignore_me.txt]
        """).strip()
    )
    main(["--no-configured-files", "patch"])
    assert tmp_dir.joinpath("please_ignore_me.txt").read_text() == "0.5.5"


def test_no_configured_files_still_file_args_work(tmp_dir, vcs):
    tmp_dir.joinpath("please_ignore_me.txt").write_text("0.5.5")
    tmp_dir.joinpath("please_update_me.txt").write_text("1.1.1")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent("""
        [bumpversion]
        current_version = 1.1.1
        [bumpversion:file:please_ignore_me.txt]
        """).strip()
    )
    main(["--no-configured-files", "patch", "please_update_me.txt"])
    assert tmp_dir.joinpath("please_ignore_me.txt").read_text() == "0.5.5"
    assert tmp_dir.joinpath("please_update_me.txt").read_text() == "1.1.2"


class TestSplitArgsInOptionalAndPositional:
    def test_all_optional(self):
        params = ["--allow-dirty", "--verbose", "-n", "--tag-name", '"Tag"']
        positional, optional = split_args_in_optional_and_positional(params)

        assert positional == []
        assert optional == params

    def test_all_positional(self):
        params = ["minor", "setup.py"]
        positional, optional = split_args_in_optional_and_positional(params)

        assert positional == params
        assert optional == []

    def test_no_args(self):
        assert split_args_in_optional_and_positional([]) == ([], [])

    def test_short_optionals(self):
        params = ["-m", '"Commit"', "-n"]
        positional, optional = split_args_in_optional_and_positional(params)

        assert positional == []
        assert optional == params

    def test_1optional_2positional(self):
        params = ["-n", "major", "setup.py"]
        positional, optional = split_args_in_optional_and_positional(params)

        assert positional == ["major", "setup.py"]
        assert optional == ["-n"]

    def test_2optional_1positional(self):
        params = ["-n", "-m", '"Commit"', "major"]
        positional, optional = split_args_in_optional_and_positional(params)

        assert positional == ["major"]
        assert optional == ["-n", "-m", '"Commit"']

    def test_2optional_mixed_2positional(self):
        params = ["--allow-dirty", "-m", '"Commit"', "minor", "setup.py"]
        positional, optional = split_args_in_optional_and_positional(params)

        assert positional == ["minor", "setup.py"]
        assert optional == ["--allow-dirty", "-m", '"Commit"']


def test_build_number_configuration(tmp_dir):
    tmp_dir.joinpath("VERSION.txt").write_text("2.1.6-5123")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
        [bumpversion]
        current_version: 2.1.6-5123
        parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\-(?P<build>\d+)
        serialize = {major}.{minor}.{patch}-{build}

        [bumpversion:file:VERSION.txt]

        [bumpversion:part:build]
        independent = True
        """)
    )

    main(["build"])
    assert tmp_dir.joinpath("VERSION.txt").read_text() == "2.1.6-5124"

    main(["major"])
    assert tmp_dir.joinpath("VERSION.txt").read_text() == "3.0.0-5124"

    main(["build"])
    assert tmp_dir.joinpath("VERSION.txt").read_text() == "3.0.0-5125"


def test_independent_falsy_value_in_config_does_not_bump_independently(tmp_dir):
    tmp_dir.joinpath("VERSION").write_text("2.1.0-5123")

    tmp_dir.joinpath(".bumpversion.cfg").write_text(
        dedent(r"""
        [bumpversion]
        current_version: 2.1.0-5123
        parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\-(?P<build>\d+)
        serialize = {major}.{minor}.{patch}-{build}

        [bumpversion:file:VERSION]

        [bumpversion:part:build]
        independent = 0
        """)
    )

    main(["build"])
    assert tmp_dir.joinpath("VERSION").read_text() == "2.1.0-5124"

    main(["major"])
    assert tmp_dir.joinpath("VERSION").read_text() == "3.0.0-0"
