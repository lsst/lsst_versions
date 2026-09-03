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
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

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

requires_hatchling = pytest.mark.skipif(hatchling is None, reason="hatchling package is not installed.")


def levels(caplog: pytest.LogCaptureFixture) -> set[str]:
    """Return the levels this package logged at, ignoring other loggers."""
    return {record.levelname for record in caplog.records if record.name == "lsst_versions"}


@requires_hatchling
def test_hatch_register() -> None:
    """The plugin hook returns the version source class."""
    from lsst_versions.hatch import LsstVersionSource, hatch_register_version_source

    assert hatch_register_version_source() is LsstVersionSource
    assert LsstVersionSource.PLUGIN_NAME == "lsst"


@requires_hatchling
def test_hatch_get_version_data(gitdir: Path) -> None:
    """The plugin uses the project root supplied by Hatch."""
    from lsst_versions.hatch import LsstVersionSource

    # The plugin must use the project root given to it by Hatch rather
    # than the current working directory.
    source = LsstVersionSource(gitdir, {})
    assert source.get_version_data() == {"version": find_lsst_version(gitdir)}


@requires_hatchling
def test_hatch_logging_is_quiet(gitdir: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Per-tag debug messages stay out of the build output."""
    from lsst_versions.hatch import LsstVersionSource

    # The per-tag debug messages must not reach the build output but
    # the message reporting the chosen version is still wanted.
    source = LsstVersionSource(gitdir, {})
    with caplog.at_level(logging.DEBUG, logger="lsst_versions"):
        source.get_version_data()
    assert "DEBUG" not in levels(caplog)
    assert "INFO" in levels(caplog)


def test_read_missing(tmp_path: Path) -> None:
    """No version file at all reads as no version."""
    assert _read_written_version(tmp_path) is None


def test_read_empty(tmp_path: Path) -> None:
    """An empty version file reads as no version."""
    _version_path(tmp_path).write_text("\n")
    assert _read_written_version(tmp_path) is None


def test_read_version(tmp_path: Path) -> None:
    """A written version is read back without its trailing newline."""
    _version_path(tmp_path).write_text("1.2.3\n")
    assert _read_written_version(tmp_path) == "1.2.3"


def test_write_from_git(gitdir: Path) -> None:
    """The version written for a repository is the one Git implies."""
    # The version file is written into the root of the tree being
    # versioned, so the test repository gains one for the duration.
    _write_version_file(gitdir)
    try:
        assert _read_written_version(gitdir) == find_lsst_version(gitdir)
    finally:
        _version_path(gitdir).unlink()


def test_write_reuses_existing(tmp_path: Path) -> None:
    """An existing version file is retained when nothing else is available."""
    # No Git repository and no package metadata, so the version already
    # in the file must be retained. This is the source distribution case.
    _version_path(tmp_path).write_text("9.9.9\n")
    _write_version_file(tmp_path)
    assert _read_written_version(tmp_path) == "9.9.9"


def test_write_falls_back_to_default(tmp_path: Path) -> None:
    """With nothing to go on at all the default version is written."""
    with pytest.warns(UserWarning):
        _write_version_file(tmp_path)
    assert _read_written_version(tmp_path) == _DEFAULT_VERSION


def fake_distribution() -> SimpleNamespace:
    """Stand in for the setuptools distribution being built."""
    return SimpleNamespace(metadata=SimpleNamespace(version=None))


@pytest.fixture
def in_test_repository(gitdir: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Run inside the test repository with no log level override set."""
    monkeypatch.delenv(_LOG_LEVEL_ENV, raising=False)
    monkeypatch.chdir(gitdir)
    yield gitdir
    (gitdir / "version_test.py").unlink(missing_ok=True)


def test_setuptools_logging_is_quiet(in_test_repository: Path, caplog: pytest.LogCaptureFixture) -> None:
    """The setuptools hook does not log a message for every tag."""
    # A debug message for every tag would otherwise be emitted into the
    # output of the build that triggered this.
    dist = fake_distribution()
    with caplog.at_level(logging.DEBUG, logger="lsst_versions"):
        infer_version_for_setuptools(dist)
    assert "DEBUG" not in levels(caplog)
    assert dist.metadata.version == find_lsst_version(in_test_repository)


def test_setuptools_logging_can_be_restored(
    in_test_repository: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The environment variable restores the suppressed debug messages."""
    monkeypatch.setenv(_LOG_LEVEL_ENV, "DEBUG")
    with caplog.at_level(logging.DEBUG, logger="lsst_versions"):
        infer_version_for_setuptools(fake_distribution())
    assert "DEBUG" in levels(caplog)


@pytest.mark.parametrize(
    ("hook", "delegate", "args"),
    (
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
    ),
)
def test_hooks_write_version_and_delegate(hook: str, delegate: str, args: tuple) -> None:
    """Every PEP 517 hook writes the version and forwards its arguments."""
    with (
        patch.object(_build_backend, "_write_version_file") as write_version,
        patch.object(_build_backend, delegate, return_value="result") as delegated,
    ):
        result = getattr(_build_backend, hook)(*args)

    assert result == "result"
    write_version.assert_called_once_with()
    delegated.assert_called_once_with(*args)
