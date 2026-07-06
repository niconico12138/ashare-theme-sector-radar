# 外部催化数据源研究报告

> **免责声明**: 本报告仅用于数据源研究，不构成投资建议。

## 总览

- **基准日期**: 2026-06-29
- **候选数据源**: 5
- **可用**: 1
- **部分可用**: 2
- **不可用**: 2

## 数据源详情

### AkShare Stock News (stock_news_em)

- **类别**: news
- **状态**: available
- **样本数**: 10
- **历史覆盖**: recent only
- **稳定性**: moderate
- **字段**: 关键词, 新闻标题, 新闻内容, 发布时间, 文章来源
  - 获取到 10 条新闻
  - 需要按股票代码查询，非板块级

### AkShare Stock Notice (stock_notice_report)

- **类别**: notice
- **状态**: unavailable
- **样本数**: 0
- **历史覆盖**: unknown
- **稳定性**: unknown
  - 访问失败: '000001'

### AkShare Board Info (stock_board_concept_info_ths)

- **类别**: board_info
- **状态**: partial
- **样本数**: 10
- **历史覆盖**: current snapshot only
- **稳定性**: moderate
- **字段**: 项目, 值
  - 获取到 10 个概念板块信息
  - 仅当前快照，无历史事件数据

### CNINFO Announcements

- **类别**: announcement
- **状态**: unavailable
- **样本数**: 0
- **历史覆盖**: unknown
- **稳定性**: unknown
  - 访问失败: stock_individual_notice_report() missing 1 required positional argument: 'security'

### Macro Economic News (news_economic_baidu)

- **类别**: macro_news
- **状态**: partial
- **样本数**: 10
- **历史覆盖**: recent only
- **稳定性**: low
- **字段**: 日期, 时间, 地区, 事件, 公布
  - 获取到 99 条宏观新闻
  - 非结构化，需要 NLP 处理

## 建议

- 可用数据源: AkShare Stock News (stock_news_em)
- 部分可用数据源: AkShare Board Info (stock_board_concept_info_ths), Macro Economic News (news_economic_baidu)
- 建议: 先接入可用数据源，逐步扩展到部分可用数据源
- 注意: 所有外部数据需经过缓存层，避免网络依赖

---

*本报告由 Theme Sector Radar 自动生成，仅用于数据源研究，不构成投资建议。*