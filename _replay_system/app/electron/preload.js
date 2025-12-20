// Preload runs in a non-ESM context; use CommonJS to avoid "Cannot use import statement" errors.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  pickFile: () => ipcRenderer.invoke('dialog:openFile'),
  loadFile: (filePath) => ipcRenderer.invoke('file:load', filePath)
});
