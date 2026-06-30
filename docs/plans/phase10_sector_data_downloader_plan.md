# Phase 10 Sector Data Downloader MVP 计划

日期：2026-06-29  
目标：新增板块历史数据下载能力，为后续策略筛选和回测做数据准备

## 1. 范围

### 1.1 支持的板块类型
- 行业板块 (industry)
- 概念板块 (concept)

### 1.2 使用的 AkShare 接口
- `stock_board_industry_name_ths()` - 获取行业板块列表
- `stock_board_concept_name_ths()` - 获取概念板块列表
- `stock_board_industry_index_ths(symbol, start_date, end_date)` - 行业板块历史
- `stock_board_concept_index_ths(symbol, start_date, end_date)` - 概念板块历史

### 1.3 不依赖东方财富 EM
- 当前服务器出口 IP 会被 EM 拒绝
- 使用同花顺 THS 接口

## 2. CLI 命令设计

### 2.1 基本命令
```bash
python -m theme_sector_radar.cli --download-sector-history \
  --sector-type industry \
  --start-date 2026-06-23 \
  --end-date 2026-06-30 \
  --top-n 20
```

### 2.2 可选参数
- `--sector-type industry / concept / both`
- `--symbols 生物制品,医疗服务,化学制药`
- `--top-n 20`
- `--refresh`
- `--sleep-seconds 1`

## 3. 数据存储

### 3.1 目录结构
```
data_cache/sector_history/
  ├── industry/
  │   └── {sector_name}.json
  └── concept/
      └── {sector_name}.json
```

### 3.2 JSON 文件结构
```json
{
  "sector_name": "生物制品",
  "sector_code": "BK0465",
  "sector_type": "industry",
  "source": "akshare/ths",
  "start_date": "2026-06-23",
  "end_date": "2026-06-30",
  "fetched_at": "2026-06-29T10:00:00",
  "price_change_available": true,
  "records": [...]
}
```

## 4. 下载摘要

### 4.1 输出路径
```
reports/data_downloads/YYYY-MM-DD/
  ├── download_summary.json
  └── download_summary.md
```

### 4.2 摘要字段
- requested_sector_type
- requested_count
- success_count
- failed_count
- skipped_count
- source
- failed_symbols
- warnings
- output_paths

## 5. 缓存策略

### 5.1 默认行为
- 已有缓存则跳过
- --refresh 时重新下载

### 5.2 错误处理
- 单个板块失败不中断全部任务
- 每个请求之间 sleep 避免接口压力
