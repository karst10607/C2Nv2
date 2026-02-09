const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  loadConfig: () => ipcRenderer.invoke('load-config'),
  saveConfig: (config) => ipcRenderer.invoke('save-config', config),
  browseFolder: () => ipcRenderer.invoke('browse-folder'),
  browseSaveFolder: () => ipcRenderer.invoke('browse-save-folder'),
  browseFile: (options) => ipcRenderer.invoke('browse-file', options),
  testConnection: (token) => ipcRenderer.invoke('test-connection', token),
  getStatistics: (sourceDir) => ipcRenderer.invoke('get-statistics', sourceDir),
  exportStatistics: (sourceDir, format) => ipcRenderer.invoke('export-statistics', sourceDir, format),
  startImport: (config) => ipcRenderer.invoke('start-import', config),
  exportMarkdown: (config) => ipcRenderer.invoke('export-markdown', config),
  retryFailed: () => ipcRenderer.invoke('retry-failed'),
  cleanupOldFailures: () => ipcRenderer.invoke('cleanup-old-failures'),
  stopImport: () => ipcRenderer.invoke('stop-import'),
  onImportLog: (callback) => ipcRenderer.on('import-log', (event, data) => callback(data)),
  getParsingErrors: (options) => ipcRenderer.invoke('get-parsing-errors', options),
  // Attachment analyzer
  analyzeAttachments: (sourceDir) => ipcRenderer.invoke('analyze-attachments', sourceDir),
  convertVideosToMp3: (config) => ipcRenderer.invoke('convert-videos-to-mp3', config),
  deleteAttachment: (filePath) => ipcRenderer.invoke('delete-attachment', filePath)
});
