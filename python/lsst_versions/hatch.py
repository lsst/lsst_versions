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
        """Return the project version data."""
        from ._versions import find_lsst_version

        return dict(version=find_lsst_version())
