"""Module implementing a version source plugin for the hatch build system."""

from hatchling.plugin import hookimpl
from hatchling.version.source.plugin.interface import VersionSourceInterface


@hookimpl
def hatch_register_version_source() -> type["LsstVersionSource"]:
    """Register a Hatch Version Source hook."""
    return LsstVersionSource


class LsstVersionSource(VersionSourceInterface):
    """Implement a Hatch Version Source Interface."""

    PLUGIN_NAME = "lsst"

    def get_version_data(self) -> dict:
        """Return the project version data.

        Notes
        -----
        Debug logging from this package is suppressed so that it does not
        obscure the output of the build that triggered it. Set the
        ``LSST_VERSIONS_LOG_LEVEL`` environment variable to see it.
        """
        from ._versions import _build_logging, find_lsst_version

        with _build_logging():
            return dict(version=find_lsst_version(self.root))
