"""
配置管理模組
統一管理所有配置參數
"""
import os
from pathlib import Path
from typing import Dict, Any

# 專案根目錄
SCRIPT_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 資料路徑
DATA_DIR = PROJECT_ROOT / 'data'
DECODED_DIR = DATA_DIR / 'decoded_quotes'
PROCESSED_DIR = DATA_DIR / 'processed_data'
LIMIT_UP_FILE = DATA_DIR / 'lup_ma20_filtered.parquet'

# 輸出路徑
OUTPUT_DIR = PROJECT_ROOT / 'frontend' / 'static' / 'api'
QUERY_RESULTS_DIR = DATA_DIR / 'single_query_results'

# 處理參數
DEFAULT_MAX_WORKERS = min(4, os.cpu_count() or 4)
PRICE_DECIMAL_DIVISOR = 10000  # 價格需要除以 10000

# 時間相關
TIMESTAMP_LENGTH = 12  # 時間戳補零長度
DATETIME_FORMAT = '%Y%m%d%H%M%S%f'
DATE_FORMAT = '%Y%m%d'

# 市場類型
MARKETS = ['OTC', 'TSE']

def get_quote_file_path(market: str, date: str) -> Path:
    """取得 Quote 檔案路徑"""
    return DATA_DIR / f"{market}Quote.{date}"

def get_output_dir(base_dir: Path, date: str) -> Path:
    """取得輸出目錄路徑"""
    output_dir = base_dir / date
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def get_config() -> Dict[str, Any]:
    """取得所有配置"""
    return {
        'data_dir': str(DATA_DIR),
        'decoded_dir': str(DECODED_DIR),
        'processed_dir': str(PROCESSED_DIR),
        'limit_up_file': str(LIMIT_UP_FILE),
        'output_dir': str(OUTPUT_DIR),
        'max_workers': DEFAULT_MAX_WORKERS,
        'price_divisor': PRICE_DECIMAL_DIVISOR,
        'markets': MARKETS
    }
