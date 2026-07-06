"""
板块历史数据下载器

使用 AkShare THS 接口下载行业/概念板块历史数据。
"""

import json
import os
import time
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import SectorType


class SectorHistoryDownloader:
    """板块历史数据下载器"""

    def __init__(
        self,
        data_cache_dir: str = "data_cache",
        sleep_seconds: float = 1.0,
    ):
        """
        初始化下载器

        Args:
            data_cache_dir: 数据缓存目录
            sleep_seconds: 请求间 sleep 秒数
        """
        self.data_cache_dir = data_cache_dir
        self.sleep_seconds = sleep_seconds
        self._client = None

    def _get_client(self):
        """获取 AkShare 客户端"""
        if self._client is None:
            try:
                import akshare as ak
                self._client = ak
            except ImportError:
                raise ImportError(
                    "akshare 未安装，请运行: pip install akshare"
                )
        return self._client

    def _safe_call(self, func, *args, **kwargs) -> Optional[Any]:
        """
        安全调用 AkShare 接口

        Returns:
            调用结果，失败返回 None
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            warnings.warn(f"AkShare THS call failed: {func.__name__} - {str(e)}")
            return None

    def get_sector_list(
        self,
        sector_type: SectorType,
    ) -> List[Dict[str, str]]:
        """
        获取板块列表

        Args:
            sector_type: 板块类型

        Returns:
            板块列表 [{"name": "...", "code": "..."}]
        """
        ak = self._get_client()

        if sector_type == SectorType.INDUSTRY:
            df = self._safe_call(ak.stock_board_industry_name_ths)
        else:
            df = self._safe_call(ak.stock_board_concept_name_ths)

        if df is None or df.empty:
            return []

        sectors = []
        for _, row in df.iterrows():
            sectors.append({
                "name": str(row.get("板块名称", row.get("name", ""))),
                "code": str(row.get("板块代码", row.get("code", ""))),
            })

        return sectors

    def download_sector_history(
        self,
        sector_name: str,
        sector_type: SectorType,
        start_date: str,
        end_date: str,
    ) -> Optional[Dict[str, Any]]:
        """
        下载单个板块历史数据

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            板块历史数据字典，失败返回 None
        """
        ak = self._get_client()

        try:
            if sector_type == SectorType.INDUSTRY:
                df = self._safe_call(
                    ak.stock_board_industry_index_ths,
                    symbol=sector_name,
                    start_date=start_date,
                    end_date=end_date,
                )
            else:
                df = self._safe_call(
                    ak.stock_board_concept_index_ths,
                    symbol=sector_name,
                    start_date=start_date,
                    end_date=end_date,
                )

            if df is None or df.empty:
                return None

            # 检查是否有价格变化数据
            price_change_available = "涨跌幅" in df.columns or "change_pct" in df.columns

            # 转换为记录列表
            records = []
            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    val = row[col]
                    # 转换 date/datetime 对象为字符串
                    if hasattr(val, 'isoformat'):
                        record[col] = val.isoformat()
                    else:
                        record[col] = val
                records.append(record)

            return {
                "sector_name": sector_name,
                "sector_code": "",
                "sector_type": sector_type.value,
                "source": "akshare/ths",
                "start_date": start_date,
                "end_date": end_date,
                "fetched_at": datetime.now().isoformat(),
                "price_change_available": price_change_available,
                "records": records,
            }

        except Exception as e:
            warnings.warn(f"Download failed for {sector_name}: {str(e)}")
            return None

    def save_sector_history(
        self,
        sector_type: SectorType,
        sector_name: str,
        data: Dict[str, Any],
    ):
        """
        保存板块历史数据

        Args:
            sector_type: 板块类型
            sector_name: 板块名称
            data: 板块历史数据
        """
        # 创建目录
        type_dir = "industry" if sector_type == SectorType.INDUSTRY else "concept"
        dir_path = os.path.join(self.data_cache_dir, "sector_history", type_dir)
        os.makedirs(dir_path, exist_ok=True)

        # 保存文件
        file_path = os.path.join(dir_path, f"{sector_name}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_sector_history(
        self,
        sector_type: SectorType,
        sector_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        加载板块历史数据

        Args:
            sector_type: 板块类型
            sector_name: 板块名称

        Returns:
            板块历史数据，不存在返回 None
        """
        type_dir = "industry" if sector_type == SectorType.INDUSTRY else "concept"
        file_path = os.path.join(self.data_cache_dir, "sector_history", type_dir, f"{sector_name}.json")

        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            warnings.warn(f"Failed to load {file_path}: {str(e)}")
            return None

    def has_cache(
        self,
        sector_type: SectorType,
        sector_name: str,
    ) -> bool:
        """检查是否有缓存"""
        type_dir = "industry" if sector_type == SectorType.INDUSTRY else "concept"
        file_path = os.path.join(self.data_cache_dir, "sector_history", type_dir, f"{sector_name}.json")
        return os.path.exists(file_path)

    def download_sectors(
        self,
        sector_type: SectorType,
        start_date: str,
        end_date: str,
        symbols: Optional[List[str]] = None,
        top_n: int = 20,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        批量下载板块历史数据

        Args:
            sector_type: 板块类型
            start_date: 开始日期
            end_date: 结束日期
            symbols: 指定板块名称列表
            top_n: 下载数量
            refresh: 是否强制刷新

        Returns:
            下载摘要
        """
        # 获取板块列表
        if symbols:
            sectors = [{"name": s, "code": ""} for s in symbols]
        else:
            sectors = self.get_sector_list(sector_type)
            sectors = sectors[:top_n]

        # 下载统计
        success_count = 0
        failed_count = 0
        skipped_count = 0
        failed_symbols = []
        warnings_list = []
        output_paths = []

        for i, sector in enumerate(sectors):
            sector_name = sector["name"]

            # 检查缓存
            if not refresh and self.has_cache(sector_type, sector_name):
                skipped_count += 1
                continue

            # 下载数据
            data = self.download_sector_history(
                sector_name=sector_name,
                sector_type=sector_type,
                start_date=start_date,
                end_date=end_date,
            )

            if data is None:
                failed_count += 1
                failed_symbols.append(sector_name)
                warnings_list.append(f"Failed to download {sector_name}")
            else:
                # 保存数据
                self.save_sector_history(sector_type, sector_name, data)
                success_count += 1

                type_dir = "industry" if sector_type == SectorType.INDUSTRY else "concept"
                output_paths.append(
                    os.path.join(self.data_cache_dir, "sector_history", type_dir, f"{sector_name}.json")
                )

            # Sleep 避免接口压力
            if i < len(sectors) - 1:
                time.sleep(self.sleep_seconds)

        return {
            "requested_sector_type": sector_type.value,
            "requested_count": len(sectors),
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "source": "akshare/ths",
            "failed_symbols": failed_symbols,
            "warnings": warnings_list,
            "output_paths": output_paths,
        }


def save_download_summary(
    summary: Dict[str, Any],
    output_dir: str,
):
    """
    保存下载摘要

    Args:
        summary: 下载摘要
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "download_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 生成 Markdown
    md_content = _generate_summary_md(summary)
    md_path = os.path.join(output_dir, "download_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)


def _generate_summary_md(summary: Dict[str, Any]) -> str:
    """生成摘要 Markdown"""
    lines = []

    lines.append("# Sector History Download Summary")
    lines.append("")
    lines.append(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **Sector Type**: {summary['requested_sector_type']}")
    lines.append(f"- **Requested Count**: {summary['requested_count']}")
    lines.append(f"- **Success Count**: {summary['success_count']}")
    lines.append(f"- **Failed Count**: {summary['failed_count']}")
    lines.append(f"- **Skipped Count**: {summary['skipped_count']}")
    lines.append(f"- **Source**: {summary['source']}")
    lines.append("")

    if summary.get("failed_symbols"):
        lines.append("## Failed Symbols")
        lines.append("")
        for symbol in summary["failed_symbols"]:
            lines.append(f"- {symbol}")
        lines.append("")

    if summary.get("warnings"):
        lines.append("## Warnings")
        lines.append("")
        for warning in summary["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    return "\n".join(lines)
