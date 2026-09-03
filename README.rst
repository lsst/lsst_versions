lsst_versions
=============

This package is used to calculate a version dynamically from a Git repository when it is being built by ``pip``.
It is not needed for EUPS-only packages, and the calculated package version will be ``pip``-compatible and thus differ from that produced by EUPS's ``pkgautoversion``.
It avoids the need to hard-code and continually update a version string.
It assumes the use of LSST DM release and tagging practices.

Development
-----------

This package uses `uv <https://docs.astral.sh/uv/>`_ to manage the library versions used for local development and CI.
The versions are recorded in ``uv.lock`` and the tests are run in that locked environment:

.. code-block:: bash

    uv run pytest
    uv run mypy

Documentation is built from the ``doc`` dependency group, which requires Python 3.12 or later:

.. code-block:: bash

    uv run --group doc sphinx-build -b html doc doc/_build/html

Run the following to refresh ``uv.lock`` with the latest available versions of all libraries:

.. code-block:: bash

    uv lock --upgrade
