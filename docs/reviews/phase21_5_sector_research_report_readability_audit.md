# Phase 21.5: Sector Research Report 语义审计与可读性优化

**审计日期**: 2026-06-30
**审计目标**: 审计和优化 Markdown 报告可读性、解释语义和分组展示

---

## 1. 当前报告问题

### 1.1 缺少"本报告如何阅读"章节
- 读者不知道从哪里开始阅读
- confidence_score 和 opportunity_score 的区别不清楚

### 1.2 缺少"按标签分组"展示
- 无法快速识别哪些板块属于"综合观察候选"
- 无法快速识别哪些板块属于"分歧观察"或"偏弱观察"

### 1.3 weak_or_avoid 使用了"建议回避"
- "建议回避"可能被误读为交易指令
- 应改为观察语义

### 1.4 过度确定性表达
- 需要检查并移除"必然"、"一定"、"肯定"等表达

---

## 2. 半导体 rotation_candidate 可读性检查

### 2.1 当前解释
- rotation_label: rotation_rising (板块处于上升阶段)
- technical_label: trend_conflicted (窗口之间存在分歧)
- heat_label: heat_fading (短线热度减弱)

### 2.2 解释是否足够
**是的**，报告清楚说明了：
- 为什么是 rotation_candidate: 轮动信号强 (rotation_rising)
- 冲突点: 技术面窗口分歧
- 观察要点: 观察是否持续升温

### 2.3 改进建议
可以增加更详细的解释，说明 rotation_candidate 的判定条件。

---

## 3. 医疗服务 conflicted 可读性检查

### 3.1 当前解释
- technical_label: trend_conflicted (窗口分歧)
- heat_label: heat_moderate (短线热度适中)
- rotation_label: rotation_lagging (板块处于落后阶段)

### 3.2 解释是否足够
**是的**，报告清楚说明了：
- 为什么是 conflicted: 技术面冲突 + 轮动落后
- 冲突点: 窗口分歧
- 观察要点: 等待更多确认

### 3.3 改进建议
可以更明确说明为什么不输出 weak_or_avoid。

---

## 4. weak_or_avoid 语义检查

### 4.1 当前表达
- "多维度偏弱，建议回避"

### 4.2 问题
- "建议回避" 可能被误读为交易指令

### 4.3 修复后表达
- "当前正向观察强度有限，信号偏弱" (当 opportunity_score < 0.3)
- "当前多维度偏弱，但仍有部分正向信号" (当 opportunity_score >= 0.3)

---

## 5. confidence_score / opportunity_score 解释检查

### 5.1 当前解释
- **confidence_score**: 当前标签可信度，**不是机会强度**
  - weak_or_avoid + 高 confidence_score 表示 '系统较有把握认为该板块偏弱'
- **opportunity_score**: 正向观察强度，技术面、热度、轮动等维度的正向信号

### 5.2 是否清楚
**是的**，报告明确说明了 confidence_score 不是机会强度。

---

## 6. 新增"本报告如何阅读"章节

### 6.1 内容
1. 先看共识标签，了解系统当前判断类型
2. 再看排序分，了解综合排序
3. 再看正向观察强度，判断正向信号强度
4. 再看证据充分度，判断数据是否完整
5. 再看风险可控度，判断风险是否可控
6. 标签可信度只表示当前标签的可信度，不等于正向观察强度
7. weak_or_avoid 表示多维信号偏弱，不是交易指令
8. conflicted 表示维度之间有分歧，需要继续观察

---

## 7. 新增"按标签分组"章节

### 7.1 分组规则
- **综合观察候选**: strong_consensus, trend_confirmed, trend_confirmed_but_strength_limited, rotation_candidate, defensive_watch
- **分歧观察**: conflicted, short_term_active_unconfirmed
- **偏弱观察**: weak_or_avoid
- **数据不足**: insufficient_data

### 7.2 展示格式
每个分组展示表格：
板块 | 标签 | 排序分 | 正向观察强度 | 证据充分度 | 风险可控度 | 标签可信度 | 主要观察点

---

## 8. 修复前后报告结构对比

### 修复前
1. 免责声明
2. 报告参数
3. 综合确认 Top N
4. 标签解释
5. 多维评分说明
6. 多维 Agent 观点
7. 窗口共识摘要
8. 风险与冲突摘要
9. 数据质量摘要
10. 观察要点汇总
11. 附录：字段说明

### 修复后
1. 免责声明
2. **本报告如何阅读** (新增)
3. 报告参数
4. 综合确认 Top N
5. **按标签分组** (新增)
6. 标签解释
7. 多维评分说明
8. 多维 Agent 观点
9. 窗口共识摘要
10. 风险与冲突摘要
11. 数据质量摘要
12. 观察要点汇总
13. 附录：字段说明

---

## 9. 测试结果

**542 passed**，所有测试通过。

---

## 10. ai-hedge-fund 状态

✅ 未修改 `ai-hedge-fund` 项目任何文件。
