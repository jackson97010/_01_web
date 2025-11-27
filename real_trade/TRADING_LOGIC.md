# 交易策略進出場邏輯說明

## 策略概述

本策略是一個**基於量價突破與力竭反轉的短線做空策略**，主要捕捉價格創新高但買盤力竭的反轉機會。策略分為三個階段：觸發偵測、進場確認、出場執行。

**核心思想**：
1. 當價格創2分鐘新高且買盤爆量時觸發訊號
2. 等待買盤力竭（ratio_10s_30s衰退至觸發時的1/3）
3. 在合理回檔範圍（0.2%~0.6%）做空進場
4. 破低後等待空單回補或買盤力竭時停利出場
5. 向上突破0.8%時停損出場

---

## 一、觸發階段 (Trigger Detection)

### 觸發條件

當以下條件**同時滿足**時，產生觸發訊號：

#### 1. 價格條件
```python
price >= high_2m  # 創2分鐘新高
```

**說明**：
- `high_2m`：過去2分鐘的最高價（rolling window）
- 突破新高表示價格處於上升趨勢

#### 2. 買盤強度條件（時段動態）

```python
ratio_buy5min_33221 > threshold
```

**時段依賴閾值**：

| 時段 | 閾值 | 說明 |
|------|------|------|
| 09:05 ~ 09:20 | > 0.7 | 開盤初期，量能要求較低 |
| 09:20 ~ 10:00 | > 0.75 | 盤中過渡，量能要求中等 |
| 10:00 以後 | > 0.8 | 盤中穩定，量能要求較高 |

**指標說明**：
- `ratio_buy5min_33221`：5分鐘買盤比例（33221加權）
- 加權方式：最近的資料權重更高（3:3:2:2:1）
- 數值範圍：0 ~ 1，越高表示買盤越強

#### 3. 爆量條件

```python
ratio_15s_180s_w321 > 6.0
```

**指標說明**：
- `ratio_15s_180s_w321`：15秒買盤累積量 / 180秒買盤平均量（321加權）
- 閾值 6.0 表示短期買盤是平均水平的6倍
- 意義：短期爆量，可能是力竭前兆

#### 4. 時間過濾

```python
time >= 09:05:00
```

**原因**：避免開盤初期（09:00~09:05）的異常波動

#### 5. 冷卻機制

```python
cooldown_seconds = 30.0  # 30秒內不重複觸發
```

**作用**：
- 兩次觸發訊號之間至少間隔30秒
- 避免同一波段重複觸發
- 減少過度交易

### 觸發參數設定

```python
trigger_params = {
    'ratio_15s_180s_threshold': 6.0,      # 爆量閾值
    'filter_start_time': '09:05:00',      # 開始偵測時間
    'cooldown_seconds': 30.0              # 冷卻時間（秒）
}
```

### 觸發訊號輸出

每個觸發訊號（`TriggerSignal`）包含：
- `index`: 原始索引
- `timestamp`: 觸發時間
- `price`: 觸發價格
- `ratio_15s_180s_w321`: 觸發時的爆量比值
- `ratio_buy5min_33221`: 觸發時的買盤強度
- `ratio_10s_30s`: 觸發時的10秒/30秒比值（用於計算力竭閾值）
- `reason`: 觸發原因（'break_2min_high'）

---

## 二、進場階段 (Entry Signal Generation)

### 進場邏輯

觸發訊號產生後，**不會立即進場**，而是等待「力竭確認」與「回檔確認」。

#### 1. 力竭確認 (Exhaustion Detection)

**動態力竭閾值**：
```python
exhaustion_threshold = trigger_ratio_10s_30s / 3.0
```

**力竭條件**：
```python
ratio_10s_30s < exhaustion_threshold
```

**說明**：
- 使用 `ratio_10s_30s` 作為力竭指標（10秒買盤 / 30秒買盤）
- 閾值是**動態的**：觸發時的 ratio_10s_30s ÷ 3
- 意義：短期買盤衰退至觸發時的1/3，確認力竭

**時間窗口（動態調整）**：

| 時段 | 窗口大小 | 說明 |
|------|---------|------|
| 09:05 ~ 09:20 | 15秒 | 早盤快速反應 |
| 09:20 ~ 10:00 | 30秒 | 盤中過渡期 |
| 10:00 以後 | 45秒 | 盤中穩定期 |

**邏輯**：
- 從觸發時間開始，在對應的時間窗口內尋找力竭點
- 找到第一個滿足 `ratio_10s_30s < exhaustion_threshold` 的tick

#### 2. 回檔確認 (Pullback Validation)

力竭確認後，檢查每個tick的回檔幅度：

```python
pullback_pct = (reference_high - entry_price) / reference_high * 100
```

**參考高點**：
- `reference_high` = 觸發時的 `high_2m`（2分鐘高點）

**回檔要求**：
```python
min_pullback_pct <= pullback_pct <= max_pullback_pct
```

**一般情況**：
- `min_pullback_pct = 0.2`：最小回檔0.2%
- `max_pullback_pct = 0.6`：最大回檔0.6%

**開盤強勢策略**（開盤漲幅 > 6%）：
- `min_pullback_pct = 0.6`：最小回檔0.6%
- `max_pullback_pct = 2.0`：最大回檔2.0%

**過濾邏輯**：
- 回檔太小（< 0.2%）：可能只是價格震盪，不是真正回檔
- 回檔太大（> 0.6%）：可能已經跌過頭，風險增加
- 開盤強勢時：允許更大回檔空間，捕捉更多機會

#### 3. VWAP 乖離檢查（條件性啟用）

**啟用時機**：
- 進場時間在 **09:45:00** 之後

**VWAP 條件判斷**：

```python
vwap_divergence_pct = (entry_price - vwap) / vwap * 100

if entry_time < 09:45:00:
    vwap_pass = True  # 09:45之前不檢查
elif entry_price <= vwap:
    vwap_pass = True  # 價格在VWAP以下直接通過
elif vwap_divergence_pct >= 1.5:
    vwap_pass = True  # 乖離>=1.5%通過
else:
    vwap_pass = False  # 乖離<1.5%不通過
```

**邏輯表格**：

| 時間 | 價格 vs VWAP | 乖離幅度 | 結果 |
|------|-------------|---------|------|
| < 09:45 | 任意 | 任意 | ✅ 通過 |
| >= 09:45 | <= VWAP | 任意 | ✅ 通過 |
| >= 09:45 | > VWAP | >= 1.5% | ✅ 通過 |
| >= 09:45 | > VWAP | < 1.5% | ❌ 不通過 |

**意義**：
- 09:45之前市場尚未穩定，不檢查VWAP
- 價格在VWAP以下表示相對低位，可以進場
- 價格高於VWAP時，需要足夠的乖離（>=1.5%）才能進場，避免追高

### 開盤強勢策略

**觸發條件**：
```python
open_gap_pct = (open_price - prev_close) / prev_close * 100
if open_gap_pct > 6.0:
    # 啟用開盤強勢策略
```

**參數調整**：
```python
entry_params['min_pullback_pct'] = 0.6  # 0.2 → 0.6
entry_params['max_pullback_pct'] = 2.0  # 0.6 → 2.0
```

**策略意義**：
- 開盤漲幅 > 6% 表示市場極度強勢
- 價格波動空間更大，允許更深回檔
- 提高下限確保回檔足夠明顯，避免假訊號

### 進場參數設定

```python
entry_params = {
    'exhaustion_divisor': 3.0,                # 力竭閾值 = trigger_ratio / 3
    'min_pullback_pct': 0.2,                  # 最小回檔 (%)
    'max_pullback_pct': 0.6,                  # 最大回檔 (%)
    'window_seconds_early': 15.0,             # 09:05~09:20 窗口（秒）
    'window_seconds_mid': 30.0,               # 09:20~10:00 窗口（秒）
    'window_seconds_late': 45.0,              # 10:00後 窗口（秒）
    'vwap_divergence_threshold': 1.5,         # VWAP 乖離閾值 (%)
    'vwap_check_start_time': '09:45:00'       # VWAP 檢查啟用時間
}
```

### 進場訊號輸出

每個進場訊號（`EntrySignal`）包含：
- `trigger_index`: 觸發訊號索引
- `trigger_time`: 觸發時間
- `trigger_price`: 觸發價格
- `trigger_reason`: 觸發原因
- `exhaustion_time`: 力竭時間
- `entry_time`: 實際進場時間
- `entry_price`: 進場價格
- `exhaustion_ratio`: 力竭時的 ratio_10s_30s
- `reference_high`: 參考高點（觸發時的 high_2m）
- `pullback_pct`: 回檔幅度
- `vwap_at_entry`: 進場時的 VWAP
- `vwap_divergence_pct`: 與 VWAP 的乖離幅度

---

## 三、出場階段 (Exit Execution)

出場策略包含兩種機制：**停損出場** 和 **停利出場**。

### 3.1 停損出場 (Stop Loss)

#### 停損條件

```python
stop_loss_price = entry_price * 1.008  # 進場價 × (1 + 0.8%)
```

**觸發時機**：
- 進場後，價格**向上**觸及停損價

#### 停損邏輯

```python
# 尋找進場後第一個價格 >= stop_loss_price 的 tick
after_entry = trades[trades['time'] > entry_time]
hit_ticks = after_entry[after_entry['price'] >= stop_loss_price]

if not hit_ticks.empty:
    first_hit = hit_ticks.iloc[0]
    # 停損出場
```

#### 停損參數

```python
stop_loss_pct = 0.8  # 停損幅度 0.8%
```

#### 停損訊號輸出

每個停損訊號（`StopLossSignal`）包含：
- `entry_time`: 進場時間
- `entry_price`: 進場價格
- `stop_loss_price`: 停損價格
- `stop_loss_time`: 停損觸發時間
- `stop_loss_hit_price`: 停損成交價格
- `loss_pct`: 虧損幅度

---

### 3.2 停利出場 (Take Profit)

停利出場是**兩階段機制**：先破低、再等回補訊號。

#### 階段一：破低偵測

進場後，持續監控價格是否跌破以下任一低點：

```python
# 使用進場時的低點值（不是動態更新）
low_5m_at_entry   # 5分鐘低點
low_10m_at_entry  # 10分鐘低點
low_15m_at_entry  # 15分鐘低點
```

**重要**：
- 這些低點是在**進場時**當下的值
- 不是動態更新的rolling window
- 一旦破任一低點，進入第二階段

**破低判斷**：
```python
for tick in after_entry:
    if tick['price'] < low_5m_at_entry:
        break_low_time = tick['time']
        break_reason = 'break_5m_low'
        break
    elif tick['price'] < low_10m_at_entry:
        break_low_time = tick['time']
        break_reason = 'break_10m_low'
        break
    elif tick['price'] < low_15m_at_entry:
        break_low_time = tick['time']
        break_reason = 'break_15m_low'
        break
```

#### 階段二：回補訊號（二擇一）

一旦破低，等待以下任一條件出場：

##### 條件 1：量能回補訊號（優先）

```python
ratio_15s_180s > 7.0
```

**說明**：
- 空單回補導致賣壓減弱
- ratio_15s_180s：15秒賣盤 / 180秒賣盤平均
- 閾值 7.0（注意：代碼預設是10.0，但圖表使用7.0）

##### 條件 2：買盤力竭停利（備選）

**時間判斷**：
```python
if 10:00 <= break_time < 12:00:
    ratio_column = 'ratio_buy5min'  # 不加權版本
else:
    ratio_column = 'ratio_buy5min_33221'  # 加權版本
```

**條件**：
```python
ratio_column < 0.48
```

**說明**：
- 10:00~12:00 使用不加權版本（更穩定）
- 其他時間使用加權版本（更敏感）
- 數值 < 0.48 表示買盤持續低迷

##### 出場時機選擇

```python
# 取兩個條件中先發生的時間點
if ratio_exit_time and buy5min_exit_time:
    exit_time = min(ratio_exit_time, buy5min_exit_time)
elif ratio_exit_time:
    exit_time = ratio_exit_time
elif buy5min_exit_time:
    exit_time = buy5min_exit_time
else:
    # 沒有出場訊號，繼續持有
    pass
```

**邏輯**：
- 如果兩個條件同時符合，取先發生的
- 如果只有一個符合，就用該條件
- 如果都不符合，繼續持有（直到停損或收盤）

#### 停利參數設定

```python
exit_params = {
    'ratio_threshold': 10.0,         # ratio_15s_180s 閾值（建議調整為7.0）
    'buy5min_threshold': 0.48        # ratio_buy5min 閾值
}
```

**注意**：
- 代碼中 `ratio_threshold` 預設為 10.0
- 但實際圖表中顯示為 7.0
- 建議根據回測結果調整

#### 停利訊號輸出

每個出場訊號（`ExitSignal`）包含：
- `entry_time`: 進場時間
- `entry_price`: 進場價格
- `exit_time`: 出場時間
- `exit_price`: 出場價格
- `exit_reason`: 出場原因（如 'break_5m_low_ratio>7'）
- `reference_low`: 參考低點（5m/10m/15m）
- `ratio_at_exit`: 出場時的 ratio_15s_180s
- `profit_pct`: 獲利幅度

---

### 3.3 停損與停利的優先順序

**規則**：停損優先於停利

```python
# 檢查是否有停損，且停損時間比出場時間早
if stop_loss_time is not None and stop_loss_time < exit_time:
    # 停損先發生，跳過此出場訊號
    continue
```

**意義**：
- 如果停損和停利同時發生，以停損為準
- 避免在已經停損的單子上產生停利訊號
- 確保風險控制優先

---

## 四、完整策略流程圖

```
開始
  ↓
【開盤檢測】
  ├─ 計算開盤漲幅 = (open - prev_close) / prev_close × 100%
  ├─ 若 > 6% → 調整進場參數
  │   ├─ min_pullback_pct: 0.2% → 0.6%
  │   └─ max_pullback_pct: 0.6% → 2.0%
  └─ 否則 → 使用一般參數
  ↓
【觸發偵測】
  ├─ 價格創2分鐘新高 (price >= high_2m)
  ├─ ratio_buy5min_33221 > 時段閾值 (0.7/0.75/0.8)
  ├─ ratio_15s_180s_w321 > 6.0
  ├─ 時間 >= 09:05:00
  └─ 冷卻機制（30秒）
  ↓
觸發訊號產生
  ↓
【進場確認】
  ├─ 時間窗口：15s/30s/45s（依時段）
  ├─ 力竭確認：ratio_10s_30s < trigger_ratio / 3
  ├─ 回檔確認：0.2%~0.6%（或 0.6%~2.0%）
  └─ VWAP 檢查：
      ├─ < 09:45 → 通過
      ├─ price <= VWAP → 通過
      ├─ price > VWAP 且乖離 >= 1.5% → 通過
      └─ price > VWAP 且乖離 < 1.5% → 不通過
  ↓
進場訊號產生 → 做空進場
  ↓
【持倉監控】
  ├─ 停損監控：price >= entry_price × 1.008 → 停損出場
  │
  └─ 停利監控：
      ├─ 價格破5m/10m/15m低點？
      │   ├─ 否 → 繼續持有
      │   └─ 是 → 等待出場訊號
      │       ├─ ratio_15s_180s > 7 → 立即出場
      │       ├─ ratio_buy5min < 0.48 → 停利出場
      │       └─ 都不符合 → 繼續持有
  ↓
出場訊號產生 → 平倉
  ↓
結束
```

---

## 五、特徵計算方法 (Feature Engineering)

本章節詳細說明策略中使用到的所有特徵指標的計算算法，所有計算均基於 `feature_v6.py` 的實際實作。

### 5.0 時間縫合 (Time Stitching)

在計算所有滾動特徵之前，需要先進行**時間縫合**，排除緩搓（Halt）期間的時間影響。

#### 時間縫合邏輯

```python
# 1. 計算時間差
time_diff = Datetime.diff()

# 2. 判斷是否在緩搓期間
is_halt = in_halt_period  # 或 Flag == 1

# 3. 計算調整量
halt_adjustment = time_diff if is_halt else 0

# 4. 計算調整後時間
adj_datetime = Datetime - halt_adjustment.cumsum()
```

**說明**：
- 緩搓期間的時間會被「縫合」掉
- 所有滾動窗口計算都基於 `adj_datetime` 而非原始 `Datetime`
- 確保滾動窗口不受緩搓中斷影響

---

### 5.1 價格滾動特徵 (Rolling High/Low)

#### high_2m, high_3m, high_5m（滾動最高價）

**計算方法**：
```python
high_2m = Price.rolling_max_by('adj_datetime', '2m')
high_3m = Price.rolling_max_by('adj_datetime', '3m')
high_5m = Price.rolling_max_by('adj_datetime', '5m')
```

**說明**：
- 每個 tick 當下往前 N 分鐘區間的最高價
- 使用時間縫合後的 `adj_datetime`
- 動態更新的滾動窗口

**用途**：
- `high_2m`: 觸發條件，判斷是否創新高
- `high_3m`, `high_5m`: 進場時的參考高點（實際使用 high_2m）

#### low_2m, low_3m, low_5m, low_10m, low_15m（滾動最低價）

**計算方法**：
```python
low_2m = Price.rolling_min_by('adj_datetime', '2m')
low_3m = Price.rolling_min_by('adj_datetime', '3m')
low_5m = Price.rolling_min_by('adj_datetime', '5m')
low_10m = Price.rolling_min_by('adj_datetime', '10m')
low_15m = Price.rolling_min_by('adj_datetime', '15m')
```

**說明**：
- 每個 tick 當下往前 N 分鐘區間的最低價
- 使用時間縫合後的 `adj_datetime`
- 動態更新的滾動窗口

**用途**：
- `low_5m`, `low_10m`, `low_15m`: 出場條件，判斷是否破低

---

### 5.2 VWAP（成交量加權平均價）

**計算方法**：
```python
vwap = cumsum(Price × Volume) / cumsum(Volume)
```

**說明**：
- 從當天開盤起算的累積 VWAP
- 每個 tick 都包含在計算中（包含盤前試搓）
- 不受時間縫合影響，使用原始成交資料

**用途**：
- 進場條件之一（09:45 後檢查乖離）
- 判斷進場價格是否合理

**VWAP 乖離計算**：
```python
vwap_divergence_pct = (entry_price - vwap) / vwap × 100
```

---

### 5.3 買賣盤成交量 (Buy/Sell Volume)

#### vol_buy, vol_sell（單筆買賣盤量）

**計算方法**：
```python
vol_buy = Volume if tick_type == '1' else 0
vol_sell = Volume if tick_type == '2' else 0
```

**說明**：
- `tick_type == '1'`: 外盤（買盤成交）
- `tick_type == '2'`: 內盤（賣盤成交）
- 這是所有 ratio 指標的基礎

---

### 5.4 ratio_15s_180s（15秒/180秒買盤比，原始版本）

**計算方法**：
```python
# 1. 計算 15 秒買盤累積量
vol_buy_15s = vol_buy.rolling_sum_by('adj_datetime', '15s')

# 2. 計算 180 秒買盤累積量
vol_buy_180s = vol_buy.rolling_sum_by('adj_datetime', '180s')

# 3. 計算 ratio（等價於 15s×12 / 180s）
ratio_15s_180s = (vol_buy_15s × 12) / vol_buy_180s
```

**說明**：
- 分子：15 秒買盤量 × 12 = 180 秒買盤量（假設均勻分布）
- 分母：180 秒買盤量（原始總和）
- **無加權**，所有時間段等權重

**用途**：
- 出場條件：> 7.0 表示空單回補

---

### 5.5 ratio_15s_180s_w321（15秒/180秒買盤比，加權版本）

**計算方法**：

#### 步驟 1：準備滾動數據

```python
# 產生 15s, 30s, 45s, ..., 180s 的滾動買盤量
for i in 1 to 12:
    roll_vol_buy_{i}_15s = vol_buy.rolling_sum_by('adj_datetime', f'{i×15}s')
```

#### 步驟 2：計算加權分母（321 加權）

```python
# 0-60s (0-1分鐘): 權重 3/6 = 0.5
# 60-120s (1-2分鐘): 權重 2/6 = 0.333
# 120-180s (2-3分鐘): 權重 1/6 = 0.167

w_buy_180_321 = (
    roll_vol_buy_4_15s × (3/6) +                              # 0-60s
    (roll_vol_buy_8_15s - roll_vol_buy_4_15s) × (2/6) +      # 60-120s
    (roll_vol_buy_12_15s - roll_vol_buy_8_15s) × (1/6)       # 120-180s
)
```

#### 步驟 3：計算 ratio

```python
ratio_15s_180s_w321 = (vol_buy_15s × 12) / w_buy_180_321
```

**加權邏輯表格**：

| 時間區間 | 累積窗口 | 權重 | 說明 |
|---------|---------|------|------|
| 0 ~ 1 分鐘 | 0 ~ 60s | **3/6** (0.5) | 最近資料，權重最高 |
| 1 ~ 2 分鐘 | 60 ~ 120s | **2/6** (0.333) | 中期資料 |
| 2 ~ 3 分鐘 | 120 ~ 180s | **1/6** (0.167) | 遠期資料，權重最低 |

**說明**：
- 加權方式：**最近的資料權重更高**
- 分子：仍使用 15s × 12（無加權）
- 分母：使用 321 加權的 180s 買盤量
- 相較原始版本，更敏感於近期變化

**用途**：
- 觸發條件：> 6.0 表示短期爆量

---

### 5.6 ratio_buy5min_33221（5分鐘買盤比例，加權版本）

**計算方法**：

#### 步驟 1：準備滾動數據

```python
# 產生 1m, 2m, 3m, 4m, 5m 的滾動買盤量和總量
for i in 1 to 5:
    roll_vol_buy_{i}_1m = vol_buy.rolling_sum_by('adj_datetime', f'{i}m')
    roll_Volume_{i}_1m = Volume.rolling_sum_by('adj_datetime', f'{i}m')
```

#### 步驟 2：計算加權買盤量和總量（33221 加權）

```python
# 權重: 3/11, 3/11, 2/11, 2/11, 1/11
weights_33221 = [3/11, 3/11, 2/11, 2/11, 1/11]

w_buy_33221 = 0
w_vol_33221 = 0

for i in 1 to 5:
    # 計算該分鐘區間的量（差分）
    if i == 1:
        bucket_buy = roll_vol_buy_1_1m
        bucket_vol = roll_Volume_1_1m
    else:
        bucket_buy = roll_vol_buy_{i}_1m - roll_vol_buy_{i-1}_1m
        bucket_vol = roll_Volume_{i}_1m - roll_Volume_{i-1}_1m

    # 加權累加
    w_buy_33221 += bucket_buy × weights_33221[i-1]
    w_vol_33221 += bucket_vol × weights_33221[i-1]
```

#### 步驟 3：計算 ratio

```python
ratio_buy5min_33221 = w_buy_33221 / w_vol_33221
```

**加權邏輯表格**：

| 時間區間 | 權重 | 說明 |
|---------|------|------|
| 0 ~ 1 分鐘 | **3/11** (0.273) | 最近資料 |
| 1 ~ 2 分鐘 | **3/11** (0.273) | 次近資料 |
| 2 ~ 3 分鐘 | **2/11** (0.182) | 中期資料 |
| 3 ~ 4 分鐘 | **2/11** (0.182) | 中期資料 |
| 4 ~ 5 分鐘 | **1/11** (0.091) | 遠期資料，權重最低 |

**說明**：
- 分子：加權買盤成交量
- 分母：加權總成交量
- 數值範圍：0 ~ 1
- 越高表示買盤越強

**用途**：
- 觸發條件，時段依賴：
  - 09:05~09:20: > 0.7
  - 09:20~10:00: > 0.75
  - 10:00以後: > 0.8

---

### 5.7 ratio_buy5min（5分鐘買盤比例，不加權版本）

**計算方法**：

```python
# 1. 計算 5 分鐘買盤累積量
vol_buy_5m = vol_buy.rolling_sum_by('adj_datetime', '5m')

# 2. 計算 5 分鐘總成交量
Volume_5m = Volume.rolling_sum_by('adj_datetime', '5m')

# 3. 計算 ratio
ratio_buy5min = vol_buy_5m / Volume_5m
```

**說明**：
- 分子：5 分鐘買盤成交量（等權重）
- 分母：5 分鐘總成交量（等權重）
- 數值範圍：0 ~ 1
- **無加權**，所有時間段等權重

**與加權版本的差異**：

| 項目 | 不加權版本 (ratio_buy5min) | 加權版本 (ratio_buy5min_33221) |
|------|--------------------------|-------------------------------|
| 計算方式 | 等權重平均 | 33221 加權 |
| 穩定性 | **更穩定** | 較敏感 |
| 反應速度 | 較慢 | **更快** |
| 使用時段 | 10:00~12:00 | 其他時段 |

**用途**：
- 出場條件：< 0.48（僅在 10:00~12:00 使用）
- 盤中時段波動較大，不加權版本更穩定

---

### 5.8 ratio_10s_30s（10秒/30秒買盤比）

**計算方法**：

```python
# 1. 計算 10 秒買盤累積量
vol_buy_10s = vol_buy.rolling_sum_by('adj_datetime', '10s')

# 2. 計算 30 秒買盤累積量
vol_buy_30s = vol_buy.rolling_sum_by('adj_datetime', '30s')

# 3. 計算 ratio（等價於 10s×3 / 30s）
ratio_10s_30s = (vol_buy_10s × 3) / vol_buy_30s
```

**說明**：
- 分子：10 秒買盤量 × 3 = 30 秒買盤量（假設均勻分布）
- 分母：30 秒買盤量（原始總和）
- 無加權，等權重

**用途**：
- **力竭判斷指標**
- 動態力竭閾值 = 觸發時的 ratio_10s_30s ÷ 3
- 當 ratio_10s_30s < 閾值時，判定為力竭

---

### 5.9 ratio_15s_60s（15秒/60秒買盤比）

**計算方法**：

```python
# 1. 計算 15 秒買盤累積量
vol_buy_15s = vol_buy.rolling_sum_by('adj_datetime', '15s')

# 2. 計算 60 秒買盤累積量
vol_buy_60s = vol_buy.rolling_sum_by('adj_datetime', '60s')

# 3. 計算 ratio（等價於 15s×4 / 60s）
ratio_15s_60s = (vol_buy_15s × 4) / vol_buy_60s
```

**說明**：
- 分子：15 秒買盤量 × 4 = 60 秒買盤量（假設均勻分布）
- 分母：60 秒買盤量（原始總和）
- 無加權，等權重

**用途**：
- 輔助觀察指標
- 目前策略中未直接使用

---

### 5.10 特徵暖身期 (Warmup Period)

所有滾動特徵在計算初期資料不足時，會設為 **0**。

#### 暖身期設定

| 特徵 | 暖身期 | 說明 |
|------|--------|------|
| `ratio_15s_180s` | 180 秒 | 需要 3 分鐘資料 |
| `ratio_15s_180s_w321` | 180 秒 | 需要 3 分鐘資料 |
| `ratio_buy5min_54321` | 5 分鐘 | 需要 5 分鐘資料 |
| `ratio_buy5min_33221` | 5 分鐘 | 需要 5 分鐘資料 |
| `ratio_buy5min` | 5 分鐘 | 需要 5 分鐘資料 |
| `ratio_15s_60s` | 60 秒 | 需要 1 分鐘資料 |
| `ratio_10s_30s` | 30 秒 | 需要 30 秒資料 |

**暖身邏輯**：
```python
if elapsed_time < warmup_period:
    feature_value = 0
else:
    feature_value = calculated_value
```

**說明**：
- `elapsed_time` = 當前時間 - 開盤時間（基於 adj_datetime）
- 確保特徵值在資料充足後才有意義
- 避免初期資料不足導致的異常值

---

### 5.11 特徵計算流程總結

```
原始資料 (Datetime, Price, Volume, tick_type)
  ↓
時間縫合 (Time Stitching)
  → adj_datetime = Datetime - halt_adjustment.cumsum()
  ↓
分類買賣盤
  → vol_buy, vol_sell
  ↓
計算 VWAP
  → vwap = cumsum(Price × Volume) / cumsum(Volume)
  ↓
滾動窗口計算（基於 adj_datetime）
  → Rolling High/Low (2m, 3m, 5m, 10m, 15m)
  → Rolling Sums (10s, 15s, 30s, 60s, 180s, 5m)
  ↓
加權特徵計算
  → ratio_15s_180s (無加權)
  → ratio_15s_180s_w321 (321 加權)
  → ratio_buy5min (無加權)
  → ratio_buy5min_33221 (33221 加權)
  → ratio_10s_30s (無加權)
  → ratio_15s_60s (無加權)
  ↓
暖身期過濾
  → 資料不足時設為 0
  ↓
最終特徵輸出
```

---

## 六、關鍵指標說明

### 6.1 high_2m（2分鐘高點）

- **定義**：過去2分鐘的最高價
- **計算方法**：詳見第五章 5.1 節
- **用途**：觸發條件之一
- **意義**：突破2分鐘高點表示價格處於上升趨勢

### 6.2 ratio_buy5min_33221（5分鐘買盤比例，加權）

- **計算方法**：詳見第五章 5.6 節
- **加權方式**：33221（3/11, 3/11, 2/11, 2/11, 1/11）
- **數值範圍**：0 ~ 1
- **用途**：觸發條件，時段依賴（0.7/0.75/0.8）
- **意義**：衡量買盤強度

### 6.3 ratio_15s_180s_w321（15秒/180秒買盤比，加權）

- **計算方法**：詳見第五章 5.5 節
- **加權方式**：321（3/6, 2/6, 1/6）
- **用途**：
  - 觸發階段：> 6.0 表示短期爆量
  - 出場階段：> 7.0 表示空單回補
- **意義**：衡量短期買盤相對於中期的強弱

### 6.4 ratio_10s_30s（10秒/30秒買盤比）

- **計算方法**：詳見第五章 5.8 節
- **公式**：(10秒買盤 × 3) / 30秒買盤
- **用途**：力竭判斷指標
- **力竭閾值**：觸發時的 ratio_10s_30s ÷ 3
- **意義**：短期買盤快速衰退

### 6.5 ratio_buy5min（5分鐘買盤比例，不加權）

- **計算方法**：詳見第五章 5.7 節
- **公式**：5分鐘買盤 / 5分鐘總量
- **用途**：10:00~12:00 時段的停利判斷
- **閾值**：< 0.48
- **原因**：盤中時段波動較大，不加權版本更穩定

### 6.6 low_5m / low_10m / low_15m

- **定義**：5/10/15分鐘的滾動最低價
- **計算方法**：詳見第五章 5.1 節
- **用途**：停利出場的破低參考點
- **重要**：使用進場時的值，不是動態更新

### 6.7 VWAP（成交量加權平均價）

- **計算方法**：詳見第五章 5.2 節
- **公式**：cumsum(Price × Volume) / cumsum(Volume)
- **用途**：進場條件，09:45後檢查乖離
- **意義**：衡量平均成交價格

---

## 七、參數總覽

### 觸發階段參數

| 參數名稱 | 預設值 | 說明 |
|---------|--------|------|
| `ratio_15s_180s_threshold` | 6.0 | 爆量閾值 |
| `filter_start_time` | '09:05:00' | 開始偵測時間 |
| `cooldown_seconds` | 30.0 | 冷卻時間（秒） |

**時段依賴閾值（ratio_buy5min_33221）**：

| 時段 | 閾值 | 說明 |
|------|------|------|
| 09:05~09:20 | 0.7 | 早盤 |
| 09:20~10:00 | 0.75 | 盤中過渡 |
| 10:00以後 | 0.8 | 盤中穩定 |

### 進場階段參數

| 參數名稱 | 一般值 | 開盤強勢值 | 說明 |
|---------|--------|-----------|------|
| `exhaustion_divisor` | 3.0 | 3.0 | 力竭閾值除數 |
| `min_pullback_pct` | 0.2 | **0.6** | 最小回檔 (%) |
| `max_pullback_pct` | 0.6 | **2.0** | 最大回檔 (%) |
| `window_seconds_early` | 15.0 | 15.0 | 09:05~09:20 窗口（秒） |
| `window_seconds_mid` | 30.0 | 30.0 | 09:20~10:00 窗口（秒） |
| `window_seconds_late` | 45.0 | 45.0 | 10:00後 窗口（秒） |
| `vwap_divergence_threshold` | 1.5 | 1.5 | VWAP 乖離閾值 (%) |
| `vwap_check_start_time` | '09:45:00' | '09:45:00' | VWAP 檢查啟用時間 |

**開盤強勢策略觸發**：
- 條件：`open_gap_pct > 6.0`

### 出場階段參數

| 參數名稱 | 預設值 | 說明 |
|---------|--------|------|
| `stop_loss_pct` | 0.8 | 停損幅度 (%) |
| `ratio_threshold` | 10.0 | ratio_15s_180s 回補閾值（建議7.0） |
| `buy5min_threshold` | 0.48 | ratio_buy5min 停利閾值 |

---

## 八、風險管理

### 8.1 單筆交易風險

- **最大虧損**：0.8%（停損）
- **期望獲利**：依破低幅度而定，通常 1% up

### 8.2 訊號過濾機制

1. **時間過濾**：避免開盤異常（09:05 前不觸發）
2. **冷卻機制**：避免重複進場（30秒間隔）
3. **回檔過濾**：避免追價（0.2% ~ 0.6%）
4. **VWAP 過濾**：避免追高（09:45 後 < 1.5%）
5. **時段動態**：不同時段使用不同參數

### 8.3 出場保護

1. **停損優先**：確保虧損可控
2. **破低確認**：等待價格確實下跌
3. **雙重條件**：量能回補 OR 買盤力竭
4. **時間分段**：10:00~12:00 使用更穩健的指標

---

## 九、實際應用範例

### 範例 1：完整交易流程

```
09:10:30 - 觸發訊號
  ├─ 價格：100.5（創2分鐘新高）
  ├─ ratio_buy5min_33221：0.72（> 0.7，09:05~09:20）
  ├─ ratio_15s_180s_w321：6.8（> 6.0）
  └─ ratio_10s_30s：0.85

09:10:35 - 力竭確認（15秒窗口內）
  ├─ ratio_10s_30s：0.27（< 0.85÷3 = 0.283）
  └─ 力竭成立

09:10:36 - 進場檢查
  ├─ 價格：100.3
  ├─ 參考高點（high_2m）：100.6
  ├─ 回檔：(100.6 - 100.3) / 100.6 = 0.30%
  ├─ 判斷：0.2% ≤ 0.30% ≤ 0.6% ✅
  ├─ VWAP：100.1
  ├─ 價格 > VWAP，但 < 09:45 → 通過 ✅
  └─ 進場價：100.3

09:10:36 - 做空進場
  ├─ 進場價：100.3
  ├─ 停損價：100.3 × 1.008 = 101.1
  ├─ 5m低點：99.8
  ├─ 10m低點：99.5
  └─ 15m低點：99.2

09:12:15 - 價格破5分鐘低點
  └─ 價格：99.7（< 99.8）

09:12:20 - 回補訊號出現
  ├─ ratio_15s_180s：7.5（> 7.0）
  └─ 出場價：99.6

結果：獲利 0.70% = (100.3 - 99.6) / 100.3 × 100
```

### 範例 2：停損出場

```
09:15:00 - 進場
  └─ 進場價：200.0

09:15:30 - 價格反彈
  ├─ 價格：201.7（≥ 200.0 × 1.008 = 201.6）
  └─ 觸發停損

09:15:30 - 停損出場
  └─ 停損價：201.7

結果：虧損 0.85% = (201.7 - 200.0) / 200.0 × 100
```

### 範例 3：開盤強勢策略

```
開盤檢測
  ├─ 前收：50.0
  ├─ 開盤：53.5
  └─ 漲幅：(53.5 - 50.0) / 50.0 = 7.0% > 6% ✅

策略調整
  ├─ min_pullback_pct: 0.2% → 0.6%
  └─ max_pullback_pct: 0.6% → 2.0%

09:08:00 - 觸發訊號
  ├─ 價格：54.0
  └─ 符合觸發條件

09:08:05 - 力竭確認
  └─ ratio_10s_30s 衰退至閾值以下

09:08:06 - 進場檢查
  ├─ 價格：53.2
  ├─ 參考高點：54.0
  ├─ 回檔：(54.0 - 53.2) / 54.0 = 1.48%
  └─ 判斷：0.6% ≤ 1.48% ≤ 2.0% ✅

進場成功（若使用一般參數，此訊號會被過濾）
```

---

## 九、策略特點總結

### 優勢

1. **多層過濾機制**：減少假訊號
2. **時段動態調整**：適應不同時段的市場特性
3. **動態力竭閾值**：根據觸發強度自動調整
4. **風險可控**：固定停損 0.8%
5. **量化規則**：無主觀判斷，可回測驗證

### 適用場景

- **盤中短線**：09:05 ~ 收盤
- **高波動股票**：需要足夠的成交量和價格波動
- **趨勢反轉**：捕捉爆量後的力竭回檔

### 注意事項

1. **滑價風險**：實際成交價可能與訊號價格有差異
2. **極端行情**：連續漲停可能無法停損
3. **參數優化**：需根據不同股票特性調整參數
4. **交易成本**：需考慮手續費和交易稅
5. **開盤強勢策略**：
   - 僅在開盤漲幅 > 6% 時自動啟用
   - 允許更大回檔，需要更謹慎的風險管理
   - 建議適當調整停損參數
6. **ratio_threshold 調整**：
   - 代碼預設 10.0，但實際圖表使用 7.0
   - 建議根據回測結果調整此參數

---

## 十、程式碼結構

### 主要類別

1. **TriggerDetector**（plot_entrier.py）
   - 負責觸發訊號偵測
   - 輸出：TriggerSignal 物件

2. **Entrier**（plot_entrier.py）
   - 負責進場訊號產生
   - 輸出：EntrySignal 物件

3. **StopLossDetector**（plot_exiter.py）
   - 負責停損訊號偵測
   - 輸出：StopLossSignal 物件

4. **ExitDetector**（plot_exiter.py）
   - 負責停利訊號偵測
   - 輸出：ExitSignal 物件

### 資料流

```
Tick Data (Parquet)
  ↓
TriggerDetector.detect()
  ↓
TriggerSignal List
  ↓
Entrier.generate()
  ↓
EntrySignal List
  ↓
┌─────────────────┬─────────────────┐
│                 │                 │
StopLossDetector  ExitDetector
│                 │
StopLoss Signals  Exit Signals
│                 │
└─────────────────┴─────────────────┘
  ↓
plot_exiter_signals()
  ↓
視覺化圖表 (HTML)
```

---

## 結語

本策略是一個**系統化的短線做空策略**，透過量價突破與力竭反轉的原理，捕捉市場的短期反轉機會。關鍵在於：

1. **嚴格的觸發條件**：確保訊號品質（價格突破 + 買盤強度 + 爆量）
2. **動態的力竭判斷**：根據觸發強度自動調整閾值
3. **時段動態調整**：不同時段使用不同參數
4. **耐心的進場等待**：等待力竭確認和合理回檔
5. **靈活的出場機制**：停損保護 + 破低停利

透過回測和參數優化，可以進一步提升策略的穩定性和獲利能力。

**重要提醒**：
- 本文檔基於 `plot_entrier.py` 和 `plot_exiter.py` 的實際代碼邏輯撰寫
- 所有參數和條件都來自於實際代碼
- 建議在修改代碼後同步更新本文檔
