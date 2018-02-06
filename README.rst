.. start-badges

|travis| |requires| |wheel| |supported-versions| |supported-implementations|

.. |travis| image:: https://travis-ci.org/andrivet/advbumpversion.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/andrivet/advbumpversion

.. |requires| image:: https://requires.io/github/andrivet/advbumpversion/requirements.svg?branch=master
    :target: https://requires.io/github/andrivet/advbumpversion/requirements/?branch=master
    :alt: Requirements Status

.. |wheel| image:: https://img.shields.io/pypi/wheel/advbumpversion.svg?style=flat
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/advbumpversion

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/advbumpversion.svg?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/advbumpversion

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/advbumpversion.svg?style=flat
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/advbumpversion

.. end-badges

==============
ADVbumpversion
==============

Fork
====

This is a fork (**ADVbumpversion**) of a fork (**bump2version**).

The excellent original project that can be found here: https://github.com/peritus/bumpversion.
Unfortunately it seems like development has been stuck for some time and no activity has been seen from the
author.

Christian Verkerk has made some Pull Request merges and this project (renamed **bump2version**) can be found here: https://github.com/c4urself/bump2version.

I have merged other Push Requests, in particular the ability to have more than one rule for a file, in a new project **ADVbumpversion**.
Look at ``CHANGELOG.rst`` to see all the changes.

Note: For compatibility, this project declares ``advbumpversion``, ``bump2version`` and ``bumpversion``. The remaining of this document uses ``bumpversion`` in command-line examples.

Introduction
============

Version-bump your software with a single command!

A small command line tool to simplify releasing software by updating all
version strings in your source code by the correct increment. Also creates
commits and tags:

- version formats are highly configurable
- works without any VCS, but happily reads tag information from and writes
  commits and tags to Git and Mercurial if available
- just handles text files, so it's not specific to any programming language


Installation
============

You can download and install the latest version of this software from the Python package index (PyPI) as follows::

    pip install --upgrade advbumpversion


Usage
=====

There are two modes of operation: On the command line for single-file operation
and using a `configuration file <#configuration>`_ for more complex multi-file
operations.

::

    bumpversion [options] part [file]


``part`` (required)
  The part of the version to increase, e.g. ``minor``.

  Valid values include those given in the ``--serialize`` / ``--parse`` option.

  Example `bumping 0.5.1 to 0.6.0`::

     bumpversion --current-version 0.5.1 minor src/VERSION

``[file]``
  **default: none** (optional)

  The file that will be modified.

  If not given, the list of ``[bumpversion:file:…]`` sections from the
  configuration file will be used. If no files are mentioned on the
  configuration file either, are no files will be modified.

  Example `bumping 1.1.9 to 2.0.0`::

     bumpversion --current-version 1.1.9 major setup.py

Configuration
+++++++++++++

All options can optionally be specified in a config file called
``.bumpversion.cfg`` so that once you know how ``bumpversion`` needs to be
configured for one particular software package, you can run it without
specifying options later. You should add that file to VCS so others can also
bump versions.

Options on the command line take precedence over those from the config file,
which take precedence over those derived from the environment and then from the
defaults.

Example ``.bumpversion.cfg``::

  [bumpversion]
  current_version = 0.2.9
  commit = True
  tag = True

  [bumpversion:file:setup.py]

If no ``.bumpversion.cfg`` exists, ``bumpversion`` will also look into
``setup.cfg`` for configuration.

Global configuration
--------------------

General configuration is grouped in a ``[bumpversion]`` section.

``current_version =``
  **no default value** (required)

  The current version of the software package before bumping.

  Also available as ``--current-version`` (e.g. ``bumpversion --current-version 0.5.1 patch setup.py``)

``new_version =``
  **no default value** (optional)

  The version of the software package after the increment. If not given will be
  automatically determined.

  Also available as ``--new-version`` (e.g. to go from 0.5.1 directly to
  0.6.1: ``bumpversion --current-version 0.5.1 --new-version 0.6.1 patch
  setup.py``).

``tag = (True | False)``
  **default:** False (`Don't create a tag`)

  Whether to create a tag, that is the new version, prefixed with the character
  "``v``". If you are using git, don't forget to ``git-push`` with the
  ``--tags`` flag.

  Also available on the command line as ``(--tag | --no-tag)``.

``sign_tags = (True | False)``
  **default:** False (`Don't sign tags`)

  Whether to sign tags.

  Also available on the command line as ``(--sign-tags | --no-sign-tags)``.

``tag_name =``
  **default:** ``v{new_version}``

  The name of the tag that will be created. Only valid when using ``--tag`` / ``tag = True``.

  This is templated using the `Python Format String Syntax
  <http://docs.python.org/2/library/string.html#format-string-syntax>`_.
  Available in the template context are ``current_version`` and ``new_version``
  as well as all environment variables (prefixed with ``$``). You can also use
  the variables ``now`` or ``utcnow`` to get a current timestamp. Both accept
  datetime formatting (when used like as in ``{now:%d.%m.%Y}``).

  Also available as ``--tag-name`` (e.g. ``bumpversion --message 'Jenkins Build
  {$BUILD_NUMBER}: {new_version}' patch``).

``commit = (True | False)``
  **default:** ``False`` (`Don't create a commit`)

  Whether to create a commit using git or Mercurial.

  Also available as ``(--commit | --no-commit)``.

``message =``
  **default:** ``Bump version: {current_version} -> {new_version}``

  The commit message to use when creating a commit. Only valid when using ``--commit`` / ``commit = True``.

  This is templated using the `Python Format String Syntax
  <http://docs.python.org/2/library/string.html#format-string-syntax>`_.
  Available in the template context are ``current_version`` and ``new_version``
  as well as all environment variables (prefixed with ``$``). You can also use
  the variables ``now`` or ``utcnow`` to get a current timestamp. Both accept
  datetime formatting (when used like as in ``{now:%d.%m.%Y}``).

  Also available as ``--message`` (e.g.: ``bumpversion --message
  '[{now:%Y-%m-%d}] Jenkins Build {$BUILD_NUMBER}: {new_version}' patch``)


Part specific configuration
---------------------------

A version string consists of one or more parts, e.g. the version ``1.0.2``
has three parts, separated by a dot (``.``) character. In the default
configuration these parts are named `major`, `minor`, `patch`, however you can
customize that using the ``parse``/``serialize`` option.

By default all parts considered numeric, that is their initial value is ``0``
and they are increased as integers. Also, the value ``0`` is considered to be
optional if it's not needed for serialization, i.e. the version ``1.4.0`` is
equal to ``1.4`` if ``{major}.{minor}`` is given as a ``serialize`` value.

For advanced versioning schemes, non-numeric parts may be desirable (e.g. to
identify `alpha or beta versions
<http://en.wikipedia.org/wiki/Software_release_life_cycle#Stages_of_development>`_,
to indicate the stage of development, the flavor of the software package or
a release name). To do so, you can use a ``[bumpversion:part:…]`` section
containing the part's name (e.g. a part named ``release_name`` is configured in
a section called ``[bumpversion:part:release_name]``.

The following options are valid inside a part configuration:

``values =``
  **default**: numeric (i.e. ``0``, ``1``, ``2``, …)

  Explicit list of all values that will be iterated when bumping that specific
  part.

  Example::

    [bumpversion:part:release_name]
    values =
      witty-warthog
      ridiculous-rat
      marvelous-mantis

``optional_value =``
  **default**: The first entry in ``values =``.

  If the value of the part matches this value it is considered optional, i.e.
  it's representation in a ``--serialize`` possibility is not required.

  Example::

    [bumpversion]
    current_version = 1.alpha
    parse = (?P<num>\d+)(\.(?P<release>.*))?
    serialize =
      {num}.{release}
      {num}

    [bumpversion:part:release]
    optional_value = gamma
    values =
      alpha
      beta
      gamma

  Here, ``bumpversion release`` would bump ``1.alpha`` to ``1.beta``. Executing
  ``bumpversion release`` again would bump ``1.beta`` to ``1``, because
  `release` being ``gamma`` is configured optional.

``first_value =``
  **default**: The first entry in ``values =``.

  When the part is reset, the value will be set to the value specified here.

File specific configuration
---------------------------

``[bumpversion:file:…:…]``

**Note**: If you want to specify different options (``parse``, ...) for the same file, you can have several sections for the same file.
To distinguish these sections, append ``:`` and an identifier (its value has no importance) after the file name.

``parse =``
  **default:** ``(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)``

  Regular expression (using `Python regular expression syntax
  <http://docs.python.org/2/library/re.html#regular-expression-syntax>`_) on
  how to find and parse the version string.

  Is required to parse all strings produced by ``serialize =``. Named matching
  groups ("``(?P<name>...)``") provide values to as the ``part`` argument.

  Also available as ``--parse``

``serialize =``
  **default:** ``{major}.{minor}.{patch}``

  Template specifying how to serialize the version parts back to a version
  string.

  This is templated using the `Python Format String Syntax
  <http://docs.python.org/2/library/string.html#format-string-syntax>`_.
  Available in the template context are parsed values of the named groups
  specified in ``parse =`` as well as all environment variables (prefixed with
  ``$``).

  Can be specified multiple times, bumpversion will try the serialization
  formats beginning with the first and choose the last one where all values can
  be represented like this::

    serialize =
      {major}.{minor}
      {major}

  Given the example above, the new version *1.9* it will be serialized as
  ``1.9``, but the version *2.0* will be serialized as ``2``.

  Also available as ``--serialize``. Multiple values on the command line are
  given like ``--serialize {major}.{minor} --serialize {major}``

``search =``
  **default:** ``{current_version}``

  Template string how to search for the string to be replaced in the file.
  Useful if the remotest possibility exists that the current version number
  might be multiple times in the file and you mean to only bump one of the
  occurrences. Can be multiple lines, templated using `Python Format String Syntax
  <http://docs.python.org/2/library/string.html#format-string-syntax>`_.

``replace =``
  **default:** ``{new_version}``

  Template to create the string that will replace the current version number in
  the file.

  Given this ``requirements.txt``::

    Django>=1.5.6,<1.6
    MyProject==1.5.6

  using this ``.bumpversion.cfg`` will ensure only the line containing
  ``MyProject`` will be changed::

    [bumpversion]
    current_version = 1.5.6

    [bumpversion:file:requirements.txt]
    search = MyProject=={current_version}
    replace = MyProject=={new_version}

  Can be multiple lines, templated using `Python Format String Syntax
  <http://docs.python.org/2/library/string.html#format-string-syntax>`_.

Options
=======

Most of the configuration values above can also be given as an option.
Additionally, the following options are available:

``--dry-run, -n``
  Don't touch any files, just pretend. Best used with ``--verbose``.

``--allow-dirty``
  Normally, bumpversion will abort if the working directory is dirty to protect
  yourself from releasing unversioned files and/or overwriting unsaved changes.
  Use this option to override this check.

``--verbose``
  Print useful information to stderr

``--list``
  List machine readable information to stdout for consumption by other
  programs.

  Example output::

    current_version=0.0.18
    new_version=0.0.19

``-h, --help``
  Print help and exit

Using bumpversion in a script
=============================

If you need to use the version generated by bumpversion in a script you can make use of
the `--list` option, combined with `grep` and `sed`.

Say for example that you are using git-flow to manage your project and want to automatically
create a release. When you issue `git flow release start` you already need to know the
new version, before applying the change.

The standard way to get it in a bash script is

    bumpversion --dry-run --list <part> | grep <field name> | sed -r s,"^.*=",,

where <part> is as usual the part of the version number you are updating. You need to specify
`--dry-run` to avoid bumpversion actually bumping the version number.

For example, if you are updating the minor number and looking for the new version number this becomes

    bumpversion --dry-run --list minor | grep new_version | sed -r s,"^.*=",,

Development
===========

Development of this happens on GitHub, patches including tests, documentation
are very welcome, as well as bug reports! Also please open an issue if this
tool does not support every aspect of bumping versions in your development
workflow, as it is intended to be very versatile.

How to release bumpversion itself
+++++++++++++++++++++++++++++++++

Execute the following commands::

    git checkout master
    git pull
    make test
    bumpversion release
    python setup.py sdist bdist_wheel upload
    bumpversion --no-tag patch
    git push origin master --tags

License
=======

**ADVbumpversion** is licensed under the MIT License - see the LICENSE.rst file for details
