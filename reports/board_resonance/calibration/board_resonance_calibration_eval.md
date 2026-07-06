# Board Resonance Calibration Evaluation Report

**Evaluation Date**: 2026-07-06T18:13:32.269032
**Dates Evaluated**: 2026-07-01, 2026-07-02, 2026-07-03, 2026-07-06
**Calibration Set Version**: phase45
**Total Labels**: 30

## Evaluation Metrics

- **Exact Match Count**: 9
- **Exact Match Rate**: 30.0%
- **Within-One-Level Count**: 22
- **Within-One Accuracy**: 73.3%
- **Overestimated Count**: 5
- **Underestimated Count**: 6
- **Missing Count**: 13

## Score Distribution

### Strong Expected
- Count: 9
- Min: 62.45
- Max: 65.94
- Avg: 64.44

### Medium Expected
- Count: 3
- Min: 51.76
- Max: 66.04
- Avg: 61.11

### Weak/Unrelated Expected
- Count: 5
- Min: 38.76
- Max: 56.18
- Avg: 49.39

## Mismatch Samples

### Strong Expected but Not High

| Industry | Concept | Expected | Actual | Score | Type |
|----------|---------|----------|--------|-------|------|
| 生物制品 | 动物疫苗 | strong | medium | 64.58 | semantic_resonance |
| 生物制品 | 重组蛋白 | strong | medium | 62.99 | semantic_resonance |
| 半导体 | 光刻胶 | strong | medium | 62.45 | semantic_resonance |
| 电子化学品 | 光刻胶 | strong | medium | 63.82 | semantic_resonance |
| 化学原料 | 氟化工概念 | strong | medium | 62.98 | semantic_resonance |
| 电池 | 固态电池 | strong | missing | 0.00 | missing |

### Unrelated Expected but Actual Medium/High

| Industry | Concept | Expected | Actual | Score | Type |
|----------|---------|----------|--------|-------|------|
| 证券 | 动物疫苗 | unrelated | medium | 56.18 | neutral |
| 保险 | 氟化工概念 | unrelated | low | 47.37 | neutral |
| 白色家电 | 芬太尼 | unrelated | medium | 55.61 | neutral |

## Feedback Summary

### Underestimated Strong (6 samples)

| Industry | Concept | Expected | Actual | Score | Semantic | Overlap | Risk | Action |
|----------|---------|----------|--------|-------|----------|---------|------|--------|
| 生物制品 | 动物疫苗 | strong | medium | 64.58 | 0 | 0 | 0 | review_semantic_mapping |
| 生物制品 | 重组蛋白 | strong | medium | 62.99 | 0 | 0 | 0 | review_semantic_mapping |
| 半导体 | 光刻胶 | strong | medium | 62.45 | 0 | 0 | 0 | review_semantic_mapping |
| 电子化学品 | 光刻胶 | strong | medium | 63.82 | 0 | 0 | 0 | review_semantic_mapping |
| 化学原料 | 氟化工概念 | strong | medium | 62.98 | 0 | 0 | 0 | review_semantic_mapping |
| 电池 | 固态电池 | strong | missing | 0.00 | 0 | 0 | 0 | review_semantic_mapping |

### Overestimated Unrelated (3 samples)

| Industry | Concept | Expected | Actual | Score | Semantic | Overlap | Risk | Action |
|----------|---------|----------|--------|-------|----------|---------|------|--------|
| 证券 | 动物疫苗 | unrelated | medium | 56.18 | 0 | 0 | 0 | review_threshold |
| 保险 | 氟化工概念 | unrelated | low | 47.37 | 0 | 0 | 0 | review_threshold |
| 白色家电 | 芬太尼 | unrelated | medium | 55.61 | 0 | 0 | 0 | review_threshold |

### Missing Expected Strong (1 samples)

| Industry | Concept | Expected | Reason |
|----------|---------|----------|--------|
| 电池 | 固态电池 | strong | 电池与固态电池强相关 |

### Semantic Map Candidates (6 pairs)

| Industry | Concept | Current Score | Action |
|----------|---------|---------------|--------|
| 生物制品 | 动物疫苗 | 0 | add_to_board_resonance_map |
| 生物制品 | 重组蛋白 | 0 | add_to_board_resonance_map |
| 半导体 | 光刻胶 | 0 | add_to_board_resonance_map |
| 电子化学品 | 光刻胶 | 0 | add_to_board_resonance_map |
| 化学原料 | 氟化工概念 | 0 | add_to_board_resonance_map |
| 电池 | 固态电池 | 0 | add_to_board_resonance_map |

### Threshold Review Candidates (5 pairs)

| Industry | Concept | Score | Current | Action |
|----------|---------|-------|---------|--------|
| 生物制品 | 动物疫苗 | 64.58 | high >= 65 | consider_lowering_high_threshold |
| 生物制品 | 重组蛋白 | 62.99 | high >= 65 | consider_lowering_high_threshold |
| 半导体 | 光刻胶 | 62.45 | high >= 65 | consider_lowering_high_threshold |
| 电子化学品 | 光刻胶 | 63.82 | high >= 65 | consider_lowering_high_threshold |
| 化学原料 | 氟化工概念 | 62.98 | high >= 65 | consider_lowering_high_threshold |

## All Evaluations

| Industry | Concept | Expected | Actual | Score | Match | Missing |
|----------|---------|----------|--------|-------|-------|---------|
| 化学制药 | 创新药 | strong | high | 65.94 | ✅ |  |
| 化学制药 | 仿制药一致性评价 | strong | high | 65.94 | ✅ |  |
| 化学制药 | 芬太尼 | strong | high | 65.61 | ✅ |  |
| 生物制品 | 动物疫苗 | strong | medium | 64.58 | ❌ |  |
| 生物制品 | 重组蛋白 | strong | medium | 62.99 | ❌ |  |
| 半导体 | 光刻胶 | strong | medium | 62.45 | ❌ |  |
| 半导体 | 存储芯片 | strong | high | 65.61 | ✅ |  |
| 电子化学品 | 光刻胶 | strong | medium | 63.82 | ❌ |  |
| 化学原料 | 氟化工概念 | strong | medium | 62.98 | ❌ |  |
| 电池 | 固态电池 | strong | missing | 0.00 | ❌ | ⚠️ |
| 医疗服务 | 辅助生殖 | medium | high | 65.52 | ❌ |  |
| 医疗服务 | 阿尔茨海默概念 | medium | high | 66.04 | ❌ |  |
| 元件 | 超级电容 | medium | missing | 0.00 | ❌ | ⚠️ |
| 光伏设备 | 硅能源 | medium | missing | 0.00 | ❌ | ⚠️ |
| 风电设备 | 海上风电 | medium | missing | 0.00 | ❌ | ⚠️ |
| 证券 | 金融科技 | medium | missing | 0.00 | ❌ | ⚠️ |
| 农化制品 | 丙烯酸 | medium | missing | 0.00 | ❌ | ⚠️ |
| 化学原料 | 环氧丙烷 | medium | low | 51.76 | ❌ |  |
| 白色家电 | 超级电容 | weak | missing | 0.00 | ❌ | ⚠️ |
| 工程机械 | 华为海思概念股 | weak | missing | 0.00 | ❌ | ⚠️ |
| 纺织制造 | 合成生物 | weak | low | 38.76 | ✅ |  |
| 造纸 | 光刻胶 | weak | low | 49.05 | ✅ |  |
| 物流 | 创新药 | weak | missing | 0.00 | ❌ | ⚠️ |
| 养殖业 | 半导体 | weak | missing | 0.00 | ❌ | ⚠️ |
| 证券 | 动物疫苗 | unrelated | medium | 56.18 | ❌ |  |
| 煤炭 | 辅助生殖 | unrelated | missing | 0.00 | ✅ | ⚠️ |
| 银行 | 光刻胶 | unrelated | missing | 0.00 | ✅ | ⚠️ |
| 保险 | 氟化工概念 | unrelated | low | 47.37 | ❌ |  |
| 白色家电 | 芬太尼 | unrelated | medium | 55.61 | ❌ |  |
| 服装家纺 | 存储芯片 | unrelated | missing | 0.00 | ✅ | ⚠️ |
