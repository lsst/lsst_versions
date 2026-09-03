# This file is part of lsst_versions.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# Use of this source code is governed by a 3-clause BSD-style
# license that can be found in the LICENSE file.

"""Tests of the build system plugins that consume the version calculation."""

import logging
import os
import tempfile
import unittest
import unittest.mock
from types import SimpleNamespace
from unittest.mock import patch

# Hatchling is only in the dev dependency group, so tests run from a plain
# environment can still exercise everything else.
try:
    import hatchling  # noqa: F401
except ImportError:
    hatchling = None

from lsst_versions import _build_backend, find_lsst_version, infer_version_for_setuptools
from lsst_versions._build_backend import (
    _DEFAULT_VERSION,
    _read_written_version,
    _version_path,
    _write_version_file,
)
from lsst_versions._versions import _LOG_LEVEL_ENV
from test_versions import GITDIR, setup_module  # noqa: F401


@unittest.skipIf(hatchling is None, "hatchling package is not installed.")
class HatchVersionSourceTestCase(unittest.TestCase):
    """Test the Hatch version source plugin."""

    def test_register(self):
        from lsst_versions.hatch import LsstVersionSource, hatch_register_version_source

        self.assertIs(hatch_register_version_source(), LsstVersionSource)
        self.assertEqual(LsstVersionSource.PLUGIN_NAME, "lsst")

    def test_get_version_data(self):
        from lsst_versions.hatch import LsstVersionSource

        # The plugin must use the project root given to it by Hatch rather
        # than the current working directory.
        source = LsstVersionSource(GITDIR, {})
        self.assertEqual(source.get_version_data(), {"version": find_lsst_version(GITDIR)})

    def test_logging_is_quiet(self):
        from lsst_versions.hatch import LsstVersionSource

        # The per-tag debug messages must not reach the build output but
        # the message reporting the chosen version is still wanted.
        source = LsstVersionSource(GITDIR, {})
        with self.assertLogs("lsst_versions", level=logging.DEBUG) as cm:
            source.get_version_data()
        self.assertNotIn("DEBUG", [record.levelname for record in cm.records])
        self.assertIn("INFO", [record.levelname for record in cm.records])


class BuildBackendTestCase(unittest.TestCase):
    """Test the version file handling used by the in-tree build backend."""

    def setUp(self):
        self.tmpdir = self.enterContext(tempfile.TemporaryDirectory())

    def test_read_missing(self):
        self.assertIsNone(_read_written_version(self.tmpdir))

    def test_read_empty(self):
        with open(_version_path(self.tmpdir), "w") as fh:
            fh.write("\n")
        self.assertIsNone(_read_written_version(self.tmpdir))

    def test_read_version(self):
        with open(_version_path(self.tmpdir), "w") as fh:
            print("1.2.3", file=fh)
        self.assertEqual(_read_written_version(self.tmpdir), "1.2.3")

    def test_write_from_git(self):
        # The version file is written into the root of the tree being
        # versioned, so the test repository gains one for the duration.
        _write_version_file(GITDIR)
        self.addCleanup(os.unlink, _version_path(GITDIR))
        self.assertEqual(_read_written_version(GITDIR), find_lsst_version(GITDIR))

    def test_write_reuses_existing(self):
        # No Git repository and no package metadata, so the version already
        # in the file must be retained. This is the source distribution case.
        with open(_version_path(self.tmpdir), "w") as fh:
            print("9.9.9", file=fh)
        _write_version_file(self.tmpdir)
        self.assertEqual(_read_written_version(self.tmpdir), "9.9.9")

    def test_write_falls_back_to_default(self):
        # Nothing to go on at all.
        with self.assertWarns(UserWarning):
            _write_version_file(self.tmpdir)
        self.assertEqual(_read_written_version(self.tmpdir), _DEFAULT_VERSION)


class SetuptoolsHookTestCase(unittest.TestCase):
    """Test the setuptools entry point."""

    @staticmethod
    def fake_distribution() -> SimpleNamespace:
        """Stand in for the setuptools distribution being built."""
        return SimpleNamespace(metadata=SimpleNamespace(version=None))

    def setUp(self):
        self.enterContext(unittest.mock.patch.dict(os.environ))
        os.environ.pop(_LOG_LEVEL_ENV, None)
        cwd = os.getcwd()
        os.chdir(GITDIR)
        self.addCleanup(os.chdir, cwd)
        self.addCleanup(os.unlink, os.path.join(GITDIR, "version_test.py"))

    def test_logging_is_quiet(self):
        # A debug message for every tag would otherwise be emitted into the
        # output of the build that triggered this.
        dist = self.fake_distribution()
        with self.assertLogs("lsst_versions", level=logging.DEBUG) as cm:
            infer_version_for_setuptools(dist)
        self.assertNotIn("DEBUG", [record.levelname for record in cm.records])
        self.assertEqual(dist.metadata.version, find_lsst_version(GITDIR))

    def test_logging_can_be_restored(self):
        os.environ[_LOG_LEVEL_ENV] = "DEBUG"
        with self.assertLogs("lsst_versions", level=logging.DEBUG):
            infer_version_for_setuptools(self.fake_distribution())


class BuildHookTestCase(unittest.TestCase):
    """Test the PEP 517 hooks implemented by the in-tree build backend."""

    # Hook, the setuptools function it must delegate to, and the arguments
    # that must be forwarded unchanged.
    HOOKS = (
        ("build_wheel", "_build_wheel", ("wheeldir", {"setting": "value"}, "metadir")),
        ("build_sdist", "_build_sdist", ("sdistdir", {"setting": "value"})),
        ("build_editable", "_build_editable", ("wheeldir", {"setting": "value"}, "metadir")),
        (
            "prepare_metadata_for_build_wheel",
            "_prepare_metadata_for_build_wheel",
            ("metadir", {"setting": "value"}),
        ),
        (
            "prepare_metadata_for_build_editable",
            "_prepare_metadata_for_build_editable",
            ("metadir", {"setting": "value"}),
        ),
    )

    def test_hooks_write_version_and_delegate(self):
        for hook, delegate, args in self.HOOKS:
            with self.subTest(hook=hook):
                with (
                    patch.object(_build_backend, "_write_version_file") as write_version,
                    patch.object(_build_backend, delegate, return_value="result") as delegated,
                ):
                    result = getattr(_build_backend, hook)(*args)

                self.assertEqual(result, "result")
                write_version.assert_called_once_with()
                delegated.assert_called_once_with(*args)


if __name__ == "__main__":
    unittest.main()
