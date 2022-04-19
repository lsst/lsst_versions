.. py:currentmodule:: lsst_versions

.. _lsst_versions:

#############
lsst_versions
#############

This package is used to calculate a version dynamically from a Git repository when it is being built by ``pip``.
It is not needed for EUPS-only packages, and the calculated package version will be ``pip``-compatible and thus differ from that produced by EUPS's ``pkgautoversion``.
It avoids the need to hard-code and continually update a version string.
It assumes the use of LSST DM release and tagging practices.

.. _lsst_versions-changes:

Changes
=======

.. toctree::
   :maxdepth: 1

   CHANGES.rst

.. _lsst_versions-contributing:

.. _lsst_versions-using:

Using lsst_versions
===================

.. toctree::
   :maxdepth: 1

   configuring.rst

Contributing
============

``lsst_versions`` is developed at https://github.com/lsst/lsst_versions.
You can find Jira issues for this module under the `lsst_versions <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20component%20%3D%20lsst_versions>`_ component.

.. _lsst_versions-pyapi:

Python API reference
====================

.. automodapi:: lsst_versions
   :no-main-docstr:
