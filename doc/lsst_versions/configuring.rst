Modifying the pyproject.toml file
=================================

.. note::

    These instructions assume that a project is configured using ``pyproject.toml`` and ``setuptools``.
    If your project does not have such a file but instead uses ``setup.py`` and/or ``setup.cfg``, then creating a TOML file specifically for these configurations will work.

Buid-time version determination can be enabled by adding a few lines to the ``pyproject.toml`` configuration file for the package.

At the top add a build system:

.. code-block:: toml

    [build-system]
    requires = ["setuptools", "lsst_versions"]
    build-backend = "setuptools.build_meta"

The ``setuptools`` package is implied by using ``lsst_versions`` but it does not hurt to add it explicitly, especially if your package does use ``setuptools``.
Then in a tool section describe where the version information should be written:

.. code-block:: toml

    [tool.lsst_versions]
    write_to = "python/lsst/mypackage/version.py"

It is expected that the package ``__init__.py`` will import this generated file to publish the version.

These minor changes should be sufficient for ``pip install .`` to build the package with the correct version.

Using with Hatchling
--------------------

When building a project that employs the Hatchling build backend, ``lsst_versions`` can be used as a Version Source plugin.

In the project's ``pyproject.toml``, update the build system specification:

.. code-block:: toml

    [build-system]
    requires = ["hatchling", "lsst-versions"]
    build-backend = "hatchling.build"

    [tool.hatch.version]
    source = "lsst"

Checkouts with no Git history
=============================

Determining a version requires the Git history of the package.
Some tools, such as Dependabot, work from a checkout that does not have one.
Rather than failing the build, a version of ``0+unknown`` is reported when no version can be found from Git or from package metadata.

``0+unknown`` is a PEP 440 local version.
It can be parsed by packaging tools and sorts below every real release, but public index servers such as PyPI refuse to accept local versions, so a package built this way can never be released by accident.
A dependency such as ``lsst-daf-butler>=28`` will not be satisfied by it either, so the placeholder cannot pass silently.

The ``lsst-version`` command reports the same string.

Debugging
=========

The version calculation issues a debug message for every tag in the repository.
These messages are suppressed while another package is being built so that they do not obscure the output of build tools that enable debug logging, such as ``uv pip install -v``.
The informational message reporting the chosen version is still issued.
Set the ``LSST_VERSIONS_LOG_LEVEL`` environment variable to see the debug messages:

.. code-block:: bash

    LSST_VERSIONS_LOG_LEVEL=DEBUG pip install .

The ``lsst-version`` command is unaffected and takes a ``--log-level`` option instead.

GitHub Actions
==============

When running inside a GitHub Action it will be necessarily to clone the entire repository for this version determination to work.

.. code-block:: yaml

      - uses: actions/checkout@v2
        with:
          # Need to clone everything.
          fetch-depth: 0
