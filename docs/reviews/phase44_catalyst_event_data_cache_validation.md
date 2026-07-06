# Phase 44: Catalyst Event Data Cache Validation

## 修改内容

1. 新增 `theme_sector_radar/data/catalyst_events/__init__.py`
2. 新增 `theme_sector_radar/data/catalyst_events/models.py`：CatalystEvent 数据模型
3. 新增 `theme_sector_radar/data/catalyst_events/cache.py`：事件缓存
4. 新增 `theme_sector_radar/data/catalyst_events/mapper.py`：成分股映射
5. 新增 `theme_sector_radar/data/catalyst_events/downloader.py`：新闻下载器
6. 新增 `tests/fixtures/catalyst_events/sample_stock_news.json`：fixture 数据
7. 修改 `cli.py`：新增 `--download-catalyst-events` 参数
8. 新增 `tests/theme_sector_radar/test_catalyst_events.py`：12 个测试
9. 新增 `docs/plans/phase44_catalyst_event_data_cache_plan.md`

## CatalystEvent 字段结构

| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | str | 事件唯一标识 |
| event_date | str | 事件日期 |
| source | str | 数据源 |
| source_url | str | 原始链接 |
| title | str | 标题 |
| summary | str | 摘要 |
| event_type | str | stock_news/announcement/policy/macro/unknown |
| related_symbols | list | 关联股票代码 |
| related_industries | list | 关联行业 |
| related_concepts | list | 关联概念 |
| confidence | float | 置信度 |
| freshness | str | same_day/recent/stale/unknown |
| raw_payload_hash | str | 原始数据哈希 |

## 缓存路径

- `data_cache/catalyst_events/YYYY-MM-DD/events.json`
- `data_cache/catalyst_events/YYYY-MM-DD/source_status.json`

## Offline Fixture 下载结果

- 5 个 fixture 事件成功加载
- 3 个股票映射到行业（白酒、电池）
- 1 个 unmapped（未知公司）

## 成分股映射结果

- 600519 → 白酒
- 300750 → 电池、新能源汽车、储能
- 999999 → unmapped

## source_status 示例

```json
{
  "source_id": "fixture",
  "status": "fixture",
  "requested_symbols": 2,
  "success_count": 2,
  "failed_count": 0
}
```

## 是否新增 CatalystEventAgent

**否。** 本阶段只实现缓存层。

## 是否影响生产决策规则

**否。** 事件数据不参与当前决策。

## 测试结果

12 个新增测试全部通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，事件缓存仅用于后续研究，不参与当前决策。*
