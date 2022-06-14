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
