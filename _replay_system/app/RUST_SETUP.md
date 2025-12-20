# Rust + Neon 設置指南

## 第一步：安裝 Rust

### Windows 安裝步驟

1. **下載 Rust 安裝器**
   - 訪問：https://rustup.rs/
   - 或直接下載：https://win.rustup.rs/x86_64

2. **運行安裝器**
   ```cmd
   # 下載後執行 rustup-init.exe
   # 選擇 1) Proceed with installation (default)
   ```

3. **驗證安裝**
   ```cmd
   rustc --version
   cargo --version
   ```

   應該看到類似輸出：
   ```
   rustc 1.75.0 (82e1608df 2023-12-21)
   cargo 1.75.0 (1d8b05cdd 2023-11-20)
   ```

4. **安裝 Visual Studio Build Tools**（如果還沒有）
   - 下載：https://visualstudio.microsoft.com/downloads/
   - 選擇 "Build Tools for Visual Studio 2022"
   - 安裝時勾選 "Desktop development with C++"

---

## 第二步：安裝 Neon CLI

```bash
npm install -g @neon-rs/cli
```

驗證安裝：
```bash
neon --version
```

---

## 第三步：創建 Neon 模塊

在專案根目錄執行：

```bash
cd C:\Users\User\Documents\HFT\_replay_system\app
neon new native
```

這會創建一個 `native` 目錄，包含：
```
native/
├── Cargo.toml          # Rust 項目配置
├── src/
│   └── lib.rs         # Rust 源代碼
├── package.json       # Node.js 綁定
└── index.node         # 編譯後的二進制文件
```

---

## 第四步：構建 Rust 模塊

```bash
cd native
npm install
npm run build
```

成功後會生成 `index.node` 文件。

---

## 第五步：在項目中使用

```javascript
// 在 electron/main.js 中
const native = require('../native');

// 使用 Rust 函數
const result = native.processParquetData(data);
```

---

## 故障排除

### 問題 1：找不到 MSVC

**錯誤信息：**
```
error: linker `link.exe` not found
```

**解決方案：**
安裝 Visual Studio Build Tools（見第一步）

---

### 問題 2：Rust 編譯失敗

**解決方案：**
```bash
# 更新 Rust
rustup update

# 清理並重新構建
cargo clean
npm run build
```

---

### 問題 3：Node 版本不兼容

**解決方案：**
確保使用 Node.js 18+ 版本
```bash
node --version  # 應該 >= 18.0.0
```

---

## 下一步

安裝完成後，查看 `RUST_INTEGRATION.md` 了解如何集成到應用中。
