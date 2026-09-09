"""Runtime configuration for the governed NEMWEB Lakeflow pipeline.

This replaces the reference pipeline's DLT-named configuration helper.  It
only reads bundle-provided Spark configuration and performs no network or file
I/O.  Source mode remains part of every Bronze row so snapshot data cannot be
mistaken for live evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentic_energy.nemweb.contracts import mode_landing_root


@dataclass(frozen=True)
class PipelineConfig:
    """Validated settings injected by ``resources/nemweb.pipeline.yml``."""

    source_mode: str
    landing_path: str
    market_timezone: str
    landing_catalog: str
    landing_schema: str

    @classmethod
    def from_spark(cls, spark_session) -> "PipelineConfig":
        source_mode = spark_session.conf.get("nemweb.source_mode")
        if source_mode not in {"live", "snapshot"}:
            raise ValueError("nemweb.source_mode must be 'live' or 'snapshot'")

        landing_parent_path = spark_session.conf.get("nemweb.landing_path").rstrip("/")
        if not landing_parent_path.startswith("/Volumes/"):
            raise ValueError("nemweb.landing_path must be a Unity Catalog Volume path")
        # The bundle setting is the shared managed Volume parent.  Resolve the
        # exact same validated <parent>/<mode> root as the lander; otherwise the
        # lander can succeed while Auto Loader silently watches an empty parent.
        landing_path = mode_landing_root(
            landing_parent_path, source_mode
        ).as_posix()

        market_timezone = spark_session.conf.get("nemweb.market_timezone")
        session_timezone = spark_session.conf.get("spark.sql.session.timeZone")
        if session_timezone != "Australia/Brisbane":
            raise ValueError("spark.sql.session.timeZone must be Australia/Brisbane")
        if market_timezone != "Australia/Brisbane":
            raise ValueError(
                "NEM market timestamps must use fixed AEST semantics "
                "(Australia/Brisbane)"
            )
        try:
            landing_catalog = spark_session.conf.get("nemweb.landing_catalog")
            landing_schema = spark_session.conf.get("nemweb.landing_schema")
        except (KeyError, TypeError):  # compatibility for focused local config fakes
            parts = landing_parent_path.split("/")
            landing_catalog, landing_schema = parts[2], parts[3]
        return cls(source_mode, landing_path, market_timezone, landing_catalog, landing_schema)
