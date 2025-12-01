const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  loadConfig: () => ipcRenderer.invoke('load-config'),
  saveConfig: (config) => ipcRenderer.invoke('save-config', config),
  browseFolder: () => ipcRenderer.invoke('browse-folder'),
  testConnection: (token) => ipcRenderer.invoke('test-connection', token),
  getStatistics: (sourceDir) => ipcRenderer.invoke('get-statistics', sourceDir),
  startImport: (config) => ipcRenderer.invoke('start-import', config),
  retryFailed: () => ipcRenderer.invoke('retry-failed'),
  cleanupOldFailures: () => ipcRenderer.invoke('cleanup-old-failures'),
  stopImport: () => ipcRenderer.invoke('stop-import'),
  onImportLog: (callback) => ipcRenderer.on('import-log', (event, data) => callback(data))
});
