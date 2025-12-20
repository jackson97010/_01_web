import fs from 'fs';
import path from 'path';

// 載入測試數據
const filePath = 'C:\\Users\\User\\Documents\\HFT\\_replay_system\\3060_1219.json';
console.log('載入檔案:', filePath);

// 讀取並處理 NaN 值
let raw = fs.readFileSync(filePath, 'utf-8');
raw = raw.replace(/:\s*NaN\s*([,\}])/g, ': null$1');
raw = raw.replace(/:\s*Infinity\s*([,\}])/g, ': null$1');
raw = raw.replace(/:\s*-Infinity\s*([,\}])/g, ': null$1');

const data = JSON.parse(raw);
console.log(`總共 ${data.length} 筆數據\n`);

// 找出前 10 筆 Depth 數據
const depths = data.filter(item => item.Type === 'Depth').slice(0, 10);

console.log('前 10 筆五檔數據:');
depths.forEach((depth, i) => {
  console.log(`\n第 ${i + 1} 筆:`);
  console.log(`  時間: ${depth.Datetime}`);
  console.log(`  Timestamp: ${depth.Timestamp}`);
  console.log(`  買一: ${depth.Bid1_Price} @ ${depth.Bid1_Volume}`);
  console.log(`  賣一: ${depth.Ask1_Price} @ ${depth.Ask1_Volume}`);

  // 檢查是否有任何 undefined 或 null
  if (depth.Bid1_Price === undefined || depth.Bid1_Price === null) {
    console.log('  ⚠️  買一價格為 undefined 或 null');
  }
  if (depth.Ask1_Price === undefined || depth.Ask1_Price === null) {
    console.log('  ⚠️  賣一價格為 undefined 或 null');
  }
});

// 統計有多少筆 Depth 數據
const depthCount = data.filter(item => item.Type === 'Depth').length;
const tradeCount = data.filter(item => item.Type === 'Trade').length;

console.log(`\n統計:`);
console.log(`  Depth 數據: ${depthCount} 筆`);
console.log(`  Trade 數據: ${tradeCount} 筆`);

// 檢查是否有無效數據
const invalidDepths = data.filter(item =>
  item.Type === 'Depth' &&
  (!item.Bid1_Price || !item.Ask1_Price)
);

if (invalidDepths.length > 0) {
  console.log(`\n⚠️  發現 ${invalidDepths.length} 筆無效的五檔數據（缺少買一或賣一價格）`);
}