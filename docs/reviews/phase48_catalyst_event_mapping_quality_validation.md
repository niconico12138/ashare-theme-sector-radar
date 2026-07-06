# Phase 48: Catalyst Event Mapping Quality Validation

## 修改内容

1. 修改 `theme_sector_radar/data/catalyst_events/mapper.py`：增强 symbol/name 标准化
2. 修改 `theme_sector_radar/data/catalyst_events/models.py`：新增 mapping_status 字段
3. 新增 `theme_sector_radar/data/catalyst_events/mapping_quality.py`
4. 修改 `cli.py`：自动生成 mapping quality 报告
5. 新增 `tests/theme_sector_radar/test_catalyst_event_mapping_quality.py`：16 个测试

## symbol normalization 规则

- 提取 6 位连续数字
- 支持 SH/SZ 前缀和 .SH/.SZ/.XSHG/.XSHE 后缀
- 去空格和特殊字符
- 无法提取返回 None

## name normalization 规则

- 去空格
- 去常见后缀：股份、集团、有限公司、控股、科技、A、B
- 支持简称匹配（通过 ALIAS_MAP）

## 映射率前后对比

| 指标 | Phase 47 | Phase 48 |
|------|----------|----------|
| 映射率 | 20% | **80%** |
| mapped_by_symbol | 5 | 20 |
| unmapped | 20 | 5 |

## mapping_status 分布

| 状态 | 数量 |
|------|------|
| mapped_by_symbol | 20 |
| unmapped_symbol_not_found | 5 |

## top unmapped 示例

| Symbol | 名称 | 出现次数 | 原因 |
|--------|------|----------|------|
| 999999 | 某公司 | 5 | unmapped_symbol_not_found |

## ambiguous 行为

当多个 symbol 匹配同一名称时，标记为 ambiguous_name_match，不自动映射。

## mapping_quality 输出路径

- `reports/data_downloads/catalyst_events/YYYY-MM-DD_to_YYYY-MM-DD/catalyst_mapping_quality.json`
- `reports/data_downloads/catalyst_events/YYYY-MM-DD_to_YYYY-MM-DD/catalyst_mapping_quality.md`

## 是否修改 CatalystEventAgent vote

**否。**

## 是否影响生产决策规则

**否。**

## 测试结果

16 个新增测试全部通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，仅用于数据质量验证，不构成投资建议。*
