# 性能優化指南

## 當前性能優化

### ✅ 已實現的優化

1. **React.memo** - 避免不必要的重渲染
2. **降採樣** - 超過 5000 點自動降採樣
3. **ECharts lazy update** - 延遲更新圖表
4. **快速播放** - 20ms 間隔更新

### 📊 性能瓶頸分析

主要性能瓶頸：
1. **數據處理** - Parquet 解析和數據轉換
2. **React 渲染** - 大量數據時的 DOM 更新
3. **圖表繪製** - ECharts 渲染大量數據點

---

## 🚀 進階優化方案

### 方案 1：Web Worker（推薦，易實現）

**優點：**
- ✅ 不阻塞主線程
- ✅ 純 JavaScript，容易整合
- ✅ 可以並行處理多個數據源

**實現步驟：**

1. 安裝 Worker 插件：
```bash
npm install --save-dev vite-plugin-worker
```

2. 配置 Vite（`vite.config.ts`）：
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
  plugins: [
    react(),
  ],
  worker: {
    format: 'es'
  },
  // ... 其他配置
});
```

3. 使用 Worker（已創建 `src/workers/dataProcessor.worker.ts`）

**預期提升：** 30-50% 數據處理速度提升

---

### 方案 2：Rust + Neon（高性能，需要編譯）

**優點：**
- ✅ 極高性能（比 JS 快 10-100 倍）
- ✅ 類型安全
- ✅ 適合大量數值計算

**實現步驟：**

1. 安裝 Neon：
```bash
npm install --save-dev @neon-rs/cli
npx neon new native
```

2. Rust 代碼示例（`native/src/lib.rs`）：
```rust
use neon::prelude::*;

// 高性能數據處理
fn process_parquet_data(mut cx: FunctionContext) -> JsResult<JsArray> {
    let data = cx.argument::<JsArray>(0)?;
    let len = data.len(&mut cx);

    // 使用 Rust 的高性能迭代器處理數據
    let result = JsArray::new(&mut cx, len);

    // ... 數據處理邏輯

    Ok(result)
}

#[neon::main]
fn main(mut cx: ModuleContext) -> NeonResult<()> {
    cx.export_function("processParquetData", process_parquet_data)?;
    Ok(())
}
```

3. 在 JavaScript 中使用：
```typescript
import { processParquetData } from './native';

const processedData = processParquetData(rawData);
```

**預期提升：** 10-100 倍數據處理速度

**缺點：**
- 需要 Rust 工具鏈
- 跨平台編譯較複雜
- 開發周期較長

---

### 方案 3：WebAssembly (WASM)

**優點：**
- ✅ 接近原生性能
- ✅ 可以用 C++/Rust 編寫
- ✅ 瀏覽器原生支持

**實現步驟：**

1. 使用 Rust + wasm-pack：
```bash
cargo install wasm-pack
wasm-pack new data-processor
```

2. Rust 代碼（`src/lib.rs`）：
```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct DataProcessor {
    data: Vec<f64>,
}

#[wasm_bindgen]
impl DataProcessor {
    #[wasm_bindgen(constructor)]
    pub fn new() -> DataProcessor {
        DataProcessor { data: Vec::new() }
    }

    pub fn process(&mut self, input: &[f64]) -> Vec<f64> {
        // 高性能數據處理
        input.iter().map(|x| x * 2.0).collect()
    }
}
```

3. 編譯並使用：
```bash
wasm-pack build --target web
```

```typescript
import init, { DataProcessor } from './data-processor/pkg';

await init();
const processor = new DataProcessor();
const result = processor.process(data);
```

**預期提升：** 5-50 倍

---

### 方案 4：SQLite + 索引（適合大數據）

**優點：**
- ✅ 適合海量數據
- ✅ 高效查詢
- ✅ 支持複雜過濾

**實現步驟：**

1. 安裝 better-sqlite3：
```bash
npm install better-sqlite3
npm install --save-dev @types/better-sqlite3
```

2. 創建數據庫（`electron/database.js`）：
```javascript
const Database = require('better-sqlite3');
const db = new Database('market_data.db');

// 創建表和索引
db.exec(`
  CREATE TABLE IF NOT EXISTS ticks (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    price REAL,
    volume INTEGER,
    bs_flag TEXT
  );
  CREATE INDEX idx_timestamp ON ticks(timestamp);
  CREATE INDEX idx_type ON ticks(type);
`);

// 批量插入
const insert = db.prepare(`
  INSERT INTO ticks (timestamp, type, price, volume, bs_flag)
  VALUES (?, ?, ?, ?, ?)
`);

const insertMany = db.transaction((ticks) => {
  for (const tick of ticks) {
    insert.run(tick.timestamp, tick.type, tick.price, tick.volume, tick.bs_flag);
  }
});

// 高效查詢
const query = db.prepare(`
  SELECT * FROM ticks
  WHERE timestamp BETWEEN ? AND ?
  ORDER BY timestamp
`);
```

**預期提升：** 大數據場景下查詢速度提升 100+ 倍

---

### 方案 5：優化 Parquet 讀取

**使用流式讀取：**

```javascript
// electron/main.js
async function readParquetStreaming(filePath) {
  const parquet = await import('parquetjs-lite');
  const reader = await parquet.ParquetReader.openFile(filePath);

  // 分批讀取，避免一次性載入所有數據
  const batchSize = 10000;
  const batches = [];

  for (let i = 0; i < reader.getRowCount(); i += batchSize) {
    const batch = await reader.read(batchSize);
    batches.push(batch);

    // 可以在這裡發送進度事件
    mainWindow.webContents.send('load-progress', {
      current: i,
      total: reader.getRowCount()
    });
  }

  await reader.close();
  return batches.flat();
}
```

---

## 🎯 推薦實施順序

### 階段 1：立即可做（1-2 小時）
1. ✅ 調整降採樣閾值（已完成）
2. ✅ 優化播放速度（已完成）
3. 🔄 實施 Parquet 流式讀取
4. 🔄 添加載入進度條

### 階段 2：短期優化（1-2 天）
1. 🔄 實施 Web Worker
2. 🔄 優化 React 組件渲染
3. 🔄 添加虛擬滾動

### 階段 3：中期優化（1 週）
1. 🔄 實施 SQLite 緩存
2. 🔄 添加數據預加載
3. 🔄 優化內存管理

### 階段 4：長期優化（2-4 週）
1. 🔄 Rust + Neon 重寫核心邏輯
2. 🔄 WebAssembly 編譯關鍵算法
3. 🔄 多線程處理

---

## 📈 性能測試

### 測試場景
- 小文件：< 10MB，< 10萬筆
- 中文件：10-100MB，10-100萬筆
- 大文件：> 100MB，> 100萬筆

### 當前性能（未優化）
| 場景 | 載入時間 | 播放流暢度 |
|------|---------|-----------|
| 小文件 | ~1s | ✅ 流暢 |
| 中文件 | ~5s | ⚠️ 輕微卡頓 |
| 大文件 | ~15s | ❌ 明顯卡頓 |

### 預期性能（使用 Web Worker）
| 場景 | 載入時間 | 播放流暢度 |
|------|---------|-----------|
| 小文件 | ~0.5s | ✅ 流暢 |
| 中文件 | ~2s | ✅ 流暢 |
| 大文件 | ~6s | ✅ 基本流暢 |

### 預期性能（使用 Rust）
| 場景 | 載入時間 | 播放流暢度 |
|------|---------|-----------|
| 小文件 | ~0.1s | ✅ 流暢 |
| 中文件 | ~0.5s | ✅ 流暢 |
| 大文件 | ~2s | ✅ 流暢 |

---

## 💡 其他優化建議

### 1. 使用虛擬化列表
對於五檔報價，如果要顯示歷史記錄，使用 react-window：

```typescript
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={items.length}
  itemSize={35}
  width="100%"
>
  {Row}
</FixedSizeList>
```

### 2. 使用 IndexedDB 緩存
```typescript
// 緩存處理後的數據
const dbRequest = indexedDB.open('MarketDataCache', 1);

dbRequest.onsuccess = () => {
  const db = dbRequest.result;
  const tx = db.transaction('data', 'readwrite');
  const store = tx.objectStore('data');
  store.put({ id: filePath, data: processedData });
};
```

### 3. 使用 Canvas 替代 DOM
對於高頻更新的數據顯示，可以使用 Canvas：

```typescript
const canvas = useRef<HTMLCanvasElement>(null);

useEffect(() => {
  const ctx = canvas.current?.getContext('2d');
  if (!ctx) return;

  // 直接在 Canvas 上繪製，避免 DOM 操作
  ctx.fillStyle = '#1890ff';
  ctx.fillRect(0, 0, 100, 50);
}, [data]);
```

---

## 🛠️ 快速開始

### 最快見效的優化（5 分鐘）

1. 調整降採樣閾值：
```typescript
// src/components/PriceChart.tsx:40
const maxPoints = 3000; // 從 5000 改為 3000
```

2. 調整播放速度：
```typescript
// src/App.tsx:149
}, 10); // 從 20 改為 10，更快
```

3. 禁用開發者工具（生產環境）：
```javascript
// electron/main.js:62
// mainWindow.webContents.openDevTools({ mode: 'detach' }); // 註釋掉
```

---

## 📞 需要幫助？

如果需要實施任何優化方案，請告訴我：
1. 你的數據文件大小範圍
2. 可接受的載入時間
3. 是否願意使用 Rust/C++
4. 開發時間預算

我會為你提供最合適的優化方案！
