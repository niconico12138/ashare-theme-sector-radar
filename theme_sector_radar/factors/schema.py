"""
统一因子 Schema 数据结构定义

使用 dataclass 定义 FactorValue 和 FactorSnapshot，
不引入重依赖，可 JSON 序列化。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class FactorValue:
    """单个因子的值和元信息。

    Attributes:
        factor_id: 因子唯一标识符
        raw_value: 原始值（可以是 None）
        score: 归一化后的分数 (0-100)
        category: 因子类别 (trend/momentum/volatility/volume/risk/reversal/sector/agent/composite)
        source_project: 来源项目/模块
        direction: 评分方向 (higher_is_better/lower_is_better/neutral/already_scored)
        lookback_days: 回溯天数（如适用）
        quality: 数据质量 (good/approximate/estimated/missing)
        display_name: 中文显示名
        description: 因子描述
        tags: 标签列表
    """

    factor_id: str
    raw_value: float | None
    score: float
    category: str
    source_project: str
    direction: str
    lookback_days: int | None
    quality: str
    display_name: str
    description: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为普通 dict，方便 JSON 序列化。"""
        return asdict(self)


@dataclass
class FactorSnapshot:
    """因子快照，包含某只股票在某一时点的所有因子值。

    Attributes:
        schema_version: schema 版本号
        as_of: 数据日期
        code: 股票代码
        name: 股票名称
        factors: 因子值列表
        summary: 汇总信息
    """

    schema_version: str = "1.0"
    as_of: str = ""
    code: str = ""
    name: str = ""
    factors: list[FactorValue] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为普通 dict，方便 JSON 序列化。"""
        d = asdict(self)
        return d
