"""Ingestion package for raw NWP and observation data sources."""

from importlib import import_module
from typing import Any

from scientific.ingestion.grib import (
    GribMessageMetadata,
    GribQCReport,
    generate_manifest,
    group_messages,
    parse_grib_file,
    parse_grib_message,
    perform_qc,
    read_grib_file,
)
from scientific.ingestion.mera import (
    MeraObservation,
    MeraObservationCollection,
    MeraQCReport,
    read_mera_file,
    read_mera_observations,
)
from scientific.ingestion.imd import (
    IMD_DAILY_MERGED_SATELLITE_GAUGE_PRODUCT,
    ImdDailyObservation,
    ImdDailyObservationWindow,
    imd_daily_merged_satellite_gauge_window,
    read_imd_daily_file,
)
__all__ = [
    "GribMessageMetadata",
    "GribQCReport",
    "generate_manifest",
    "group_messages",
    "parse_grib_file",
    "parse_grib_message",
    "perform_qc",
    "read_grib_file",
    "MeraObservation",
    "MeraObservationCollection",
    "MeraQCReport",
    "read_mera_file",
    "read_mera_observations",
    "ImdDailyObservation",
    "ImdDailyObservationWindow",
    "IMD_DAILY_MERGED_SATELLITE_GAUGE_PRODUCT",
    "imd_daily_merged_satellite_gauge_window",
    "read_imd_daily_file",
    "NCMRWF_TIGGE_ORIGIN",
    "TIGGE_DATASET",
    "TiggeAcquisitionResult",
    "TiggeCredentials",
    "TiggeRequest",
    "acquire_tigge_forecast",
]


_TIGGE_EXPORTS = {
    "NCMRWF_TIGGE_ORIGIN",
    "TIGGE_DATASET",
    "TiggeAcquisitionResult",
    "TiggeCredentials",
    "TiggeRequest",
    "acquire_tigge_forecast",
}


def __getattr__(name: str) -> Any:
    """Lazily preserve TIGGE public exports without preloading its CLI module."""
    if name in _TIGGE_EXPORTS:
        module = import_module("scientific.ingestion.tigge")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
