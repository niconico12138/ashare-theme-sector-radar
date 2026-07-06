# Phase 44: Catalyst Event Data Cache

## 本阶段目标

实现外部催化事件缓存层，支持从个股新闻采集事件，并通过成分股映射到行业/概念层。

## 坚持原则

- 只做事件缓存层
- 事件数据不参与生产决策
- 网络下载可选
- 默认离线测试必须可运行
- 后续 Phase 45 才考虑 CatalystEventAgent

## 实现内容

1. 事件数据模型 (CatalystEvent)
2. 事件缓存读写
3. 成分股到板块的映射
4. 个股新闻下载器 (offline_fixture + network)
5. CLI 下载命令

## 缓存路径

- `data_cache/catalyst_events/YYYY-MM-DD/events.json`
- `data_cache/catalyst_events/YYYY-MM-DD/source_status.json`
