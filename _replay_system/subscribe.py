import redis
import time
import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
import pandas as pd  # pip install pandas

# --- 設定 Redis ---
REDIS_HOST = '192.168.100.130'
REDIS_PORT = 6379
CHANNELS = ['4939', '8042', '2485', '6291']

# ==========================================
# 1. 定義資料結構 (Structure)
# ==========================================

@dataclass
class TickData:
    """
    單筆 Tick 的結構
    時間精度：包含微秒 (Microseconds)
    """
    code: str
    datetime: datetime.datetime  # 包含微秒的完整時間物件
    price: float           # 成交價
    volume: int            # 單量
    total_volume: int      # 總量
    tick_type: int         # 1: 外盤 (Buy), 2: 內盤 (Sell), 0: 中性
    
    # 記錄當下判斷依據的五檔 (方便回測驗證)
    ref_bid_price: float = 0.0
    ref_ask_price: float = 0.0
    
    sim_trade: int = 0     # 試撮旗標

@dataclass
class DepthCache:
    """暫存五檔資訊 (狀態用)"""
    timestamp: str
    best_bid: float = 0.0
    best_ask: float = 0.0

# ==========================================
# 2. 核心處理器 (處理時間與內外盤)
# ==========================================

class MarketDataProcessor:
    def __init__(self):
        self.depth_state: Dict[str, DepthCache] = {}
        self.tick_buffer: List[TickData] = []

    def _parse_time(self, time_str: str) -> datetime.datetime:
        """
        解析 HHMMSSuuuuuu (微秒)
        例如: 131219825776 -> 13:12:19.825776
        例如: 83005993712 -> 08:30:05.993712 (需補零)
        """
        # 1. 去空白並補零至 12 位數 (HHMMSSuuuuuu)
        s = time_str.strip().zfill(12)
        
        # 2. 取得今日日期
        now_date = datetime.date.today()
        
        try:
            # %f 在 Python 中是用來解析微秒 (6位數)
            # s 格式為: HHMMSSffffff
            t_obj = datetime.datetime.strptime(s, "%H%M%S%f").time()
            
            # 3. 結合成完整的 datetime 物件
            return datetime.datetime.combine(now_date, t_obj)
        except ValueError:
            # 萬一格式錯誤，回傳當下時間 (或可選擇拋出錯誤)
            return datetime.datetime.now()

    def parse_depth(self, line: str):
        """解析五檔並更新 Cache"""
        parts = [x.strip() for x in line.split(',')]
        if len(parts) < 4: return

        code = parts[1].lstrip()
        time_str = parts[2]
        
        best_bid = 0.0
        best_ask = 0.0
        current_side = None
        
        # 解析 BID/ASK
        for part in parts[3:]:
            if part.startswith("BID"):
                current_side = "BID"
                continue
            elif part.startswith("ASK"):
                current_side = "ASK"
                continue
            
            if "*" in part:
                try:
                    p_str, _ = part.split("*")
                    price = int(p_str) / 10000
                    
                    if current_side == "BID":
                        if best_bid == 0.0: best_bid = price
                    elif current_side == "ASK":
                        if best_ask == 0.0: best_ask = price
                except ValueError:
                    continue

        # 更新該股票的五檔狀態
        self.depth_state[code] = DepthCache(timestamp=time_str, best_bid=best_bid, best_ask=best_ask)

    def parse_trade(self, line: str) -> Optional[TickData]:
        """解析成交，結合 Cache 判斷內外盤"""
        parts = [x.strip() for x in line.split(',')]
        if len(parts) < 7: return None

        code = parts[1].lstrip()
        time_str = parts[2]
        sim_flag = int(parts[3])
        
        try:
            price = int(parts[4]) / 10000
            vol = int(parts[5])
            total_vol = int(parts[6])
        except ValueError:
            return None

        # --- 內外盤判斷 ---
        tick_type = 0
        ref_bid = 0.0
        ref_ask = 0.0

        if code in self.depth_state:
            cache = self.depth_state[code]
            ref_bid = cache.best_bid
            ref_ask = cache.best_ask
            
            if ref_ask > 0 and price >= ref_ask:
                tick_type = 1 # 外盤
            elif ref_bid > 0 and price <= ref_bid:
                tick_type = 2 # 內盤

        # --- 建立資料物件 ---
        tick = TickData(
            code=code,
            datetime=self._parse_time(time_str), # 這裡會處理微秒
            price=price,
            volume=vol,
            total_volume=total_vol,
            tick_type=tick_type,
            ref_bid_price=ref_bid,
            ref_ask_price=ref_ask,
            sim_trade=sim_flag
        )
        
        self.tick_buffer.append(tick)
        return tick

    def get_dataframe(self) -> pd.DataFrame:
        """轉出 Pandas DataFrame"""
        if not self.tick_buffer:
            return pd.DataFrame()
        
        df = pd.DataFrame([asdict(t) for t in self.tick_buffer])
        # 強制確保 datetime column 是 datetime64[ns] 格式，方便後續操作
        df['datetime'] = pd.to_datetime(df['datetime'])
        return df

# ==========================================
# 3. 主程式 Loop
# ==========================================

def subscribe_and_listen():
    processor = MarketDataProcessor()
    
    while True:
        try:
            print(f"Connecting to Redis {REDIS_HOST}...")
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_timeout=5)
            p = r.pubsub(ignore_subscribe_messages=True)
            p.subscribe(CHANNELS)
            print(f"Subscribed to: {', '.join(CHANNELS)}")
            
            for message in p.listen():
                if message['type'] != 'message':
                    continue

                data = message['data'].decode('utf-8')

                # 1. 先處理五檔更新狀態
                if data.startswith("depthLog"):
                    processor.parse_depth(data)

                # 2. 再處理成交並產生訊號
                elif data.startswith("Trade"):
                    tick = processor.parse_trade(data)
                    
                    if tick:
                        # 顯示微秒格式: %f
                        t_str = tick.datetime.strftime('%H:%M:%S.%f')
                        type_str = "外盤(Buy)" if tick.tick_type == 1 else ("內盤(Sell)" if tick.tick_type == 2 else "-")
                        
                        print(f"[{tick.code}] {t_str} | 價:{tick.price} | 量:{tick.volume} | {type_str}")

                        # 模擬：累積 5 筆後顯示 DataFrame
                        if len(processor.tick_buffer) % 5 == 0:
                            print("\n--- Pandas DataFrame Snapshot ---")
                            df = processor.get_dataframe()
                            # 顯示最後幾筆，確認時間格式
                            print(df[['datetime', 'code', 'price', 'tick_type']].tail(3))
                            print("---------------------------------")
                            
        except redis.exceptions.ConnectionError:
            print("⚠️ Redis lost, retrying...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    subscribe_and_listen()