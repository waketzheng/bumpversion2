from __future__ import annotations

import errno
import logging
import os
import subprocess
from tempfile import NamedTemporaryFile

from bumpversion.exceptions import (
    MercurialDoesNotSupportSignedTagsException,
    WorkingDirectoryIsDirtyException,
)

logger = logging.getLogger(__name__)


class BaseVCS:
    _TEST_USABLE_COMMAND: list[str]
    _COMMIT_COMMAND: list[str]

    @classmethod
    def commit(cls, message, context, extra_args=None) -> None:
        extra_args = extra_args or []
        with NamedTemporaryFile("wb", delete=False) as f:
            f.write(message.encode("utf-8"))
        env = os.environ.copy()
        env["HGENCODING"] = "utf-8"
        for key in ("current_version", "new_version"):
            env[str("BUMPVERSION_" + key.upper())] = str(context[key])
        try:
            subprocess.check_output(
                cls._COMMIT_COMMAND + [f.name] + extra_args, env=env
            )
        except subprocess.CalledProcessError as exc:
            err_msg = f"Failed to run {exc.cmd}: return code {exc.returncode}, output: {exc.output}"
            logger.exception(err_msg)
            raise exc
        finally:
            os.unlink(f.name)

    @classmethod
    def is_usable(cls) -> bool:
        try:
            return (
                subprocess.call(
                    cls._TEST_USABLE_COMMAND,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                )
                == 0
            )
        except OSError as e:
            if e.errno in (errno.ENOENT, errno.EACCES, errno.ENOTDIR):
                return False
            raise


class Git(BaseVCS):
    _TEST_USABLE_COMMAND = ["git", "rev-parse", "--git-dir"]
    _COMMIT_COMMAND = ["git", "commit", "-F"]

    @classmethod
    def assert_nondirty(cls) -> None:
        lines = [
            line.strip()
            for line in subprocess.check_output(
                ["git", "status", "--porcelain"]
            ).splitlines()
            if not line.strip().startswith(b"??")
        ]

        if lines:
            raise WorkingDirectoryIsDirtyException(
                "Git working directory is not clean:\n{}".format(
                    b"\n".join(lines).decode()
                )
            )

    @classmethod
    def latest_tag_info(cls) -> dict:
        try:
            # git-describe doesn't update the git-index, so we do that
            subprocess.check_output(["git", "update-index", "--refresh"])

            # get info about the latest tag in git
            describe_out = (
                subprocess.check_output(
                    [
                        "git",
                        "describe",
                        "--dirty",
                        "--tags",
                        "--long",
                        "--abbrev=40",
                        "--match=v*",
                    ],
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .split("-")
            )
        except subprocess.CalledProcessError:
            logger.debug("Error when running git describe")
            return {}

        info: dict = {}

        if describe_out[-1].strip() == "dirty":
            info["dirty"] = True
            describe_out.pop()

        info["commit_sha"] = describe_out.pop().lstrip("g")
        info["distance_to_latest_tag"] = int(describe_out.pop())
        info["current_version"] = "-".join(describe_out).lstrip("v")

        return info

    @classmethod
    def add_path(cls, path) -> None:
        subprocess.check_output(["git", "add", "--update", "--ignore-errors", path])

    @classmethod
    def tag(cls, sign, name, message) -> None:
        """
        Create a tag of the new_version in VCS.

        If only name is given, bumpversion uses a lightweight tag.
        Otherwise, it utilizes an annotated tag.
        """
        command = ["git", "tag", name]
        if sign:
            command += ["--sign"]
        if message:
            command += ["--message", message]
        subprocess.check_output(command)


class Mercurial(BaseVCS):
    _TEST_USABLE_COMMAND = ["hg", "root"]
    _COMMIT_COMMAND = ["hg", "commit", "--logfile"]

    @classmethod
    def latest_tag_info(cls) -> dict:
        return {}

    @classmethod
    def assert_nondirty(cls) -> None:
        lines = [
            line.strip()
            for line in subprocess.check_output(["hg", "status", "-mard"]).splitlines()
            if not line.strip().startswith(b"??")
        ]

        if lines:
            raise WorkingDirectoryIsDirtyException(
                "Mercurial working directory is not clean:\n{}".format(
                    b"\n".join(lines).decode()
                )
            )

    @classmethod
    def add_path(cls, path) -> None:
        pass

    @classmethod
    def tag(cls, sign, name, message) -> None:
        command = ["hg", "tag", name]
        if sign:
            raise MercurialDoesNotSupportSignedTagsException(
                "Mercurial does not support signed tags."
            )
        if message:
            command += ["--message", message]
        subprocess.check_output(command)
