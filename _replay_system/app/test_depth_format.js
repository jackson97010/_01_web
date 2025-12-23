const fs = require('fs');
const path = require('path');

// 讀取 JSON 檔案的前幾筆 Depth 資料
const jsonPath = 'C:\\Users\\User\\Documents\\HFT\\_replay_system\\3060_1219.json';

console.log('檢查 JSON 檔案中的 Depth 資料格式...\n');

try {
  const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));

  // 找出前 3 筆 Depth 資料
  const depthRows = data.filter(row => row.Type === 'Depth').slice(0, 3);

  console.log(`總共有 ${data.length} 筆資料`);
  console.log(`其中 Depth 資料有 ${data.filter(row => row.Type === 'Depth').length} 筆`);
  console.log(`其中 Trade 資料有 ${data.filter(row => row.Type === 'Trade').length} 筆\n`);

  if (depthRows.length > 0) {
    console.log('=== 第一筆 Depth 資料 ===');
    const firstDepth = depthRows[0];
    console.log('完整資料:', JSON.stringify(firstDepth, null, 2));

    console.log('\n=== 五檔價格檢查 ===');
    for (let i = 1; i <= 5; i++) {
      const bidPrice = firstDepth[`Bid${i}_Price`];
      const bidVol = firstDepth[`Bid${i}_Volume`];
      const askPrice = firstDepth[`Ask${i}_Price`];
      const askVol = firstDepth[`Ask${i}_Volume`];

      console.log(`第 ${i} 檔:`);
      console.log(`  Bid: ${bidPrice} x ${bidVol}`);
      console.log(`  Ask: ${askPrice} x ${askVol}`);
    }

    console.log('\n=== 資料類型檢查 ===');
    console.log('Type:', typeof firstDepth.Type, '=', firstDepth.Type);
    console.log('Timestamp:', typeof firstDepth.Timestamp, '=', firstDepth.Timestamp);
    console.log('Bid1_Price:', typeof firstDepth.Bid1_Price, '=', firstDepth.Bid1_Price);
    console.log('Bid1_Volume:', typeof firstDepth.Bid1_Volume, '=', firstDepth.Bid1_Volume);

    // 檢查是否有 null 或 NaN
    console.log('\n=== 檢查 null/NaN 值 ===');
    const hasNull = Object.entries(firstDepth).some(([key, val]) => val === null);
    const hasNaN = Object.entries(firstDepth).some(([key, val]) => typeof val === 'number' && isNaN(val));
    const hasUndefined = Object.entries(firstDepth).some(([key, val]) => val === undefined);

    console.log('包含 null:', hasNull);
    console.log('包含 NaN:', hasNaN);
    console.log('包含 undefined:', hasUndefined);

    // 檢查關鍵欄位
    console.log('\n=== 關鍵欄位檢查 ===');
    const requiredFields = ['Type', 'Timestamp', 'Datetime', 'Bid1_Price', 'Ask1_Price'];
    requiredFields.forEach(field => {
      const value = firstDepth[field];
      console.log(`${field}: ${value === null ? 'null' : value === undefined ? 'undefined' : value}`);
    });

  } else {
    console.log('沒有找到 Depth 資料！');
  }

} catch (error) {
  console.error('錯誤:', error.message);
}