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

GitHub Actions
==============

When running inside a GitHub Action it will be necessarily to clone the entire repository for this version determination to work.

.. code-block:: yaml

      - uses: actions/checkout@v2
        with:
          # Need to clone everything.
          fetch-depth: 0
