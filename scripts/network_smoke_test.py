"""
Phase 52: Network smoke test for AkShare catalyst events
Tests real network connectivity and downloads a small sample.
Usage:
    python scripts/network_smoke_test.py
    python scripts/network_smoke_test.py --symbols 600519,000001,300750
    python scripts/network_smoke_test.py --output results.json
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Resolve project root relative to this script (no hardcoded paths)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="AkShare network smoke test")
    parser.add_argument(
        "--symbols",
        default="600519,000001,300750",
        help="Comma-separated stock symbols to test (default: 600519,000001,300750)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: scripts/phase52_network_smoke_result.json)",
    )
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    out_path = (
        Path(args.output)
        if args.output
        else PROJECT_ROOT / "scripts" / "phase52_network_smoke_result.json"
    )

    results = {
        "test_name": "phase52_network_smoke_test",
        "timestamp": datetime.now().isoformat(),
        "akshare_import": False,
        "network_connectivity": False,
        "stock_news_em_test": False,
        "sample_data": None,
        "error_type": None,
        "error_message": None,
        "source_status": "untested",
    }

    # Step 1: Test AkShare import
    try:
        import akshare as ak

        results["akshare_import"] = True
        results["akshare_version"] = getattr(ak, "__version__", "unknown")
        print(f"[OK] AkShare imported, version={results['akshare_version']}")
    except Exception as e:
        results["error_type"] = "import_error"
        results["error_message"] = str(e)[:200]
        results["source_status"] = "akshare_import_failed"
        print(f"[FAIL] AkShare import failed: {e}")
        _save_results(results, out_path)
        sys.exit(0)

    # Step 2: Test network connectivity with stock_news_em
    all_news = []
    failed_symbols = []

    # Title field candidates — AkShare versions may use different column names
    title_candidates = ["新闻标题", "标题", "title"]

    for symbol in symbols:
        print(f"\n[TEST] stock_news_em(symbol={symbol})...")
        try:
            df = ak.stock_news_em(symbol=symbol)
            if df is not None and len(df) > 0:
                results["network_connectivity"] = True
                results["stock_news_em_test"] = True
                news_count = len(df)
                print(f"  [OK] Got {news_count} news items")
                cols = list(df.columns)
                # Determine title column
                title_col = None
                for cand in title_candidates:
                    if cand in cols:
                        title_col = cand
                        break
                # Take first 2 as sample
                for _, row in df.head(2).iterrows():
                    raw_title = str(row.get(title_col, "")) if title_col else ""
                    item = {
                        "symbol": symbol,
                        "title": raw_title[:80],
                        "source": "akshare_stock_news_em",
                        "columns": cols,
                    }
                    all_news.append(item)
                    print(f"    title: {item['title']}")
            else:
                print(f"  [WARN] Empty result for {symbol}")
                failed_symbols.append(symbol)
        except Exception as e:
            error_str = str(e)[:200]
            print(f"  [FAIL] {error_str}")
            failed_symbols.append(symbol)
            if results["error_type"] is None:
                results["error_type"] = "network_error"
                results["error_message"] = error_str

    results["sample_data"] = all_news
    results["failed_symbols"] = failed_symbols
    results["success_symbols"] = [s for s in symbols if s not in failed_symbols]

    # Determine overall status
    if results["stock_news_em_test"]:
        results["source_status"] = "network_available"
    elif results["akshare_import"]:
        results["source_status"] = "network_unavailable"
    else:
        results["source_status"] = "akshare_unavailable"

    print(f"\n=== Summary ===")
    print(f"  AkShare import: {results['akshare_import']}")
    print(f"  Network connectivity: {results['network_connectivity']}")
    print(f"  stock_news_em test: {results['stock_news_em_test']}")
    print(f"  Overall status: {results['source_status']}")
    if results["error_type"]:
        print(f"  Error: {results['error_type']}: {results['error_message'][:100]}")

    _save_results(results, out_path)


def _save_results(results, out_path):
    """Save results JSON, creating parent dirs if needed."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
