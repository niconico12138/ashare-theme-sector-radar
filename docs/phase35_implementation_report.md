# Phase 35: 本地历史概念成分股数据层 - 实施报告

## 实施日期: 2026-07-05

## 一、修改文件清单

### market_data_service (已存在)

| 文件 | 状态 | 说明 |
|------|------|------|
| `market_data_service/providers/local_concept_members_provider.py` | ✅ 已存在 | LocalConceptMembersProvider 实现 |
| `market_data_service/data/concept_members_history.csv` | ✅ 已存在 | 4 个概念的样例数据 |
| `market_data_service/services/constituents.py` | ✅ 已存在 | Fallback 链已包含 local_concept_members |
| `market_data_service/client.py` | ✅ 已存在 | 已支持 as_of 参数 |
| `market_data_service/api.py` | ✅ 已存在 | 已支持 as_of 参数和 X-Data-Source header |

### theme-sector-radar-dev (本次修改)

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `unified_pipeline.py` | 修改 | health gate 识别 http_local_concept_members 为真实数据源 |
| `sector_stock_bridge.py` | 修改 | source_counter 添加 http_local_concept_members |
| `unified_pipeline.py` | 修改 | 报告生成显示 http_local_concept_members |
| `tests/theme_sector_radar/test_unified_bridge.py` | 修改 | valid_labels 添加 http_local_concept_members |

## 二、新增数据样例说明

### concept_members_history.csv

| 概念 | 股票数量 | 股票代码 |
|------|----------|----------|
| 光刻机 | 8 | 002371, 688012, 688561, 603160, 300236, 603659, 300346, 688120 |
| 硅能源 | 7 | 002459, 601012, 300274, 600438, 688599, 688390, 688032 |
| 猴痘概念 | 7 | 002399, 300122, 300601, 300347, 300759, 002007, 600196 |
| 重组蛋白 | 7 | 300347, 300759, 300122, 300601, 600196, 002007, 300760 |

CSV 格式:
```csv
as_of,concept,code,name,source
2026-07-01,光刻机,002371,北方华创,manual_snapshot
```

## 三、测试结果

### market_data_service
- **测试数量**: 290 passed
- **状态**: ✅ 全部通过

### theme-sector-radar-dev
- **测试数量**: 993 passed, 3 skipped
- **状态**: ✅ 全部通过

## 四、2026-07-01 重跑结果摘要

### API 验证
```
GET /boards/concept/光刻机/constituents?as_of=2026-07-01
HTTP 200
X-Data-Source: local_concept_members
返回 8 只股票
```

### Pipeline 运行结果

#### 成分股来源
| 板块 | 来源 | 股票数 |
|------|------|--------|
| 光刻机 | http_local_concept_members | 8 |
| 硅能源 | http_local_concept_members | 7 |
| 猴痘概念 | http_local_concept_members | 7 |
| 重组蛋白 | http_local_concept_members | 7 |

#### 候选股数量变化
- **Before**: 13 只 (4 个概念 unavailable)
- **After**: 18 只趋势 + 13 只短线 = 31 只高关联度个股

#### 健康门禁
- **Before**: FAIL (unavailable 板块占比 4/9 >= 30%)
- **After**: WARN (离线映射占比 5/9 >= 50%，但所有板块都有数据)

## 五、是否还存在 unavailable 概念

**否** - 所有 4 个之前 unavailable 的概念现在都有成分股数据:
- ✅ 光刻机: 8 只成分股
- ✅ 硅能源: 7 只成分股
- ✅ 猴痘概念: 7 只成分股
- ✅ 重组蛋白: 7 只成分股

## 六、验收确认

- ✅ 光刻机、硅能源、猴痘概念、重组蛋白不再 unavailable
- ✅ constituent_sources 包含 http_local_concept_members
- ✅ 候选股数量: Before 13 -> After 18 (趋势) + 13 (短线)
- ✅ 健康门禁: Before FAIL -> After WARN
- ✅ Markdown 报告里能看到本地历史概念成分股来源
- ✅ 不泄露 LLM key
- ✅ 不输出买卖建议

## 七、实施要点

### 核心修改

1. **unified_pipeline.py health gate** (第 655-680 行):
   - 将 `http_local_concept_members` 添加到 `real_sources` 计算
   - 修改条件判断以识别 local_concept 作为真实数据源

2. **sector_stock_bridge.py source_counter** (第 1089 行):
   - 添加 `"http_local_concept_members": 0` 到初始化

3. **unified_pipeline.py 报告生成** (第 784 行):
   - 在数据来源状态表格中添加 `http_local_concept_members`

4. **test_unified_bridge.py valid_labels** (第 791 行):
   - 添加 `"http_local_concept_members"` 到有效标签集合

### 数据流

```
theme-sector-radar-dev
  -> sector_stock_bridge.fetch_sector_constituents()
    -> market_data_http_client.get_board_constituents(as_of=...)
      -> GET /boards/concept/{name}/constituents?as_of=2026-07-01
        -> market_data_service
          -> constituents.py fallback chain:
            1. EM (失败)
            2. local_concept_members (成功!)
          -> 返回 8 只股票
    -> source = "http_local_concept_members"
```
