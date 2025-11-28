"""
日誌系統模組
統一的日誌輸出格式
"""
import logging
import sys
from typing import Optional
from pathlib import Path

def setup_logger(
    name: str = 'stock_processor',
    level: int = logging.INFO,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    設定日誌系統

    Args:
        name: Logger 名稱
        level: 日誌級別
        log_file: 日誌檔案路徑（可選）

    Returns:
        配置好的 Logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重複添加 handler
    if logger.handlers:
        return logger

    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 檔案 handler（如果指定）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

def log_progress(current: int, total: int, prefix: str = '進度') -> None:
    """
    輸出進度資訊

    Args:
        current: 當前進度
        total: 總數
        prefix: 前綴文字
    """
    percentage = (current / total * 100) if total > 0 else 0
    print(f'\r{prefix}: [{current}/{total}] {percentage:.1f}%', end='', flush=True)
    if current == total:
        print()  # 完成時換行

class ProgressBar:
    """簡單的進度條類別"""

    def __init__(self, total: int, prefix: str = '處理中', width: int = 50):
        self.total = total
        self.current = 0
        self.prefix = prefix
        self.width = width

    def update(self, amount: int = 1) -> None:
        """更新進度"""
        self.current += amount
        self._display()

    def _display(self) -> None:
        """顯示進度條"""
        if self.total == 0:
            return

        percentage = self.current / self.total
        filled = int(self.width * percentage)
        bar = '█' * filled + '░' * (self.width - filled)

        print(f'\r{self.prefix}: |{bar}| {self.current}/{self.total} ({percentage*100:.1f}%)',
              end='', flush=True)

        if self.current >= self.total:
            print()  # 完成時換行
