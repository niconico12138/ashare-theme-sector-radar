# Phase 43: External Catalyst Data Research Validation

## 修改内容

1. 新增 `theme_sector_radar/research/__init__.py`
2. 新增 `theme_sector_radar/research/catalyst_data_source_research.py`
3. 修改 `cli.py`：新增 `--research-catalyst-sources` 参数
4. 新增 `docs/plans/phase43_external_catalyst_data_research_plan.md`

## 数据源研究结果

| 数据源 | 状态 | 样本数 | 说明 |
|--------|------|--------|------|
| AkShare Stock News | available | 10 | 需按股票代码查询，非板块级 |
| AkShare Stock Notice | unavailable | 0 | 接口参数问题 |
| AkShare Board Info | partial | 10 | 仅当前快照，无历史事件 |
| CNINFO Announcements | unavailable | 0 | 接口参数问题 |
| Macro Economic News | partial | 10 | 非结构化，需 NLP 处理 |

## 可用性评估

### 可用数据源
- **stock_news_em**: 可获取个股新闻，但需要按股票代码查询，非板块级

### 部分可用数据源
- **stock_board_concept_info_ths**: 可获取概念板块信息，但仅当前快照
- **news_economic_baidu**: 可获取宏观新闻，但非结构化

### 不可用数据源
- **stock_notice_report**: 接口参数问题
- **stock_individual_notice_report**: 接口参数问题

## 缓存层设计建议

1. 所有外部数据必须经过缓存层
2. 缓存目录: `data_cache/catalyst/`
3. 缓存格式: JSON
4. 缓存策略: 每日更新，保留 30 天
5. 网络失败时使用缓存数据

## 下一步建议

1. Phase 44: 实现 Catalyst Event Data Cache
2. 优先接入 stock_news_em（个股新闻）
3. 考虑通过板块成分股映射到板块级催化事件
4. 评估是否需要 NLP 处理非结构化新闻

## 测试结果

所有离线测试通过。

## 是否影响生产决策规则

**否。** 本阶段只是数据源研究。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，仅用于数据源研究，不构成投资建议。*
