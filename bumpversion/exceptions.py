from __future__ import annotations


class BumpVersionException(Exception):
    """Custom base class for all BumpVersion exception types."""


class MessageMixin:
    def __init__(self, message) -> None:
        self.message = message


class IncompleteVersionRepresentationException(MessageMixin, BumpVersionException): ...


class MissingValueForSerializationException(MessageMixin, BumpVersionException): ...


class WorkingDirectoryIsDirtyException(MessageMixin, BumpVersionException): ...


class MercurialDoesNotSupportSignedTagsException(
    MessageMixin, BumpVersionException
): ...


class VersionNotFoundException(BumpVersionException):
    """A version number was not found in a source file."""


class InvalidVersionPartException(BumpVersionException):
    """The specified part (e.g. 'bugfix') was not found"""
