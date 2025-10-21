const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  loadConfig: () => ipcRenderer.invoke('load-config'),
  saveConfig: (config) => ipcRenderer.invoke('save-config', config),
  browseFolder: () => ipcRenderer.invoke('browse-folder'),
  testConnection: (token) => ipcRenderer.invoke('test-connection', token),
  startImport: (config, dryRun) => ipcRenderer.invoke('start-import', config, dryRun),
  retryFailed: () => ipcRenderer.invoke('retry-failed'),
  stopImport: () => ipcRenderer.invoke('stop-import'),
  onImportLog: (callback) => ipcRenderer.on('import-log', (event, data) => callback(data))
});
