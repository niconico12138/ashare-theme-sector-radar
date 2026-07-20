"""
数据模块

提供数据获取、缓存和快照管理。
"""

from .cache import DataCache
from .bars_data_router import AutoBarsClient
from .fixture_provider import FixtureProvider
from .providers import DataProvider
from .stockdb_sdk_client import StockDBSdkClient
from .today_realtime_client import TodayRealtimeClient
from .official_announcements import (
    archive_raw_announcement,
    build_event_ledger,
    build_event_record,
    build_source_health_report,
    default_source_registry,
    infer_effective_from,
    probe_source_registry,
)
from .risk_events import (
    adapt_policy_macro_fixture,
    aggregate_risk_events,
    build_risk_monitor_report,
    build_risk_event,
    detect_market_anomalies,
    extract_llm_shadow,
    fuse_risk_events,
    policy_macro_source_registry,
    validate_risk_event,
)
from .official_source_providers import CsrcOfficialDocumentProvider
from .commodity_prices import (
    BlockedCommodityPriceProvider,
    OfflineCommodityPriceProvider,
    archive_commodity_price_evidence,
    build_commodity_observation_ledger,
    commodity_price_source_registry,
    normalize_commodity_fixture,
    validate_commodity_observation,
)
from .event_impact_shadow import (
    build_commodity_price_change_event,
    build_copper_increase_research_case,
    map_event_impact_shadow,
    validate_event_impact_shadow,
)
from .event_enhancement import (
    build_copper_enhancement_research_case,
    build_event_enhancement,
    build_event_exposure_mapping,
    validate_event_enhancement,
    validate_event_exposure_mapping,
)
from .event_adjustment_shadow import (
    EventAdjustmentShadowConfig,
    build_copper_adjustment_research_case,
    build_event_adjustment_shadow,
    validate_event_adjustment_shadow,
)
from .event_adjustment_ranking_shadow import (
    build_base_ranking_snapshot,
    build_copper_ranking_ab_research_case,
    build_event_ab_evaluation_contract,
    build_event_ab_metric_preregistration,
    build_event_adjustment_manifest,
    build_event_adjustment_ranking_ab_shadow,
    validate_base_ranking_snapshot,
    validate_event_adjustment_manifest,
    validate_event_adjustment_ranking_ab_shadow,
)
from .event_prospective_collection import (
    ProspectiveReadinessConfig,
    archive_prospective_event_day,
    load_prospective_event_day,
)

__all__ = [
    "DataProvider",
    "FixtureProvider",
    "DataCache",
    "AutoBarsClient",
    "StockDBSdkClient",
    "TodayRealtimeClient",
    "archive_raw_announcement",
    "build_event_ledger",
    "build_event_record",
    "build_source_health_report",
    "default_source_registry",
    "infer_effective_from",
    "probe_source_registry",
    "adapt_policy_macro_fixture",
    "aggregate_risk_events",
    "build_risk_monitor_report",
    "build_risk_event",
    "detect_market_anomalies",
    "extract_llm_shadow",
    "fuse_risk_events",
    "policy_macro_source_registry",
    "validate_risk_event",
    "BlockedCommodityPriceProvider",
    "CsrcOfficialDocumentProvider",
    "OfflineCommodityPriceProvider",
    "archive_commodity_price_evidence",
    "build_commodity_observation_ledger",
    "build_commodity_price_change_event",
    "build_copper_increase_research_case",
    "commodity_price_source_registry",
    "map_event_impact_shadow",
    "normalize_commodity_fixture",
    "validate_commodity_observation",
    "validate_event_impact_shadow",
    "build_copper_enhancement_research_case",
    "build_event_enhancement",
    "build_event_exposure_mapping",
    "validate_event_enhancement",
    "validate_event_exposure_mapping",
    "EventAdjustmentShadowConfig",
    "build_copper_adjustment_research_case",
    "build_event_adjustment_shadow",
    "validate_event_adjustment_shadow",
    "build_base_ranking_snapshot",
    "build_copper_ranking_ab_research_case",
    "build_event_ab_evaluation_contract",
    "build_event_ab_metric_preregistration",
    "build_event_adjustment_manifest",
    "build_event_adjustment_ranking_ab_shadow",
    "validate_base_ranking_snapshot",
    "validate_event_adjustment_manifest",
    "validate_event_adjustment_ranking_ab_shadow",
    "ProspectiveReadinessConfig",
    "archive_prospective_event_day",
    "load_prospective_event_day",
]
