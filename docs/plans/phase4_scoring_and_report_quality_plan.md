# Phase 4 评分校准与报告质量验收计划

日期：2026-06-29  
目标：让板块雷达报告从"能生成"提升到"盘后复盘可读、可解释、可追踪"

## 1. 完整 fixture 样本设计

### 1.1 两种 profile
- `minimal`: 小样本，用于 degraded 测试（行业 5 个，概念 5 个）
- `full`: 完整样本，用于 ok 报告测试（行业 25+，概念 25+）

### 1.2 full fixture 要求
- 行业板块 >= 20
- 概念板块 >= 20
- 部分板块有资金流数据
- Top N 候选板块有成分股
- 至少一个行业 + 概念共振样例
- 覆盖不同风险等级（low/medium/high）
- 覆盖不同关注等级（focus/watch/caution）

### 1.3 CLI 参数
- `--fixture-profile full` (默认)
- `--fixture-profile minimal`

## 2. 行业评分 breakdown

### 2.1 分项
```json
{
  "trend_strength": 18.0,
  "fund_flow": 15.0,
  "breadth": 12.0,
  "persistence": 10.0,
  "market_fit": 7.0,
  "data_quality": 4.0,
  "positive_score": 66.0,
  "risk_penalty": -5.0,
  "final_score": 61.0
}
```

### 2.2 要求
- 分项之和必须能解释总分
- JSON 报告保留完整 breakdown
- Markdown 只展示最关键 2-3 个原因

## 3. 概念评分 breakdown

### 3.1 分项
```json
{
  "heat_burst": 20.0,
  "fund_confirmation": 15.0,
  "constituent_linkage": 12.0,
  "phase_score": 15.0,
  "catalyst": 7.0,
  "data_quality": 4.0,
  "positive_score": 73.0,
  "risk_penalty": -8.0,
  "final_score": 65.0
}
```

## 4. 风险扣分 breakdown

### 4.1 分项
```json
{
  "overheat_penalty": -3.0,
  "divergence_penalty": 0.0,
  "liquidity_penalty": 0.0,
  "data_quality_penalty": -2.0,
  "risk_flags": ["data_quality_low"],
  "risk_level": "low"
}
```

## 5. focus_level 解释规则

### 5.1 各等级要求
- **focus**: 说明为什么高分且风险可控
- **watch**: 说明还缺什么确认
- **core_only**: 说明为什么板块强但不能直接重点关注
- **caution**: 说明主要风险
- **avoid**: 默认不进入 Top N

### 5.2 输出字段
- `reasons`: 正向原因
- `downgrade_reasons`: 降级原因
- `watch_points`: 观察要点

## 6. 资金流匹配专项验收

### 6.1 测试覆盖
1. 精确名称匹配成功
2. 去空格后匹配成功
3. 多重匹配时不关联并写 warning
4. 无匹配时不关联并写 warning
5. matched_count / unmatched_count 正确
6. 资金流覆盖率影响 data_quality_score
7. industry/concept 不能交叉误匹配

## 7. 成分股覆盖专项验收

### 7.1 测试覆盖
1. 只对 Top N 候选板块拉成分股
2. industry 调用 industry cons 接口
3. concept 调用 concept cons 接口
4. 成分股失败时不崩溃
5. coverage=0 时降低数据质量
6. 成分股列表不得生成个股推荐语义
7. Markdown 中必须写明成分股仅用于验证板块强度

## 8. Markdown 报告质量标准

### 8.1 必须包含的章节
1. 市场短线温度
2. 行业板块 Top N
3. 概念板块 Top N
4. 行业 + 概念共振
5. 数据完整性
6. 风险提示
7. 声明

### 8.2 禁止内容
- buy/sell/hold
- 买入/卖出/持有建议/个股推荐

### 8.3 质量要求
- Top 表格中的核心原因不是空字符串
- 评分 breakdown 清晰可解释

## 9. 多日快照对比预留

### 9.1 轻量预留
- 在 SectorScore 模型中预留 previous_rank / rank_change 字段
- 如果没有前一日快照，字段可以为空
- 不要大改 pipeline

### 9.2 TODO
- Phase 5 做连续多日板块轮动追踪

## 10. 验收命令

```bash
# 默认离线测试
python -m pytest tests/theme_sector_radar/ -v

# Full fixture CLI
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --offline-fixture --fixture-profile full --output reports/theme_sector_radar/2026-06-28-phase4-fixture-full

# Minimal fixture CLI
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --offline-fixture --fixture-profile minimal --output reports/theme_sector_radar/2026-06-28-phase4-fixture-minimal

# AkShare CLI (如果网络可用)
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --provider akshare --refresh --fallback-cache-days 7 --output reports/theme_sector_radar/2026-06-28-phase4-akshare
```
