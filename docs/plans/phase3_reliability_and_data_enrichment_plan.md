# Phase 3 真实盘后可用性加固计划

日期：2026-06-29  
目标：让 AkShare 模式在网络不稳定、部分接口失败时仍能产出语义可信的盘后板块报告

## 1. AkShare 网络重试策略

### 1.1 safe_call 增强
- retries: 默认 3 次
- retry_delay: 1 秒
- 捕获: 网络异常、空 DataFrame、字段缺失
- 返回: status (ok/degraded/failed)、warnings、elapsed_ms

### 1.2 重试逻辑
```
for attempt in range(retries):
    try:
        result = func(*args, **kwargs)
        if result is not None and not result.empty:
            return OkResult(result)
        else:
            warnings.append(f"第 {attempt+1} 次返回空数据")
    except NetworkError as e:
        warnings.append(f"第 {attempt+1} 次网络错误: {e}")
        sleep(retry_delay)
    except Exception as e:
        warnings.append(f"第 {attempt+1} 次异常: {e}")
        break
return FailedResult(warnings)
```

### 1.3 不崩溃保证
- 单个接口失败不影响整个 CLI
- 返回空列表 + degraded 状态
- warnings 记录失败原因

## 2. 最近可用缓存 fallback 策略

### 2.1 参数
- `--use-cache`: 优先使用指定日期缓存
- `--refresh`: 强制刷新
- `--fallback-cache-days 7`: 回退天数，默认 7

### 2.2 Fallback 逻辑
```
1. 尝试获取 as_of_date 的实时数据
2. 如果行业数据 < min_count:
   a. 搜索最近 N 天的缓存
   b. 找到可用缓存则使用
   c. 在报告中标明 source_as_of_date 和 cache_created_at
3. 如果没有可用缓存:
   a. 使用空数据
   b. status = degraded
```

### 2.3 缓存元数据
```json
{
  "provider": "akshare",
  "created_at": "2026-06-29T10:00:00",
  "as_of_date": "2026-06-28",
  "source_as_of_date": "2026-06-27",
  "is_fallback": true,
  "data_sources": ["akshare/eastmoney"]
}
```

## 3. 行业/概念最小可用数量门槛

### 3.1 默认配置
- industry_min_count: 20
- concept_min_count: 20

### 3.2 门槛处理
| 情况 | 处理 |
|------|------|
| industry >= 20 | 正常 |
| 10 <= industry < 20 | degraded, 继续 |
| industry < 10 | degraded, 警告 |
| industry = 0 | degraded, 尝试 fallback |

### 3.3 两种都低于门槛
- 生成 degraded 报告
- 不崩溃
- 明确说明原因

## 4. 数据质量评分

### 4.1 计算公式
```
base_score = 50

# 数据源完整性
if industry_count >= 20: base_score += 15
if concept_count >= 20: base_score += 15

# 资金流覆盖率
fund_flow_score = matched_count / total_count * 10
base_score += fund_flow_score

# 成分股覆盖率
constituent_score = enriched_count / top_n_count * 10
base_score += constituent_score

# 缓存 fallback 惩罚
if is_fallback: base_score -= 10

data_quality_score = min(base_score, 100)
```

### 4.2 降级规则
- 缺失行业数据: -20
- 缺失概念数据: -20
- 资金流匹配率 < 50%: -10
- 成分股覆盖率 < 50%: -5

## 5. 资金流关联策略

### 5.1 接口
- `stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")`
- `stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流")`

### 5.2 匹配逻辑
```
1. 标准化板块名称: 去空格、去特殊字符
2. 精确匹配: name == flow_name
3. 模糊匹配: name contains flow_name or flow_name contains name
4. 只在唯一匹配时关联
5. 多重匹配或无匹配: 不关联, 写 warnings
```

### 5.3 覆盖率输出
```json
{
  "industry_fund_flow_matched_count": 15,
  "concept_fund_flow_matched_count": 12,
  "unmatched_count": 8
}
```

## 6. 成分股关联策略

### 6.1 优化策略
- 不对全部 496+494 个板块拉成分股
- 只对 Top N 或 Top N*2 候选板块拉取
- 并行或串行请求，带重试

### 6.2 接口
- 行业: `stock_board_industry_cons_em(symbol=板块名称)`
- 概念: `stock_board_concept_cons_em(symbol=板块名称)`

### 6.3 失败处理
- 不崩溃
- constituents = []
- coverage = 0
- warnings 记录

## 7. 报告增强

### 7.1 JSON 报告新增字段
```json
{
  "status": "ok | degraded | failed",
  "provider_status": {
    "industry_sectors": "ok | degraded | failed",
    "concept_sectors": "ok | degraded | failed",
    "fund_flow": "ok | degraded | failed",
    "constituents": "ok | degraded | failed"
  },
  "data_completeness": {
    "industry_count": 20,
    "concept_count": 18,
    "industry_min_count": 20,
    "concept_min_count": 20
  },
  "cache_fallback": {
    "is_fallback": false,
    "source_as_of_date": null,
    "cache_created_at": null
  },
  "fund_flow_coverage": {
    "industry_matched": 15,
    "concept_matched": 12,
    "unmatched": 8
  },
  "constituent_coverage": {
    "enriched_count": 10,
    "total_candidates": 10,
    "coverage_rate": 100.0
  },
  "warnings": []
}
```

### 7.2 Markdown 报告新增章节
```markdown
## 数据完整性
- 行业板块数量: 20/20 ✅
- 概念板块数量: 18/20 ⚠️
- 资金流匹配率: 75%
- 成分股覆盖率: 100%
- 缓存 fallback: 否
- 报告状态: degraded
- Degraded 原因: 概念板块数量不足
```

## 8. 测试清单

| 测试文件 | 覆盖内容 |
|---------|---------|
| test_akshare_retry.py | 重试策略、超时、异常处理 |
| test_cache_fallback.py | 缓存回退、元数据、source_as_of_date |
| test_data_completeness.py | 最小数量门槛、降级状态 |
| test_fund_flow_matching.py | 名称匹配、覆盖率、唯一性 |
| test_constituent_enrichment.py | 成分股获取、失败降级 |
| test_degraded_report_contract.py | degraded 报告契约 |

## 9. 验收命令

```bash
# 默认离线测试
python -m pytest tests/theme_sector_radar/ -v

# 网络测试
python -m pytest tests/theme_sector_radar/ -m network -v

# Fixture CLI
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --offline-fixture --output reports/theme_sector_radar/2026-06-28-phase3-fixture

# AkShare CLI
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --provider akshare --refresh --fallback-cache-days 7 --output reports/theme_sector_radar/2026-06-28-phase3-akshare
```
