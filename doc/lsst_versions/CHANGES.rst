lsst-versions 1.6.0 2025-01-21
==============================

New Features
------------

- Adds support for [Hatchling](https://hatch.pypa.io/latest/config/build/#build-system).
  Implements a Hatch "version source plugin" interface. (`DM-48515 <https://jira.lsstcorp.org/browse/DM-48515>`_)


Miscellaneous Changes of Minor Interest
---------------------------------------

- Refreshes development and build environment specifications.

- Removes retired `pytest-openfiles` testing dependency.

- Uses secure `tarfile` data filter when supported by Python.

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
