// Preload runs in a non-ESM context; use CommonJS to avoid "Cannot use import statement" errors.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  pickFile: () => ipcRenderer.invoke('dialog:openFile'),
  loadFile: (filePath) => ipcRenderer.invoke('file:load', filePath),

  // 即時資料流 API
  startLiveStream: (stockId) => ipcRenderer.invoke('live:start', stockId),
  stopLiveStream: () => ipcRenderer.invoke('live:stop'),
  getLiveStreamStatus: () => ipcRenderer.invoke('live:status'),
  getAvailableStocks: () => ipcRenderer.invoke('live:getStocks'),

  // 監聽即時市場資料更新
  onMarketDataUpdate: (callback) => {
    const listener = (_event, data) => callback(data);
    ipcRenderer.on('market-data-update', listener);

    // 返回取消訂閱的函數
    return () => {
      ipcRenderer.removeListener('market-data-update', listener);
    };
  }
});
