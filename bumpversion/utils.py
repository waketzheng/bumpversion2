import logging
import os
import re
from argparse import _AppendAction
from difflib import unified_diff
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from bumpversion.exceptions import VersionNotFoundException

if TYPE_CHECKING:
    from .version_part import Version

logger = logging.getLogger(__name__)


class DiscardDefaultIfSpecifiedAppendAction(_AppendAction):
    """
    Fixes bug http://bugs.python.org/issue16399 for 'append' action
    """

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(self, "_discarded_default", None) is None:
            setattr(namespace, self.dest, [])
            self._discarded_default = True  # pylint: disable=attribute-defined-outside-init

        super().__call__(parser, namespace, values, option_string=None)


def keyvaluestring(d: dict) -> str:
    return ", ".join("{}={}".format(k, v) for k, v in sorted(d.items()))


def prefixed_environ() -> Dict[str, str]:
    return {"${}".format(key): value for key, value in os.environ.items()}


class ConfiguredFile:
    def __init__(self, path, versionconfig) -> None:
        self.path = path
        self._versionconfig = versionconfig

    def should_contain_version(self, version, context) -> None:
        """
        Raise VersionNotFound if the version number isn't present in this file.

        Return normally if the version number is in fact present.
        """
        context["current_version"] = self._versionconfig.serialize(version, context)
        search_expression = self._versionconfig.search.format(**context)

        if self.contains(search_expression):
            return

        # the `search` pattern did not match, but the original supplied
        # version number (representing the same version part values) might
        # match instead.

        # check whether `search` isn't customized, i.e. should match only
        # very specific parts of the file
        search_pattern_is_default = self._versionconfig.search == "{current_version}"

        if search_pattern_is_default and self.contains(version.original):
            # original version is present and we're not looking for something
            # more specific -> this is accepted as a match
            return

        # version not found
        raise VersionNotFoundException(
            "Did not find '{}' in file: '{}'".format(search_expression, self.path)
        )

    def contains(self, search: Optional[str]) -> bool:
        if not search:
            return False

        with open(self.path, "rt", encoding="utf-8") as f:
            search_lines = search.splitlines()
            lookbehind = []

            for lineno, line in enumerate(f.readlines()):
                lookbehind.append(line.rstrip("\n"))

                if len(lookbehind) > len(search_lines):
                    lookbehind = lookbehind[1:]

                if (
                    search_lines[0] in lookbehind[0]
                    and search_lines[-1] in lookbehind[-1]
                    and search_lines[1:-1] == lookbehind[1:-1]
                ):
                    logger.info(
                        "Found '%s' in %s at line %s: %s",
                        search,
                        self.path,
                        lineno - (len(lookbehind) - 1),
                        line.rstrip(),
                    )
                    return True
        return False

    def replace(
        self,
        current_version: "Version",
        new_version: "Version",
        context: dict,
        dry_run: bool,
    ) -> None:
        with open(self.path, "rt", encoding="utf-8") as f:
            file_content_before = f.read()
            file_new_lines = f.newlines

        context["current_version"] = self._versionconfig.serialize(current_version, context)
        context["new_version"] = self._versionconfig.serialize(new_version, context)

        search_for = self._versionconfig.search.format(**context)
        replace_with = self._versionconfig.replace.format(**context)
        if Path(self.path).name == "pyproject.toml":
            file_content_after = re.sub(
                rf"^(version\s*=\s*)(?P<quote>['\"])({search_for})(?P=quote)",
                rf"\1\g<quote>{replace_with}\g<quote>",
                file_content_before,
                flags=re.M,
            )
        else:
            file_content_after = file_content_before.replace(search_for, replace_with)

        if file_content_before == file_content_after:
            # TODO expose this to be configurable
            file_content_after = file_content_before.replace(current_version.original, replace_with)
        if file_content_before != file_content_after:
            logger.info("%s file %s:", "Would change" if dry_run else "Changing", self.path)
            logger.info(
                "\n".join(
                    list(
                        unified_diff(
                            file_content_before.splitlines(),
                            file_content_after.splitlines(),
                            lineterm="",
                            fromfile="a/" + self.path,
                            tofile="b/" + self.path,
                        )
                    )
                )
            )
        else:
            logger.info(
                "%s file %s",
                "Would not change" if dry_run else "Not changing",
                self.path,
            )

        if not dry_run:
            linesep = file_new_lines[0] if isinstance(file_new_lines, tuple) else file_new_lines
            with open(self.path, "wt", encoding="utf-8", newline=linesep) as f:
                f.write(file_content_after)

    def __str__(self) -> str:
        return self.path

    def __repr__(self) -> str:
        return "<bumpversion.ConfiguredFile:{}>".format(self.path)
