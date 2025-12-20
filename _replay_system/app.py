import streamlit as st
import pandas as pd
import numpy as np
import time
import streamlit.components.v1 as components

# ==========================================
# 1. CSS 樣式（修正紅綠能量條、每格定位/裁切、視覺更接近台股App）
# ==========================================
st.set_page_config(layout="wide", page_title="台股極速回放系統 Pro Max")

st.markdown("""
<style>
    .stApp { background-color: #0e0e0e; color: #e0e0e0; font-family: 'Roboto Mono', monospace; }
    :root { --up: #ff4d4f; --down: #00c853; --panel: #1a1a1a; --border: #333; }
    
    /* 五檔容器 */
    .ob-container { background-color: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 0; overflow: hidden; }
    .ticker-card { background-color: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 18px; text-align: center; margin-bottom: 10px; }

    /* 表格 */
    table.ob-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 15px; table-layout: fixed; }
    .ob-table thead th { padding: 8px 6px; font-size: 12px; color: #777; font-weight: 700; border-bottom: 1px solid #2a2a2a; }
    .ob-table td { 
        padding: 4px 8px; 
        border-bottom: 1px solid #242424; 
        height: 34px; 
        vertical-align: middle;
        position: relative;     /* ✅ 關鍵：讓能量條 absolute 以 td 為基準 */
        overflow: hidden;       /* ✅ 關鍵：能量條不會跑出格子 */
    }

    /* 數值顏色（你原本買=紅、賣=綠先保留） */
    .bid-vol { text-align: right; color: #e6e6e6; font-weight: 650; padding-right: 10px; }
    .ask-vol { text-align: left;  color: #e6e6e6; font-weight: 650; padding-left: 10px; }
    .bid-price { color: var(--up); font-weight: 850; border-right: 1px solid #333; font-size: 16px; }
    .ask-price { color: var(--down); font-weight: 850; font-size: 16px; }

    /* Diff 變化量 */
    .diff-txt { font-size: 11px; margin-left: 6px; font-weight: 850; opacity: 0.95; }

    /* ✅ 能量條：每格自己的淡底條（不會整片染色） */
    .vol-bar-bg { 
        position: absolute; 
        top: 5px; 
        bottom: 5px; 
        z-index: 0; 
        opacity: 0.18;
        border-radius: 5px;
    }
    .bid-bar { right: 6px; background-color: var(--up); }
    .ask-bar { left:  6px; background-color: var(--down); }

    .vol-text { 
        position: relative; 
        z-index: 1; 
        display: flex; 
        align-items: center; 
        gap: 4px;
        white-space: nowrap;
    }

    /* 大字報價 */
    .big-price { font-size: 56px; font-weight: 900; letter-spacing: 2px; margin: 8px 0; }
    .timestamp-micro { color: #aaa; font-size: 18px; margin-bottom: 6px; font-family: 'Courier New', monospace; font-weight: 800; }

    /* 頂部內外盤條 */
    .io-row { padding: 8px 12px; display:flex; justify-content:space-between; font-size:12px; font-weight:900; }
    .io-bar { display:flex; height:4px; width:100%; background:#2a2a2a; }
    .io-bar > div { transition: width 0.1s; }

</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. JavaScript 鍵盤監聽注入
# ==========================================
def inject_keyboard_listener():
    js_code = """
    <script>
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowLeft') {
            const buttons = window.parent.document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.innerText.includes('⏪')) { btn.click(); break; }
            }
        } else if (e.key === 'ArrowRight') {
            const buttons = window.parent.document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.innerText.includes('⏩')) { btn.click(); break; }
            }
        }
    });
    </script>
    """
    components.html(js_code, height=0, width=0)

# ==========================================
# 3. 資料處理 (ETL) - 修正版
# ==========================================
@st.cache_data
def load_data(file_path: str) -> pd.DataFrame:
    # 1. 讀取資料
    if file_path.lower().endswith('.json'):
        df = pd.read_json(file_path)
        if 'Datetime' in df.columns:
            df['Datetime'] = pd.to_datetime(df['Datetime'])
        return df

    df = pd.read_parquet(file_path)

    # 基礎清理
    df = df.sort_values('Timestamp').reset_index(drop=True)
    df = df[df['Timestamp'] >= 90000000000].copy()

    if not pd.api.types.is_datetime64_any_dtype(df['Datetime']):
        df['Datetime'] = pd.to_datetime(df['Datetime'])

    # ==========================================
    # 核心修正：引入 Type_Rank 權重排序
    # ==========================================
    # 我們給予「類型」一個權重，確保在 Timestamp 相同時：
    # Trade (0) 排在最前面 -> 接著才是 Depth (1)
    # 這樣代表：先成交，才會更新五檔。
    df['Type_Rank'] = df['Type'].map({'Trade': 0, 'Depth': 1}).fillna(2)
    
    # 重新排序：先按時間，時間相同按類型 (Trade 先, Depth 後)
    df = df.sort_values(['Timestamp', 'Type_Rank']).reset_index(drop=True)

    # ==========================================
    # 計算 BS Flag (內外盤)
    # ==========================================
    df_trade = df[df['Type'] == 'Trade'].copy()
    
    # 建立查找表：為了精確，我們也保留 Type_Rank 邏輯
    # 但 merge_asof 只能對一個鍵值，所以我們依賴排序好的 index (最穩)
    # 我們新增一個 'row_id' 當作絕對順序
    df['row_id'] = df.index
    df_trade['row_id'] = df_trade.index
    
    depth_lookup = df[df['Type'] == 'Depth'][['row_id', 'Ask1_Price', 'Bid1_Price']].copy()

    if df_trade.empty:
        st.warning("無成交資料")

    # ✅ 使用 row_id 進行合併，並設定 allow_exact_matches=False
    # 邏輯：對於每一筆 Trade，往回找 row_id 小於它的最近一筆 Depth
    # 因為我們已經把 Trade 排在同時間的 Depth 前面了，
    # 所以它一定會跳過同時間的 Depth，找到「真正的上一筆」舊五檔。
    temp_merged = pd.merge_asof(
        df_trade[['row_id', 'Price']],
        depth_lookup,
        on='row_id',
        direction='backward',
        allow_exact_matches=False 
    )

    # 價格比較 (加上 round 避免浮點數誤差)
    p = temp_merged['Price'].round(4)
    ask1 = temp_merged['Ask1_Price'].round(4)
    bid1 = temp_merged['Bid1_Price'].round(4)

    # 判斷邏輯：
    # 1. 正常外盤: 成交價 >= 賣一
    # 2. 穿價外盤: 成交價 > 舊賣一 (針對你的 34.65 案例)
    # 兩者其實都包含在 >= 裡面
    conditions = [
        p >= ask1, # 外盤
        p <= bid1  # 內盤
    ]
    df_trade['BS_Flag'] = np.select(conditions, ['Out', 'In'], default='Unknown')

    # ==========================================
    # 補救措施 (Tick Rule)
    # ==========================================
    # 如果真的還是判斷不出來 (Unknown)，跟上一筆成交價比
    mask_unknown = (df_trade['BS_Flag'] == 'Unknown')
    price_diff = df_trade['Price'].diff()
    
    df_trade.loc[mask_unknown & (price_diff > 0), 'BS_Flag'] = 'Out'
    df_trade.loc[mask_unknown & (price_diff < 0), 'BS_Flag'] = 'In'
    
    # 平盤或無法判斷，繼承上一筆
    df_trade['BS_Flag'] = df_trade['BS_Flag'].replace('Unknown', np.nan).ffill().fillna('None')

    # ==========================================
    # 合併輸出
    # ==========================================
    df_depth = df[df['Type'] == 'Depth'].copy()
    df_depth['BS_Flag'] = 'None'

    depth_cols = [c for c in df_depth.columns if ('Bid' in c or 'Ask' in c)]
    common = ['Type', 'Timestamp', 'Datetime', 'BS_Flag']
    
    for c in ['Price', 'Volume']:
        if c not in df_trade.columns: df_trade[c] = np.nan

    # 這裡直接 concat 即可，因為我們上面已經算好 flag 且排序過了
    # 但為了保險起見，我們再次依據 Timestamp 和 Type_Rank 排序
    df_replay = pd.concat([
        df_trade[common + ['Price', 'Volume']],
        df_depth[common + depth_cols]
    ], ignore_index=True)

    df_replay['Type_Rank'] = df_replay['Type'].map({'Trade': 0, 'Depth': 1}).fillna(2)
    df_replay = df_replay.sort_values(['Timestamp', 'Type_Rank']).reset_index(drop=True)
    
    return df_replay

def get_state_at_index(df: pd.DataFrame, target_idx: int):
    """快速回溯狀態：取目標 idx 前最後一筆 Depth & Trade，以及 Depth 的前一筆(用於 Diff)"""
    target_idx = max(0, min(int(target_idx), len(df) - 1))
    subset = df.iloc[:target_idx + 1]

    last_depth = prev_depth = last_trade = None

    depth_rows = subset[subset['Type'] == 'Depth']
    if not depth_rows.empty:
        last_depth = depth_rows.iloc[-1]
        if len(depth_rows) >= 2:
            prev_depth = depth_rows.iloc[-2]

    trade_rows = subset[subset['Type'] == 'Trade']
    if not trade_rows.empty:
        last_trade = trade_rows.iloc[-1]

    return last_depth, prev_depth, last_trade

# ==========================================
# 4. 渲染函式 (新增：五檔總量小計)
# ==========================================
# ==========================================
# 4. 渲染函式 (新增：掛單筆數 + 總量小計)
# ==========================================
def render_butterfly_with_diff(curr_depth, prev_depth, total_in, total_out) -> str:
    if curr_depth is None:
        return "<div class='ob-container' style='padding:20px;text-align:center'>等待報價...</div>"

    # --- 1. 時間戳記 ---
    ts_str = "--:--:--"
    if 'Datetime' in curr_depth:
        dt = curr_depth['Datetime']
        if isinstance(dt, pd.Timestamp):
            ts_str = dt.strftime('%H:%M:%S.%f')
        else:
            ts_str = str(dt)

    total = (total_in or 0) + (total_out or 0)
    in_pct = (total_in / total * 100) if total > 0 else 50
    out_pct = (total_out / total * 100) if total > 0 else 50

    # 動態 max_vol (計算能量條長度用)
    vols = []
    for i in range(1, 6):
        vols += [
            curr_depth.get(f'Bid{i}_Volume', 0) or 0,
            curr_depth.get(f'Ask{i}_Volume', 0) or 0
        ]
    max_vol = max(1, int(max(vols)))

    # --- 2. 迴圈生成每一行 (Row) ---
    rows_html = ""
    
    # 初始化累加器 (Volume & Order Count)
    sum_bid_vol = 0
    sum_ask_vol = 0
    sum_bid_ord = 0 # 買筆數總計
    sum_ask_ord = 0 # 賣筆數總計

    for i in range(1, 6):
        # 讀取價格與量
        bp = curr_depth.get(f'Bid{i}_Price', 0) or 0
        bv = curr_depth.get(f'Bid{i}_Volume', 0) or 0
        ap = curr_depth.get(f'Ask{i}_Price', 0) or 0
        av = curr_depth.get(f'Ask{i}_Volume', 0) or 0
        
        # ✅ 讀取筆數 (請確認你的欄位名稱是否為 _Order)
        bc = int(curr_depth.get(f'Bid{i}_Order', 0) or 0)
        ac = int(curr_depth.get(f'Ask{i}_Order', 0) or 0)

        # 累加
        sum_bid_vol += int(bv)
        sum_ask_vol += int(av)
        sum_bid_ord += bc
        sum_ask_ord += ac

        # 讀取上一筆 (用於 Diff)
        prev_bp = (prev_depth.get(f'Bid{i}_Price', 0) if prev_depth is not None else 0) or 0
        prev_bv = (prev_depth.get(f'Bid{i}_Volume', 0) if prev_depth is not None else 0) or 0
        prev_ap = (prev_depth.get(f'Ask{i}_Price', 0) if prev_depth is not None else 0) or 0
        prev_av = (prev_depth.get(f'Ask{i}_Volume', 0) if prev_depth is not None else 0) or 0

        # Diff 計算 (量變動)
        bid_diff = ""
        if bp > 0 and bp == prev_bp and bv != prev_bv:
            diff = int(bv - prev_bv)
            color = "var(--up)" if diff > 0 else "var(--down)"
            sign = "+" if diff > 0 else ""
            bid_diff = f"<span class='diff-txt' style='color:{color}'>({sign}{diff})</span>"

        ask_diff = ""
        if ap > 0 and ap == prev_ap and av != prev_av:
            diff = int(av - prev_av)
            color = "var(--up)" if diff > 0 else "var(--down)"
            sign = "+" if diff > 0 else ""
            ask_diff = f"<span class='diff-txt' style='color:{color}'>({sign}{diff})</span>"

        # 數值格式化
        bp_txt = f"{bp:.2f}" if bp > 0 else "-"
        bv_txt = f"{int(bv)}" if bv > 0 else "-"
        ap_txt = f"{ap:.2f}" if ap > 0 else "-"
        av_txt = f"{int(av)}" if av > 0 else "-"
        # 筆數格式化 (0 不顯示或顯示 -)
        bc_txt = f"{bc}" if bc > 0 else ""
        ac_txt = f"{ac}" if ac > 0 else ""

        # 能量條寬度
        bv_w = min(96, (bv / max_vol) * 96) if bv > 0 else 0
        av_w = min(96, (av / max_vol) * 96) if av > 0 else 0

        # ✅ 生成 Row HTML (新增最左與最右的 td)
        rows_html += f"""<tr>
<td class="count-col" style="text-align:center; color:#888; font-size:12px;">{bc_txt}</td>
<td class="bid-vol">
    <div class="vol-bar-bg bid-bar" style="width:{bv_w:.2f}%;"></div>
    <div class="vol-text" style="justify-content:flex-end;">{bv_txt}{bid_diff}</div>
</td>
<td class="bid-price">{bp_txt}</td>
<td class="ask-price">{ap_txt}</td>
<td class="ask-vol">
    <div class="vol-bar-bg ask-bar" style="width:{av_w:.2f}%;"></div>
    <div class="vol-text" style="justify-content:flex-start;">{av_txt}{ask_diff}</div>
</td>
<td class="count-col" style="text-align:center; color:#888; font-size:12px;">{ac_txt}</td>
</tr>"""

    # ✅ 小計 (Total) 行：增加筆數加總
    total_row_html = f"""<tr style="border-top: 1px solid #444; font-weight: bold; background-color: #161616;">
<td style="color: #aaa; font-size:12px;">{sum_bid_ord}</td>
<td class="bid-vol" style="color: #fff;">{sum_bid_vol}</td>
<td class="bid-price" style="border: none; font-size: 12px; color: #777;">小計</td>
<td class="ask-price" style="border: none; font-size: 12px; color: #777;">小計</td>
<td class="ask-vol" style="color: #fff;">{sum_ask_vol}</td>
<td style="color: #aaa; font-size:12px;">{sum_ask_ord}</td>
</tr>"""

    # --- 3. 組合最終 HTML ---
    # 注意：thead 也要增加欄位標題
    return f"""<div class="ob-container">
<div style="text-align: center; padding: 8px 0 2px 0; font-family: 'Courier New', monospace; font-size: 16px; font-weight: 800; color: #fff;">
    {ts_str}
</div>
<div class="io-row">
    <span style="color:var(--down)">內盤成交 {int(total_in):,}</span>
    <span style="color:var(--up)">外盤成交 {int(total_out):,}</span>
</div>
<div class="io-bar">
    <div style="width:{in_pct:.2f}%; background:var(--down);"></div>
    <div style="width:{out_pct:.2f}%; background:var(--up);"></div>
</div>
<table class="ob-table">
    <thead>
        <tr>
            <th style="width:10%;">筆</th>
            <th>委買量</th>
            <th>買價</th>
            <th>賣價</th>
            <th>委賣量</th>
            <th style="width:10%;">筆</th>
        </tr>
    </thead>
    <tbody>
        {rows_html}
        {total_row_html}
    </tbody>
</table>
</div>"""
# ==========================================
# 5. 主程式
# ==========================================
def main():
    inject_keyboard_listener()

    st.sidebar.header("🕹️ 控制台")
    # 請將此處路徑改為你的 Parquet 或 JSON 檔案
    default_path = r"C:\Users\user\Documents\_08_holdwin_data\_01_web\data\decoded_quotes\20251219\2344.parquet"
    file_path = st.sidebar.text_input("檔案路徑", default_path)

    if 'idx' not in st.session_state:
        st.session_state.idx = 0
    if 'running' not in st.session_state:
        st.session_state.running = False
    if 'total_in' not in st.session_state:
        st.session_state.total_in = 0
    if 'total_out' not in st.session_state:
        st.session_state.total_out = 0

    if st.sidebar.button("重新載入"):
        try:
            st.session_state.df = load_data(file_path)
            st.session_state.idx = 0
            st.session_state.running = False
            st.session_state.total_in = 0
            st.session_state.total_out = 0
            st.success(f"載入 {len(st.session_state.df)} 筆")
        except Exception as e:
            st.error(f"錯誤: {e}")

    if 'df' not in st.session_state:
        st.info("請先載入資料")
        return

    # --- 時間微秒跳轉 ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("⏱️ 微秒跳轉")
    target_time_str = st.sidebar.text_input("輸入時間 (HH:MM:SS.ffffff)", value="09:00:00.000000")

    if st.sidebar.button("跳轉"):
        try:
            base_date = st.session_state.df['Datetime'].iloc[0].date()
            full_time_str = f"{base_date} {target_time_str}"
            target_dt = pd.to_datetime(full_time_str)

            new_idx = st.session_state.df['Datetime'].searchsorted(target_dt)
            new_idx = int(min(max(0, new_idx), len(st.session_state.df) - 1))

            st.session_state.idx = new_idx
            st.session_state.running = False
            st.success(f"已跳轉: {target_dt.strftime('%H:%M:%S.%f')}")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"時間格式錯誤 (範例 09:00:05.123456): {e}")

    st.sidebar.markdown("---")

    # --- 播放控制 ---
    col_prev, col_play, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("⏪ 上一筆 (←)"):
            st.session_state.running = False
            st.session_state.idx = max(0, st.session_state.idx - 1)

    with col_play:
        play_btn = st.button("⏸ 暫停" if st.session_state.running else "▶ 自動播放")
        if play_btn:
            st.session_state.running = not st.session_state.running

    with col_next:
        if st.button("下一筆 ⏩ (→)"):
            st.session_state.running = False
            st.session_state.idx = min(len(st.session_state.df) - 1, st.session_state.idx + 1)

    # Timeline slider
    new_idx = st.slider("Timeline", 0, len(st.session_state.df) - 1, int(st.session_state.idx), label_visibility="collapsed")
    if new_idx != st.session_state.idx:
        st.session_state.idx = int(new_idx)
        st.session_state.running = False

    # 自動播放
    if st.session_state.running:
        st.session_state.idx += 1
        if st.session_state.idx >= len(st.session_state.df):
            st.session_state.running = False
        time.sleep(0.05)
        st.rerun()

    # --- 取得狀態 ---
    curr_row = st.session_state.df.iloc[int(st.session_state.idx)]
    last_depth, prev_depth, last_trade = get_state_at_index(st.session_state.df, st.session_state.idx)

    # ✅ 累加內外盤（只有在 running 時才累加，避免拖拉 slider 亂加）
    if st.session_state.running and curr_row['Type'] == 'Trade':
        vol = int(curr_row.get('Volume', 0) or 0)
        if curr_row.get('BS_Flag') == 'In':
            st.session_state.total_in += vol
        elif curr_row.get('BS_Flag') == 'Out':
            st.session_state.total_out += vol

    # --- 渲染畫面 ---
    col_L, col_R = st.columns([1, 1])

    with col_L:
        ob_html = render_butterfly_with_diff(
            last_depth,
            prev_depth,
            st.session_state.total_in,
            st.session_state.total_out
        )
        st.markdown(ob_html, unsafe_allow_html=True)

    with col_R:
        if last_trade is not None and pd.notna(last_trade.get('Price', np.nan)):
            p = last_trade.get('Price', np.nan)
            v = int(last_trade.get('Volume', 0) or 0)
            f = last_trade.get('BS_Flag', 'None')
            ts = last_trade['Datetime'].strftime('%H:%M:%S.%f')

            color = "var(--up)" if f == 'Out' else "var(--down)" if f == 'In' else "#ffffff"
            flag_txt = "外盤" if f == 'Out' else "內盤" if f == 'In' else "--"

            st.markdown(f"""
            <div class="ticker-card">
                <div class="timestamp-micro">{ts}</div>
                <div class="big-price" style="color:{color}">{p}</div>
                <div style="display:flex; justify-content:space-between; font-size:20px; padding:0 30px;">
                    <span>單量: {v}</span>
                    <span style="color:{color}">{flag_txt}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.info(f"Tick Info: Index={int(st.session_state.idx)} | Type={curr_row['Type']}")
        else:
            st.markdown("<div class='ticker-card'>等待成交...</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()

