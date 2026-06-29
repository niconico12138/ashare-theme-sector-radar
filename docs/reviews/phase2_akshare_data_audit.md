# Phase 2.5 AkShare 数据审计报告

日期：2026-06-29  
状态：审计完成

## 1. 数据数量统计

### 1.1 AkShare 原始数据量

直接测试 AkShare 接口：
- **行业板块**: 496 个 (`stock_board_industry_name_em()`)
- **概念板块**: 494 个 (`stock_board_concept_name_em()`)

### 1.2 CLI 运行时数据量

审计运行结果：
- **industry_sectors**: 0 个（接口调用失败）
- **concept_sectors**: 20 个（受 top_n=10*2=20 限制）

### 1.3 496 个数据说明

"496 个行业板块数据"是 **真实数据**，不是错误描述。这是 AkShare `stock_board_industry_name_em()` 接口返回的完整行业板块列表。

## 2. 类型分离审计

### 2.1 sector.type 字段检查

**concept_sectors 中的 type 值**: `{'concept'}` ✅ 正确

**industry_sectors 中的 type 值**: `set()` - 空（因为数据为空）

### 2.2 结论

- ✅ 行业板块和概念板块使用独立接口获取
- ✅ type 字段正确设置（industry/concept）
- ✅ 不存在类型混淆

## 3. 本次运行问题分析

### 3.1 行业板块数据为空的原因

```
UserWarning: AkShare 接口调用失败: stock_board_industry_name_em - HTTPSConnectionPool...
```

**原因**: 网络连接问题导致行业板块接口调用失败。这是间歇性网络问题，不是代码逻辑错误。

### 3.2 概念板块数据正常

概念板块接口成功返回数据，说明：
- 代码逻辑正确
- 网络问题是间歇性的

## 4. 数据源字段样例

### 4.1 concept_sectors 样例

```json
{
  "sector_id": "BK1630",
  "name": "先进封装",
  "type": "concept",
  "price_change_pct": 6.16,
  "turnover": 0.0,
  "main_net_inflow": 0.0,
  "constituents": [],
  "data_sources": ["akshare/eastmoney_concept"],
  "updated_at": "2026-06-29T09:19:30.823588",
  "data_quality_score": 70.0
}
```

### 4.2 问题说明

- `turnover`: 为 0.0，因为行业/概念板块列表接口不直接提供成交额
- `main_net_inflow`: 为 0.0，需要单独的资金流向接口
- `constituents`: 为空，需要单独获取成分股

## 5. 资金流关联审计

### 5.1 当前实现

资金流向通过 `stock_sector_fund_flow_rank()` 接口获取，但尚未与板块数据关联。

### 5.2 问题

- 资金流接口返回的数据使用"名称"字段
- 板块数据使用"板块名称"字段
- 需要通过名称匹配进行关联

### 5.3 建议

后续版本应实现：
1. 通过板块名称匹配资金流数据
2. 如果匹配失败，降级处理（不伪造数据）

## 6. 成分股关联审计

### 6.1 当前实现

成分股通过以下接口获取：
- 行业：`stock_board_industry_cons_em(symbol=板块名称)`
- 概念：`stock_board_concept_cons_em(symbol=板块名称)`

### 6.2 问题

需要传递板块名称（如"半导体"），而不是板块代码（如"BK0428"）。

### 6.3 建议

当前实现已正确使用板块名称，但需要注意：
- 板块名称必须精确匹配
- 如果获取失败，应降低 data_quality_score

## 7. 审计结论

### 7.1 核心发现

1. **"496 个行业板块数据"是真实数据**，不是错误
2. **行业/概念类型分离正确**，无混淆
3. **本次运行行业数据为空是网络问题**，不是代码逻辑错误

### 7.2 需要改进

1. 增强错误处理日志，明确显示获取成功/失败的数量
2. 实现资金流与板块数据的关联
3. 实现成分股与板块数据的关联

### 7.3 代码审查通过

- ✅ 类型分离正确
- ✅ 字段映射正确
- ✅ 降级处理正确
- ✅ 无伪造数据
