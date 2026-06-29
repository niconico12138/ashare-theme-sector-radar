# Phase 8.6 权重实验输入快照修复与多日真实缓存实验准备计划

日期：2026-06-29  
目标：修复 weight_comparison 的 input_snapshot_hash，确保三套权重确实使用同一个可追踪输入快照

## 1. input_snapshot 生成策略

### 1.1 Fixture 模式
1. 先生成一次 raw_snapshot
2. 保存到 reports/experiments/weights/YYYY-MM-DD-fixture/input_snapshot.json
3. 三套权重都从该 input_snapshot.json 读取

### 1.2 Cache 模式
1. 查找 data_cache/YYYY-MM-DD/raw_snapshot.json
2. 或查找 reports/theme_sector_radar/YYYY-MM-DD/raw_snapshot.json
3. 找不到时实验失败

## 2. input_snapshot_hash 计算规则

### 2.1 计算方式
- 使用 MD5 哈希
- 基于文件内容计算
- 不基于文件路径

### 2.2 验证
- 如果文件不存在，返回 "file_not_found"
- 如果计算失败，实验应失败

## 3. comparison.json 必含字段

- input_snapshot_path
- input_snapshot_hash
- input_snapshot_created_at
- input_snapshot_source: fixture / cache / report

## 4. 多日真实缓存实验

### 4.1 命令
```bash
python -m theme_sector_radar.experiments.weight_comparison \
  --start-date 2026-06-24 \
  --end-date 2026-06-28 \
  --use-cache \
  --output reports/experiments/weights/2026-06-24_to_2026-06-28-cache
```

### 4.2 要求
- 不访问网络
- 对每个日期单独生成 comparison.json
- 生成 multi_day_summary.json 和 multi_day_summary.md
- 缓存天数不足时结论为 need_more_data
