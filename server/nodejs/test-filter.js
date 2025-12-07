// 測試過濾邏輯
const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '../../frontend/static/api/20251031/1503.json');
const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));

console.log('原始資料統計：');
console.log('  Chart timestamps:', data.chart.timestamps.length);
console.log('  Trades:', data.trades.length);
console.log('  第一個 chart 時間:', data.chart.timestamps[0]);
console.log('  最後一個 chart 時間:', data.chart.timestamps[data.chart.timestamps.length - 1]);

// 過濾邏輯
const filterTime = (timeStr) => {
  const timePart = timeStr.split(' ')[1];
  if (!timePart) return false;
  const hour = parseInt(timePart.split(':')[0]);
  return hour >= 9;
};

// 過濾 chart
const validIndices = [];
data.chart.timestamps.forEach((timestamp, index) => {
  if (filterTime(timestamp)) {
    validIndices.push(index);
  }
});

console.log('\n過濾後統計：');
console.log('  有效的 chart 數據點:', validIndices.length);
if (validIndices.length > 0) {
  console.log('  第一個有效時間:', data.chart.timestamps[validIndices[0]]);
  console.log('  最後一個有效時間:', data.chart.timestamps[validIndices[validIndices.length - 1]]);
}

// 過濾 trades
const filteredTrades = data.trades.filter(trade =>
  trade.flag === 0 && filterTime(trade.time)
);

console.log('  過濾後 trades:', filteredTrades.length);
if (filteredTrades.length > 0) {
  console.log('  第一個 trade 時間:', filteredTrades[0].time);
  console.log('  最後一個 trade 時間:', filteredTrades[filteredTrades.length - 1].time);
}
