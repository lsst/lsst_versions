lsst_versions 1.7.0 2026-09-09
==============================

New Features
------------

- The version calculation can now be run with ``python -m lsst_versions`` as well as through the ``lsst-version`` command. (`DM-55986 <https://jira.lsstcorp.org/browse/DM-55986>`_)


API Changes
-----------

- ``lsst_versions.__version__`` is now read from the installed package metadata using ``importlib.metadata`` rather than from a generated ``__version__.py`` file.
  It reports ``0.0.0`` if the package has not been installed.

  ``GitPython`` is now an unconditional requirement of this package rather than an optional import.
  The ``RuntimeError`` that was raised when it was missing has been removed.

  The public functions now accept any ``os.PathLike`` for the directory or repository they are given, rather than only a `str`. (`DM-55986 <https://jira.lsstcorp.org/browse/DM-55986>`_)


Bug Fixes
---------

- A version of ``0+unknown`` is now reported when no version can be determined from Git or from package metadata, instead of raising an error.
  This allows a package to be built from a checkout with no Git history, such as a shallow clone. (`DM-55985 <https://jira.lsstcorp.org/browse/DM-55985>`_)
- The Hatch version source plugin now calculates the version from the project root supplied by Hatch rather than from the current working directory.
  Previously a Hatch build started from a different directory could report the wrong version.

  The build system plugins no longer emit their own debug logging into the output of the package being built.
  A debug message was previously issued for every tag in the repository, which buried the output of tools that enable debug logging during a build, such as ``uv pip install -v``.
  The informational message reporting the chosen version is retained.
  Set the ``LSST_VERSIONS_LOG_LEVEL`` environment variable to restore the debug messages.

  Repositories that do not use the LSST ``w.YYYY.WW`` weekly tagging convention are now versioned by semantic versioning.
  A tree built 22 commits after the ``1.6.0`` tag is therefore ``1.6.1.dev22``, which sorts above ``1.6.0`` and below ``1.6.1``.
  Previously such a repository combined the major version of its newest release with a commit count measured from the root of the repository, reporting ``1.0.28`` for that tree. (`DM-55986 <https://jira.lsstcorp.org/browse/DM-55986>`_)


Miscellaneous Changes of Minor Interest
---------------------------------------

- All build configuration has been consolidated into ``pyproject.toml``.
  The package is now built with an in-tree PEP 517 build backend.
  Library versions for development and CI are now managed with ``uv`` and recorded in ``uv.lock``.
  The minimum supported ``setuptools`` version is now 77, matching the build requirements.
  (`DM-55986 <https://jira.lsstcorp.org/browse/DM-55986>`_)


An API Removal or Deprecation
-----------------------------

- The minimum supported Python version is now 3.11.
  This allows the standard library ``tomllib`` module to be used and the ``tomli`` dependency has been dropped.
  The ``dev`` and ``typing`` extras have been replaced by the ``dev`` dependency group, and ``doc/requirements.txt`` by the ``doc`` dependency group. (`DM-55986 <https://jira.lsstcorp.org/browse/DM-55986>`_)


lsst-versions 1.6.0 2025-01-21
==============================

New Features
------------

- Adds support for [Hatchling](https://hatch.pypa.io/latest/config/build/#build-system).
  Implements a Hatch "version source plugin" interface. (`DM-48515 <https://jira.lsstcorp.org/browse/DM-48515>`_)


Miscellaneous Changes of Minor Interest
---------------------------------------

- Refreshes development and build environment specifications.

- Removes retired ``pytest-openfiles`` testing dependency.

- Uses secure ``tarfile`` data filter when supported by Python.

lsst-versions 1.5.0 2023-11-29
==============================

Package has been verified to work with python 3.12.

lsst-versions 1.4.0 2023-02-08
==============================

New Features
------------

- The calculation of the developer version has been modified.
  Previously alpha releases were constructed from weekly release tags.
  This approach, 26.0.0a20230500, resulted in confusion in PyPI installs once a formal release was made.
  To simplify installations with ``pip`` weekly developer release versions are now of the form 25.2023.500 -- the weekly is encoded in the minor and patchlevel parts of the version and these are now releases derived from the release currently being worked (and not alphas towards the next release).

lsst-versions 1.3.0 2022-07-10
==============================

API Changes
-----------

- Added a new function ``get_lsst_version``.
  This allows to get a version string of a GitHub or metadata directory.

lsst-versions 1.2.0 2022-06-27
==============================

New Features
------------

- Now falls back to looking at ``PKG-INFO`` file if no git version can be determined.
  This allows a source distribution to be built.
- The ``find_lsst_version`` API can now run without any parameters.

lsst-versions 1.1.0 2022-06-14
==============================

New Features
------------

- Added a new ``lsst-version`` command line that can be used to determine the version of a package.
  This command can also be used to create a version file in the package using the configuration found in a ``pyproject.toml`` file. (`DM-35064 <https://jira.lsstcorp.org/browse/DM-35064>`_)


API Changes
-----------

- Renamed the ``find_dev_lsst_version`` function to ``find_lsst_version`` to reflect the fact that it does more than finding developer versions. (`DM-35064 <https://jira.lsstcorp.org/browse/DM-35064>`_)


Miscellaneous Changes of Minor Interest
---------------------------------------

- * Replaced some debug prints with logging.
  * Significantly improved the test coverage. (`DM-35064 <https://jira.lsstcorp.org/browse/DM-35064>`_)


lsst-versions 1.0.0 2022-04-18
==============================

New Features
------------

- Initial release of ``lsst-versions`` package.
  This package can be used as a ``setuptools`` entry point to determine the version of a package from the Git repository. (`DM-32408 <https://jira.lsstcorp.org/browse/DM-32408>`_)
