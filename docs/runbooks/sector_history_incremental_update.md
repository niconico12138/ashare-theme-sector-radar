# 行业历史增量补齐 Runbook

## 目标

在不覆盖既有可信历史的前提下，为冻结的完整行业集合补充新的 THS 行业指数
OHLC、成交量和成交额。输出仅用于本地 paper/shadow 研究。

## 安全模型

- 源目录只读，不在原文件上追加或覆盖。
- 使用源目录已有文件名冻结行业集合，不重新按接口当日列表选样。
- 所有行业先下载到同盘 staging 目录。
- 每条记录校验 ISO 日期、唯一递增、有限数、正 OHLC、OHLC 关系及非负成交量/额。
- 重叠日期内容不同立即失败，不允许静默改写旧记录。
- 所有行业必须返回完全相同的增量日期集合，并覆盖请求结束日。
- 任一行业失败时删除 staging，目标根保持不存在。
- 全部成功后用同盘目录原子改名发布；目标根已存在时拒绝运行。
- `update_manifest.json` 保存每个行业的旧文件、增量载荷和合并文件 SHA256。

## 2026-07-16 补齐记录

旧数据根：

```text
<project-root>/data_cache/sector_history
```

新数据根：

```text
data_cache\sector_history
```

执行命令：

```powershell
python scripts\update_sector_history_incremental.py `
  --source-root <project-root>/data_cache/sector_history `
  --output-root data_cache\sector_history `
  --start-date 2026-07-09 `
  --end-date 2026-07-16 `
  --expected-sector-count 90 `
  --sleep-seconds 0.1
```

验收结果：

```text
行业数              90
每行业旧记录        122
每行业新增记录      6
每行业合并记录      128
共同新增交易日      2026-07-09, 07-10, 07-13, 07-14, 07-15, 07-16
全部行业最后日期    2026-07-16
源文件 SHA 复验     90/90 通过
合并文件 SHA 复验   90/90 通过
源目录是否修改      否
manifest SHA256      829ab87658792ce28bad061fe39003180cbd8372296d85a08183cb117915dfc0
```

## 后续增量

不要覆盖 `data_cache\sector_history`。下一次应将当前完整根作为只读源，发布到
新的版本化目录，例如：

```powershell
python scripts\update_sector_history_incremental.py `
  --source-root data_cache\sector_history `
  --output-root data_cache\sector_history_v20260717 `
  --start-date 2026-07-17 `
  --end-date 2026-07-17 `
  --expected-sector-count 90
```

验证完成后，研究命令通过显式 `--history-root` 指向新版本。旧版本必须保留，直到
新版本的严格解析、覆盖率、方向分可用率和 no-lookahead 检查全部通过。

## 回滚

本方法不修改源目录。发现新版本异常时，将研究命令的 `--history-root` 改回上一版
即可；不要对旧目录执行 reset、覆盖合并或逐文件回写。

## 已知边界

- 数据来自 AkShare THS 行业指数接口，不包含历史行业成分版本。
- 完整90行业横截面是当前冻结研究集合，不等价于历史时点真实行业宇宙。
- 补齐数据不会自动使任何 shadow 分晋级，也不会生成实盘指令。
