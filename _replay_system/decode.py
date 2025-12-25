import pandas as pd
import numpy as np
import json
import os

# ==========================================
# 1. 設定檔案與路徑
# ==========================================
# 輸入檔案路徑
file_path = r"C:\Users\User\Documents\_web\_01_web\data\single_query_results\2025-12-24\6274.parquet"

# 輸出檔案名稱
output_dir = ""  # 留空表示輸出到當前目錄，或設為 "app" 輸出到 app 子目錄
output_filename = "6274_1224.json"
output_json = os.path.join(output_dir, output_filename) if output_dir else output_filename

if not os.path.exists(file_path):
    print(f"錯誤：找不到檔案 {file_path}")
    exit()

print(f"正在讀取資料：{file_path} ...")
df = pd.read_parquet(file_path)

# ==========================================
# 2. 資料過濾與【關鍵排序】
# ==========================================
print("正在處理資料排序與權重...")
df = df.sort_values('Timestamp').reset_index(drop=True)
df['Timestamp'] = df['Timestamp'].astype(np.int64)
df = df[df['Timestamp'] >= 90000000000].copy()

# 【關鍵修正 1】引入 Type_Rank 權重排序
# 修正邏輯：Depth (0) 排在 Trade (1) 前面，確保 Trade 能看到「同時間」的五檔
# 這樣做可以讓我們同時取得「成交後(Current)」與「成交前(Prev)」的狀態
df['Type_Rank'] = df['Type'].map({'Depth': 0, 'Trade': 1}).fillna(2)

# 重新排序：先按時間，時間相同按類型 (Depth 先, Trade 後)
df = df.sort_values(['Timestamp', 'Type_Rank']).reset_index(drop=True)

# 【關鍵修正 2】建立絕對順序 ID (Row ID)
# 因為我們已經按照「因果關係」排好序了，這個 index 就是物理上的發生順序
df['row_id'] = df.index

# ==========================================
# 3. 處理內外盤邏輯 (BS Flag)
# ==========================================
print("正在計算內外盤 (BS Flag) - 使用嚴格回溯邏輯...")

df_trade = df[df['Type'] == 'Trade'].copy()
# 建立 Depth 查找表，包含 row_id
depth_lookup = df[df['Type'] == 'Depth'][['row_id', 'Ask1_Price', 'Bid1_Price']].copy()
# 【關鍵修正 3.1】增加上一筆五檔狀態 (處理 "Trade eats Price" 但五檔已更新的情況)
depth_lookup['Ask1_Prev'] = depth_lookup['Ask1_Price'].shift(1)
depth_lookup['Bid1_Prev'] = depth_lookup['Bid1_Price'].shift(1)

# 【關鍵修正 3】使用 row_id 進行合併，但排除同時間的 Depth
# 邏輯：對於每一筆 Trade，使用「成交前」的五檔狀態
# 即使同時間有 Depth 更新，也要用更新前的狀態（符合 XQ 邏輯）
temp_merged = pd.merge_asof(
    df_trade[['row_id', 'Price']],
    depth_lookup,
    on='row_id',
    direction='backward',
    allow_exact_matches=True   # 改為 True，允許匹配同時間(同row_id前)的 Depth
)

# 防止浮點數誤差
p = temp_merged['Price'].round(4)
ask1 = temp_merged['Ask1_Price'].round(4)
bid1 = temp_merged['Bid1_Price'].round(4)
ask1_prev = temp_merged['Ask1_Prev'].round(4)
bid1_prev = temp_merged['Bid1_Prev'].round(4)

# 初始判定 (Quote Rule)
# 優先檢查當前五檔，若不符合則檢查上一筆五檔 (應對資料時間差)
conditions = [
    (p >= ask1) & (ask1 > 0),           # Current Out
    (p >= ask1_prev) & (ask1_prev > 0), # Previous Out (Eaten: 吃掉舊賣一)
    (p <= bid1) & (bid1 > 0),           # Current In
    (p <= bid1_prev) & (bid1_prev > 0)  # Previous In (Hit: 打到舊買一)
]
df_trade['BS_Flag'] = np.select(conditions, ['Out', 'Out', 'In', 'In'], default='Unknown')

# 可選：調試特定時間點（可以註解掉）
# debug_timestamp = 90111319589  # 09:01:11.319589
# if (df_trade['Timestamp'] == debug_timestamp).any():
#     debug_idx = df_trade[df_trade['Timestamp'] == debug_timestamp].index[0]
#     loc_idx = df_trade.index.get_loc(debug_idx)
#     print(f"\n=== Debug {debug_timestamp} ===")
#     print(f"  Price: {p.iloc[loc_idx]:.2f}")
#     print(f"  Bid1: {bid1.iloc[loc_idx]:.2f}")
#     print(f"  Ask1: {ask1.iloc[loc_idx]:.2f}")
#     print(f"  BS_Flag: {df_trade.loc[debug_idx, 'BS_Flag']}")

# 【關鍵修正 4】二次補救 (Tick Rule)
# 如果判定出來是 Unknown (例如開盤第一筆，或資料有缺失)，改用跟上一筆成交價比
print("正在執行 Tick Rule 補救...")

mask_unknown = (df_trade['BS_Flag'] == 'Unknown')
price_diff = df_trade['Price'].diff()

df_trade.loc[mask_unknown & (price_diff > 0), 'BS_Flag'] = 'Out'
df_trade.loc[mask_unknown & (price_diff < 0), 'BS_Flag'] = 'In'

# 平盤則繼承上一筆 (ffill)
df_trade['BS_Flag'] = df_trade['BS_Flag'].replace('Unknown', np.nan).ffill().fillna('None')

# 只保留需要的欄位 (row_id 用完可以丟了，或者留著除錯)
df_trade_final = df_trade[['Type', 'Timestamp', 'Datetime', 'Price', 'Volume', 'BS_Flag', 'Type_Rank']].copy()

# ==========================================
# 4. 準備 Depth 資料並合併
# ==========================================
print("正在整理 Depth 資料...")
df_depth = df[df['Type'] == 'Depth'].copy()
df_depth['BS_Flag'] = 'None'

# 補 0
depth_numeric_cols = [c for c in df_depth.columns if 'Bid' in c or 'Ask' in c]
df_depth[depth_numeric_cols] = df_depth[depth_numeric_cols].fillna(0)
df_depth_final = df_depth.drop(columns=['row_id']) # 清理不需要的欄位

# 確保欄位一致
for c in ['Price', 'Volume']:
    if c not in df_trade_final.columns: df_trade_final[c] = None

# 合併 Trade 和 Depth
print("正在合併與最終排序...")
df_replay = pd.concat([df_trade_final, df_depth_final], ignore_index=True)

# 再次依照我們定義好的黃金順序排序
df_replay = df_replay.sort_values(['Timestamp', 'Type_Rank']).reset_index(drop=True)

# 移除 Type_Rank (前端不需要這個)
df_replay = df_replay.drop(columns=['Type_Rank'])

# ==========================================
# 5. 輸出 JSON
# ==========================================
print("正在轉換格式並寫入 JSON...")

# Datetime 轉字串
df_replay['Datetime'] = df_replay['Datetime'].astype(str)

# NaN -> None (確保前端正確判讀)
df_replay = df_replay.where(pd.notnull(df_replay), None)

# 轉字典
json_data = df_replay.to_dict(orient='records')

# 確保輸出目錄存在
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 寫入
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(json_data, f, ensure_ascii=False, default=str)

output_path = os.path.abspath(output_json)
print(f"成功！已產生 {output_path}")
print(f"總筆數：{len(json_data)}")

# 統計內外盤
trade_stats = df_replay[df_replay['Type'] == 'Trade']['BS_Flag'].value_counts()
print(f"內外盤統計：")
for flag, count in trade_stats.items():
    print(f"  {flag}: {count} 筆")