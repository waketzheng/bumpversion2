Examples
========

1. Basic example - command line
-------------------------------

Update the ``patch`` part of the version in file ``VERSION``. The current version is specified explicitly
on the command line.

``VERSION``::

    1.2.0

The following command line ``bumpversion patch --current-version 1.2.0 VERSION`` update the version inside the file:

``VERSION``::

    1.2.1

2. Basic example - configuration file
-------------------------------------

Update the ``patch`` part of the version in file ``VERSION``. The current and new version are specified explicitly
in a configuration file.

``VERSION``::

    1.2.0

``mybumpconfig.cfg``::

    [bumpversion]
    current_version: 1.2.0
    files: VERSION

``bumpversion patch --config-file mybumpconfig.cfg``

``VERSION``::

    1.2.1

3. Basic example - configuration file and new syntax
----------------------------------------------------

``files`` is deprecated. It is better to use ``[bumpversion:file:...]`` sections instead.

``mybumpconfig.cfg``::

    [bumpversion]
    current_version: 1.2.0

    [bumpversion:file:VERSION]

4. Basic example - default configuration file
---------------------------------------------

If not specified on the command line, **ADVbumpversion** will use the configuration file ``.bumpversion.cfg`` in the
current directory.

``.bumpversion.cfg``::

    [bumpversion]
    current_version: 1.2.0

    [bumpversion:file:VERSION]

``bumpversion patch``

5. Custom version format
------------------------

The default configuration format is ``major.minor.patch`` and is parsed with the regular expression
``(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)``. You can specify your own format with ``parse`` and ``serialize``.

For example, you may want to append a ``build`` part to the version as in ``2.1.0-5123``.

``.bumpconfig.cfg``::

    [bumpversion]
    current_version: 2.1.0-5123
    parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\-(?P<build>\d+)
    serialize = {major}.{minor}.{patch}-{build}

    [bumpversion:file:VERSION]

The following command::

    bumpversion build

produces the version: ``2.1.0-5124``. The command::

    bumpversion major

produces the version: ``3.0.0-0``.

6. Custom version format - build number
---------------------------------------

In the previous example, the ``build`` part is reset like the other parts because the ``major`` part was incremented.
This is sometimes not what you want. You may want to keep this part independent of the other parts. To do so,
configure explicitly this part:

``.bumpconfig.cfg``::

    [bumpversion]
    current_version: 2.1.0-5123
    parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\-(?P<build>\d+)
    serialize = {major}.{minor}.{patch}-{build}

    [bumpversion:file:VERSION]

    [bumpversion:part:build]
    independent = True

In this case, the command::

    bumpversion major

produces the version: ``3.0.0-5123`` with the ``build`` part untouched.

7. Custom version format - textual parts
----------------------------------------

By default, version parts are numerical but you can customize them and give a list of textual values.

``VERSION.txt``::

    2.1.0-alpha

``.bumpconfig.cfg``::

    [bumpversion]
    current_version: 2.1.0-alpha
    parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\-(?P<release>[a-z]+)
    serialize = {major}.{minor}.{patch}-{release}

    [bumpversion:file:VERSION.txt]

    [bumpversion:part:release]
    values =
        alpha
        beta
        gamma

The command ``bumpversion release`` produces the version ``2.1.0-beta``.

8. Custom version format - optional part
----------------------------------------

In the previous example, the ``release`` part is mandatory. You can make it optional.

``VERSION.txt``::

    2.1.0-alpha

``.bumpconfig.cfg``::

    [bumpversion]
    current_version: 2.1.0-alpha
    parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(\-(?P<release>[a-z]+))?
    serialize =
        {major}.{minor}.{patch}-{release}
        {major}.{minor}.{patch}

    [bumpversion:file:VERSION.txt]

    [bumpversion:part:release]
    optional_value = gamma
    values =
        alpha
        beta
        gamma

``parse`` has been adapted to make the parsing of ``release`` optional (with ``(...)?``, ``serialize`` has now two
possible values: ``{major}.{minor}.{patch}-{release}`` or ``{major}.{minor}.{patch}``, and ``gamma`` is explicitly
marked as optional for the ``release`` par.

The command ``bumpversion release`` produces the version ``2.1.0-beta``. A second ``bumpversion release`` produces the
version ``2.1.0``.

9. PEP 440 -- Version Identification and Dependency Specification
-----------------------------------------------------------------

`PEP 440 <http://legacy.python.org/dev/peps/pep-0440/>`_  describes a scheme for identifying versions of Python
software distributions, and declaring dependencies on particular versions.

Canonical public version identifiers must comply with the following scheme::

    [N!]N(.N)*[{a|b|rc}N][.postN][.devN]

The scheme is very generic and includes elements that are not often used (like the epoch eleement at the beginning).
A less compless (and compliant) format is the following::

    N.N[{a|b|rc}N][.postN][.devN]

Examples of versions::

    1.0
    1.0a1               # 1.0 alpha 1
    1.0b2               # 1.0 beta 2
    1.0b2.dev1          # Development release 1 of version 1.0 beta 2
    1.0.post1           # Post-release 1 of version 1.0 (i.e. minor correction)
    1.0.post1.dev2      # Development release 2 of post-release 1 of version 1.0
    5.9rc3.dev1         # Development release 1 of Release candidate 3 of version 5.9

To use this scheme, you can define the following configuration::

    [bumpversion]
    current_version = 1.0a1

    parse =
        (?P<major>\d+)\.(?P<minor>\d+)              # major and minor
        (?:(?P<pre>(?:[ab]|rc))(?P<prenum>\d+))?    # 'a' = alpha, 'b' = beta, 'rc' = release candidate
        (?:\.post(?P<post>\d+))?                    # post-release
        (?:\.dev(?P<dev>\d+))?                      # development

    serialize =
        {major}.{minor}{pre}{prenum}.post{post}.dev{dev}
        {major}.{minor}.post{post}.dev{dev}
        {major}.{minor}{pre}{prenum}.post{post}
        {major}.{minor}.post{post}
        {major}.{minor}{pre}{prenum}.dev{dev}
        {major}.{minor}.dev{dev}
        {major}.{minor}{pre}{prenum}
        {major}.{minor}

    [bumpversion:part:pre]
    optional_value = stable
    values =
        a
        b
        rc
        stable

    [bumpversion:part:prenum]
    first_value = 1

    [bumpversion:file:VERSION.txt]

The following commands bump successively the version:

==========================  =======================
Command                     Version
==========================  =======================
``bumpversion prenum``      ``1.0a2``
``bumpversion pre``         ``1.0b1``
``bumpversion pre``         ``1.0rc1``
``bumpversion pre``         ``1.0``
``bumpversion post``        ``1.0.post1``
``bumpversion dev``         ``1.0.post1.dev1``
``bumpversion minor``       ``1.1a1``
``bumpversion dev``         ``1.1a1.dev1``
``bumpversion pre``         ``1.1b1``
``bumpversion pre``         ``1.1rc1``
``bumpversion pre``         ``1.1``
``bumpversion dev``         ``1.1.dev1``
==========================  =======================

10. Semantic Versioning (SemVer)
--------------------------------

`Semantic Versioning (SemVer) <https://semver.org>`_ is a simple set of rules and requirements that dictate how version numbers
are assigned and incremented. SemVer versions have the following format::

    X.Y.Z[-{a-zA-Z-}+(.{a-zA-Z-})*][+{a-zA-Z-}+(.{a-zA-Z-})*]

**Note**: this is a simplified expression.

Examples of SemVer versions::

    1.0.0
    1.0.0-alpha.1       # 1.0.0 alpha 1
    1.0.0-beta.2        # 1.0.0 beta 2
    1.0.0-dev.1         # Development release 1 of version 1.0.0
    1.0.1               # Patch 1 of version 1.0.0
    1.0.0-post.1.dev.2  # Development release 2 of post-release 1 of version 1.0.0
    1.0.0-beta.2+5664   # 1.0.0 beta 2 build number 5664

The following configuration file can be used to implement SemVer (again, simplified)::

    [bumpversion]
    current_version = 1.0.0

    parse =
        (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)              # major, minor and patch
        (?:\-(?P<pre>(?:dev|alpha|beta|rc))\.(?P<prenum>\d+))?      # pre-release
        (?:\+(?P<build>\d+))?                                       # build metadata

    serialize =
        {major}.{minor}.{patch}-{pre}.{prenum}+{build}
        {major}.{minor}.{patch}-{pre}.{prenum}
        {major}.{minor}.{patch}+{build}
        {major}.{minor}.{patch}

    [bumpversion:part:pre]
    optional_value = stable
    values =
        dev
        alpha
        beta
        rc
        stable

    [bumpversion:part:prenum]
    first_value = 1

    [bumpversion:part:build]
    independent = True

    [bumpversion:file:VERSION.txt]

**Note**: This configuration defines 5 values for pre-release part and assumes that the build part is numerical.
SemVer permits more complex parts such as ``x.7.z.92-beta.1.2+exp.sha.5114f85``.

The following commands bump successively the version:

==================================================  =======================
Command                                             Version
==================================================  =======================
``bumpversion prenum``                              ``1.0.1-dev1.1``
``bumpversion pre``                                 ``1.0.1-alpha.1``
``bumpversion pre``                                 ``1.0.1-beta.1``
``bumpversion pre``                                 ``1.0.1-rc.1``
``bumpversion premnum``                             ``1.0.1-rc.2``
``bumpversion pre``                                 ``1.0.1``
``bumpversion build``                               ``1.0.1+1``
``bumpversion build``                               ``1.0.1+2``
``bumpversion build --new-version 1.0.1+5134``      ``1.0.1-rc+5134``
``bumpversion patch``                               ``1.0.2-dev.1+5134``
``bumpversion pre``                                 ``1.0.2-alpha.1+5134``
``bumpversion pre``                                 ``1.0.2-beta.1+5134``
``bumpversion pre``                                 ``1.0.2-rc.1+5134``
``bumpversion pre``                                 ``1.0.2+5134``
==================================================  =======================


11. Search and Replace
----------------------

In the previous examples, versions are identified by their values. It is versatile but it may confound texts with
version numbers. With ``search`` and ``replace``, you can be more specific. For example::

    [bumpversion]
    current_version: 1.2.0

    [bumpversion:file:VERSION]
    search = VERSION = {current_version}
    replace = VERSION = {new_version}

Search and replace values can have multiple lines. It can be useful for CHANGELOG files::

    [bumpversion]
    current_version: 1.2.0

    [bumpversion:file:CHANGELOG.rst]
      search =
        Unreleased
        ----------
      replace =
        Unreleased
        ----------

        Version v{new_version} ({now:%Y-%m-%d})
        ---------------------------

12. Context
-----------

```erialize``, ``search`` and ``replace`` can use values from the current context. This context contains the different
parts of the version (as parsed by ``parse`` regular expression), environment variables (with a ``$`` before their
names) and two time values: ``now`` (that corresponds to ``datetime.now()``) and ``utcnow`` (that corresponds to
``datetime.utcnow()``).

For example, if the environ variable ``USER`` is defined, it can be part of the version number::

    [bumpversion]
    current_version: 1.2.0

    [bumpversion:file:VERSION.txt]
    serialize =
        {major}.{minor}.{patch}+{$USER}

13. Build date
--------------

``now`` and ``utcnow`` can be used to change the build date with the version number. For example, if you have the
following configuration file:

``.bumpconfig.cfg``::

    [bumpversion]
    current_version = 2.1.0 2017-12-04
    serialize = {major}.{minor}.{patch} {now:%Y-%m-%d}
    parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\s(?P<date>\d{4}-\d{2}-\d{2})

    [bumpversion:file:VERSION.h:0]
    serialize = {major}.{minor}.{patch}

    [bumpversion:file:VERSION.h:1]
    serialize = {date}

The following file:

``VERSION.h``::

    #define BUILD_VERSION 2.1.0
    #define BUILD_DATE 2017-12-04 12:00
    #define BUILD_DESCRIPTION 2.1.0 (2017-12-04 12:00)

is transformed into::

    #define BUILD_VERSION 2.2.0
    #define BUILD_DATE 2018-02-09 12:00
    #define BUILD_DESCRIPTION 2.2.0 (2018-02-09 12:00)

by the command: ``bumpversion minor``.

14. Commit and Tag - Command line
---------------------------------

**ADVbumpversion** is able to interact with source controls such as **Git** and **Mercurial**. It can create
automatically tags and commits. The name of the tags and the message of the commits are configurable.
it is also possible to sign tags.

The following command::

    bumèversion patch --current-version 47.1.1 --commit VERSION

creates a commit with the message ``Bump version: 47.1.1 -> 47.1.2``.

15. Commit and Tag - Configuration File
---------------------------------------

The following configuration::

    [bumpversion]
    current_version = 47.1.1
    commit = True
    tag = True

    [bumpversion:file:VERSION]

and the command::

    bumpversion patch

creates a commit with the message ``Bump version: 48.1.1 -> 48.1.2`` and a tag named ``v48.1.2``.

16. Customize tag name
----------------------

Tag name can be customized with ``tag_name``::

    [bumpversion]
    current_version = 47.1.1
    commit = True
    tag = True
    tag_name: from-{current_version}-to-{new_version}

    [bumpversion:file:VERSION]

The tag will be named ``from-47.1.1-to-47.1.2``.

17. Annotated tags
------------------

Annotated tags are created with ``--tag-message`` in commands such as::

    bumpversion patch --current-version 42.5.1 --commit --tag --tag-message 'test {new_version}-tag' VERSION

18. Signed tags
---------------

In a similar way, it is possible to sign tags::

    [bumpversion]
    current_version = 47.1.1
    commit = True
    tag = True
    tag_name: from-{current_version}-to-{new_version}
    sign_tags = True

    [bumpversion:file:VERSION]

19. Customize commit messages
-----------------------------

In a similar way, it is possible to csutomize commit messages::

    bumpversion --message '[{now:%Y-%m-%d}] Jenkins Build {$BUILD_NUMBER}: {new_version}' patch

