const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const os = require('os');

const CONFIG_DIR = path.join(os.homedir(), '.notion_importer');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

let mainWindow;
let importProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'icon.png'),
    title: 'Notion Importer'
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  
  // Only open DevTools in development mode (not in packaged app)
  if (!app.isPackaged) {
    mainWindow.webContents.openDevTools();
  }
}

app.whenReady().then(createWindow);

// Auto-update setup
app.whenReady().then(() => {
  try {
    autoUpdater.autoDownload = true;
    autoUpdater.checkForUpdatesAndNotify();
  } catch (e) {
    console.error('autoUpdater init failed:', e);
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC Handlers
ipcMain.handle('load-config', async () => {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      const data = fs.readFileSync(CONFIG_FILE, 'utf-8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error('Failed to load config:', err);
  }
  return {
    NOTION_TOKEN: '',
    PARENT_ID: '',
    SOURCE_DIR: '/home/koto/C2Nv2/work 2'
  };
});

ipcMain.handle('save-config', async (event, config) => {
  try {
    if (!fs.existsSync(CONFIG_DIR)) {
      fs.mkdirSync(CONFIG_DIR, { recursive: true });
    }
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), 'utf-8');
    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('browse-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('browse-save-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory'],
    title: 'Select Output Folder for Markdown Export'
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('test-connection', async (event, token) => {
  console.log('Test connection IPC received, token length:', token.length);
  return new Promise((resolve) => {
    const projectDir = path.join(__dirname, '..');
    if (app.isPackaged) {
      // Use bundled binary
      const bin = path.join(process.resourcesPath, 'python_dist', process.platform === 'win32' ? 'test_connection.exe' : 'test_connection');
      console.log('Using packaged test_connection at:', bin);
      const env = { ...process.env, NOTION_TOKEN: token };
      const child = spawn(bin, [], { env });
      let output = '';
      let errors = '';
      child.stdout.on('data', (d) => { output += d.toString(); });
      child.stderr.on('data', (d) => { errors += d.toString(); });
      child.on('close', (code) => {
        if (code === 0 && output.includes('OK')) {
          resolve({ success: true });
        } else {
          resolve({ success: false, error: errors || output || `Exited ${code}` });
        }
      });
      child.on('error', (err) => resolve({ success: false, error: err.message }));
    } else {
      // Dev: use venv python if present, else system python3
      // Check both venv and .venv directories
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      console.log('Using Python:', pythonCmd);
      const pythonCode = `import sys\nimport os\nsys.path.insert(0, '${projectDir}')\ntry:\n    from notion_client import Client\n    token = """${token}"""\n    client = Client(auth=token)\n    client.users.me()\n    print("OK")\nexcept Exception as e:\n    import traceback\n    print(f"ERROR: {e}", file=sys.stderr)\n    print(traceback.format_exc(), file=sys.stderr)\n    sys.exit(1)\n`;
      const python = spawn(pythonCmd, ['-c', pythonCode]);
      let output = '';
      let errors = '';
      python.stdout.on('data', (data) => { output += data.toString(); });
      python.stderr.on('data', (data) => { errors += data.toString(); });
      python.on('close', (code) => {
        if (code === 0 && output.includes('OK')) {
          resolve({ success: true });
        } else {
          resolve({ success: false, error: errors || output || 'Unknown error' });
        }
      });
      python.on('error', (err) => { resolve({ success: false, error: `Failed to spawn python: ${err.message}` }); });
    }
  });
});

ipcMain.handle('get-statistics', async (event, sourceDir) => {
  return new Promise((resolve, reject) => {
    const projectDir = path.join(__dirname, '..');
    let cmd;
    let args = [];
    const env = { ...process.env };

    if (app.isPackaged) {
      // Use packaged Python
      cmd = path.join(process.resourcesPath, 'python_dist', process.platform === 'win32' ? 'python.exe' : 'python');
      args = ['-m', 'src.statistics', '--source-dir', sourceDir, '--comprehensive', '--json'];
      env.APP_RESOURCE_PATH = process.resourcesPath;
    } else {
      // Dev: python -m src.statistics --comprehensive --json
      // Check both venv and .venv directories
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      cmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      args = ['-m', 'src.statistics', '--source-dir', sourceDir, '--comprehensive', '--json'];
      env.APP_RESOURCE_PATH = projectDir;
    }

    const statsProcess = spawn(cmd, args, { 
      cwd: projectDir, 
      env 
    });

    let output = '';
    let errorOutput = '';

    statsProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    statsProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    statsProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const stats = JSON.parse(output);
          resolve({ success: true, stats });
        } catch (err) {
          resolve({ success: false, error: 'Failed to parse statistics', details: output });
        }
      } else {
        resolve({ success: false, error: `Process exited with code ${code}`, details: errorOutput });
      }
    });

    statsProcess.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
  });
});

// Export statistics to file
ipcMain.handle('export-statistics', async (event, sourceDir, format) => {
  return new Promise(async (resolve) => {
    // Ask user where to save the file
    const extensions = {
      'html': { name: 'HTML Report', extensions: ['html'] },
      'csv': { name: 'CSV Files', extensions: ['csv'] },
      'pdf': { name: 'PDF Report', extensions: ['pdf'] },
      'json': { name: 'JSON Data', extensions: ['json'] }
    };
    
    const result = await dialog.showSaveDialog(mainWindow, {
      title: 'Export Statistics Report',
      defaultPath: `statistics_report.${format}`,
      filters: [extensions[format] || { name: 'All Files', extensions: ['*'] }]
    });
    
    if (result.canceled || !result.filePath) {
      resolve({ success: false, error: 'Export cancelled' });
      return;
    }
    
    const outputPath = result.filePath;
    const projectDir = path.join(__dirname, '..');
    let cmd;
    let args = [];
    const env = { ...process.env };

    if (app.isPackaged) {
      cmd = path.join(process.resourcesPath, 'python_dist', process.platform === 'win32' ? 'python.exe' : 'python');
      args = ['-m', 'src.statistics', '--source-dir', sourceDir, '--export', outputPath, '--format', format];
      env.APP_RESOURCE_PATH = process.resourcesPath;
    } else {
      // Check both venv and .venv directories
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      cmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      args = ['-m', 'src.statistics', '--source-dir', sourceDir, '--export', outputPath, '--format', format];
      env.APP_RESOURCE_PATH = projectDir;
    }

    const exportProcess = spawn(cmd, args, { cwd: projectDir, env });

    let output = '';
    let errorOutput = '';

    exportProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    exportProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    exportProcess.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true, path: outputPath, output });
      } else {
        resolve({ success: false, error: errorOutput || `Process exited with code ${code}` });
      }
    });

    exportProcess.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
  });
});

ipcMain.handle('export-markdown', async (event, config) => {
  return new Promise((resolve) => {
    const projectDir = path.join(__dirname, '..');
    let cmd;
    let args = [];
    const env = { ...process.env };

    const baseArgs = ['-m', 'src.markdown_exporter',
      '--source-dir', config.SOURCE_DIR,
      '--output-dir', config.OUTPUT_DIR,
      '--table-image-width', String(config.TABLE_IMAGE_WIDTH || 400),
      '--image-width', String(config.IMAGE_WIDTH || 600)
    ];
    
    // Add format flag for standard markdown (obsidian/vscode compatible)
    if (config.MD_FORMAT === 'obsidian') {
      baseArgs.push('--standard-markdown');
    }

    if (app.isPackaged) {
      cmd = path.join(process.resourcesPath, 'python_dist', process.platform === 'win32' ? 'python.exe' : 'python');
      args = baseArgs;
      env.APP_RESOURCE_PATH = process.resourcesPath;
    } else {
      // Dev: python -m src.markdown_exporter
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      cmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      args = baseArgs;
      env.APP_RESOURCE_PATH = projectDir;
    }

    const exportProcess = spawn(cmd, args, { cwd: projectDir, env });

    let output = '';
    let errorOutput = '';

    exportProcess.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      mainWindow.webContents.send('import-log', text);
    });

    exportProcess.stderr.on('data', (data) => {
      const text = data.toString();
      errorOutput += text;
      mainWindow.webContents.send('import-log', text);
    });

    exportProcess.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true, output });
      } else {
        resolve({ success: false, error: errorOutput || `Process exited with code ${code}`, output });
      }
    });

    exportProcess.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
  });
});

// Attachment Analyzer handlers
ipcMain.handle('analyze-attachments', async (event, sourceDir) => {
  return new Promise((resolve) => {
    const projectDir = path.join(__dirname, '..');
    const env = { ...process.env };
    
    let cmd;
    if (app.isPackaged) {
      cmd = path.join(process.resourcesPath, 'python_dist', process.platform === 'win32' ? 'python.exe' : 'python');
      env.APP_RESOURCE_PATH = process.resourcesPath;
    } else {
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      cmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      env.APP_RESOURCE_PATH = projectDir;
    }

    const args = ['-m', 'src.attachment_analyzer', '--source-dir', sourceDir, '--json'];
    const proc = spawn(cmd, args, { cwd: projectDir, env });
    
    let output = '';
    let errorOutput = '';

    proc.stdout.on('data', (data) => { output += data.toString(); });
    proc.stderr.on('data', (data) => { errorOutput += data.toString(); });

    proc.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(output);
          resolve(result);
        } catch (e) {
          resolve({ success: false, error: 'Failed to parse analysis result' });
        }
      } else {
        resolve({ success: false, error: errorOutput || `Process exited with code ${code}` });
      }
    });

    proc.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
  });
});

ipcMain.handle('convert-videos-to-mp3', async (event, config) => {
  return new Promise((resolve) => {
    const projectDir = path.join(__dirname, '..');
    const env = { ...process.env };
    
    let cmd;
    if (app.isPackaged) {
      cmd = path.join(process.resourcesPath, 'python_dist', process.platform === 'win32' ? 'python.exe' : 'python');
      env.APP_RESOURCE_PATH = process.resourcesPath;
    } else {
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      cmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      env.APP_RESOURCE_PATH = projectDir;
    }

    const args = ['-m', 'src.attachment_analyzer', 
      '--source-dir', config.sourceDir, 
      '--convert-videos',
      '--json'
    ];
    if (config.deleteOriginals) {
      args.push('--delete-originals');
    }

    const proc = spawn(cmd, args, { cwd: projectDir, env });
    
    let output = '';
    let errorOutput = '';

    proc.stdout.on('data', (data) => { 
      output += data.toString();
      mainWindow.webContents.send('import-log', data.toString());
    });
    proc.stderr.on('data', (data) => { 
      errorOutput += data.toString();
      mainWindow.webContents.send('import-log', data.toString());
    });

    proc.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(output);
          resolve(result);
        } catch (e) {
          resolve({ success: true, message: output });
        }
      } else {
        resolve({ success: false, error: errorOutput || `Process exited with code ${code}` });
      }
    });

    proc.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
  });
});

ipcMain.handle('delete-attachment', async (event, filePath) => {
  try {
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
      return { success: true, deleted: filePath };
    } else {
      return { success: false, error: 'File not found' };
    }
  } catch (e) {
    return { success: false, error: e.message };
  }
});

ipcMain.handle('start-import', async (event, config) => {
  return new Promise((resolve, reject) => {
    const projectDir = path.join(__dirname, '..');
    let cmd;
    let args = [];
    const env = { ...process.env };
    if (config.NOTION_TOKEN) env.NOTION_TOKEN = config.NOTION_TOKEN;

    if (app.isPackaged) {
      // Use packaged run_import helper
      cmd = path.join(process.resourcesPath, 'python_dist', process.platform === 'win32' ? 'run_import.exe' : 'run_import');
      args.push('--run');
      if (config.SOURCE_DIR) { args.push('--source-dir', config.SOURCE_DIR); }
      if (config.PARENT_ID) { args.push('--parent-id', config.PARENT_ID); }
      if (config.MAX_COLUMNS) { args.push('--max-columns', String(config.MAX_COLUMNS)); }
      if (config.SKIP_VERIFICATION) { args.push('--skip-verification'); }
      // Pass resource path for bundled tools
      env.APP_RESOURCE_PATH = process.resourcesPath;
      importProcess = spawn(cmd, args, { env });
    } else {
      // Dev: python -m src.importer
      // Check both venv and .venv directories
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      const pyArgs = ['-m', 'src.importer'];
      pyArgs.push('--run');
      if (config.SOURCE_DIR) { pyArgs.push('--source-dir', config.SOURCE_DIR); }
      if (config.PARENT_ID) { pyArgs.push('--parent-id', config.PARENT_ID); }
      if (config.MAX_COLUMNS) { pyArgs.push('--max-columns', String(config.MAX_COLUMNS)); }
      if (config.SKIP_VERIFICATION) { pyArgs.push('--skip-verification'); }
      // Expose resource path so Python can find bundled tools during dev
      env.APP_RESOURCE_PATH = projectDir;
      importProcess = spawn(pythonCmd, pyArgs, { cwd: projectDir, env });
    }

    let output = '';
    
    importProcess.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      mainWindow.webContents.send('import-log', text);
    });

    importProcess.stderr.on('data', (data) => {
      const text = data.toString();
      output += text;
      mainWindow.webContents.send('import-log', text);
    });

    importProcess.on('close', (code) => {
      importProcess = null;
      if (code === 0) {
        resolve({ success: true, output });
      } else {
        resolve({ success: false, error: `Process exited with code ${code}`, output });
      }
    });

    importProcess.on('error', (err) => {
      importProcess = null;
      resolve({ success: false, error: err.message });
    });
  });
});

ipcMain.handle('retry-failed', async () => {
  return new Promise((resolve) => {
    const projectDir = path.join(__dirname, '..');
    let cmd, args = [];
    const env = { ...process.env };
    
    if (app.isPackaged) {
      // Use packaged retry binary (we'd need to build this)
      cmd = path.join(process.resourcesPath, 'python_dist', 'retry_failed');
      env.APP_RESOURCE_PATH = process.resourcesPath;
    } else {
      // Dev: python -m python_tools.retry_failed
      // Check both venv and .venv directories
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      cmd = pythonCmd;
      args = [path.join(projectDir, 'python_tools', 'retry_failed.py')];
      env.APP_RESOURCE_PATH = projectDir;
    }
    
    const retryProcess = spawn(cmd, args, { cwd: projectDir, env });
    let output = '';
    
    retryProcess.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      mainWindow.webContents.send('import-log', text);
    });
    
    retryProcess.stderr.on('data', (data) => {
      const text = data.toString();
      output += text;
      mainWindow.webContents.send('import-log', text);
    });
    
    retryProcess.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true, output });
      } else {
        resolve({ success: false, error: `Process exited with code ${code}`, output });
      }
    });
    
    retryProcess.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
  });
});

ipcMain.handle('stop-import', async () => {
  if (importProcess) {
    importProcess.kill();
    importProcess = null;
    return { success: true };
  }
  return { success: false };
});

ipcMain.handle('cleanup-old-failures', async () => {
  return new Promise((resolve) => {
    const projectDir = path.join(__dirname, '..');
    let cmd, args = [];
    const env = { ...process.env };
    
    if (app.isPackaged) {
      cmd = path.join(process.resourcesPath, 'python_dist', 'cleanup_old_failures');
      env.APP_RESOURCE_PATH = process.resourcesPath;
    } else {
      // Check both venv and .venv directories
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      cmd = pythonCmd;
      args = [path.join(projectDir, 'python_tools', 'cleanup_old_failures.py')];
      env.APP_RESOURCE_PATH = projectDir;
    }
    
    const cleanupProcess = spawn(cmd, args, { cwd: projectDir, env });
    
    let output = '';
    
    cleanupProcess.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    cleanupProcess.stderr.on('data', (data) => {
      output += data.toString();
    });
    
    cleanupProcess.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true, output });
      } else {
        resolve({ success: false, error: `Process exited with code ${code}`, output });
      }
    });
    
    cleanupProcess.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
  });
});

// Query parsing errors from database
ipcMain.handle('get-parsing-errors', async (event, options = {}) => {
  return new Promise((resolve) => {
    const projectDir = path.join(__dirname, '..');
    let cmd, args = [];
    const env = { ...process.env };
    
    if (app.isPackaged) {
      cmd = path.join(process.resourcesPath, 'python_dist', 'query_errors');
      env.APP_RESOURCE_PATH = process.resourcesPath;
    } else {
      // Check both venv and .venv directories
      const venvPath1 = path.join(projectDir, 'venv', 'bin', 'python3');
      const venvPath2 = path.join(projectDir, '.venv', 'bin', 'python3');
      const venvPython = fs.existsSync(venvPath1) ? venvPath1 : venvPath2;
      const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      cmd = pythonCmd;
      args = [path.join(projectDir, 'python_tools', 'query_errors.py')];
      env.APP_RESOURCE_PATH = projectDir;
    }
    
    // Add optional filters
    if (options.runId) {
      args.push('--run-id', options.runId.toString());
    }
    if (options.stage) {
      args.push('--stage', options.stage);
    }
    if (options.summary) {
      args.push('--summary');
    }
    if (options.runsWithErrors) {
      args.push('--runs-with-errors');
    }
    
    const queryProcess = spawn(cmd, args, { cwd: projectDir, env });
    
    let output = '';
    let errorOutput = '';
    
    queryProcess.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    queryProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });
    
    queryProcess.on('close', (code) => {
      if (code === 0 && output) {
        try {
          const result = JSON.parse(output);
          resolve({ success: true, ...result });
        } catch (e) {
          resolve({ success: false, error: 'Failed to parse response', output });
        }
      } else {
        resolve({ success: false, error: errorOutput || `Process exited with code ${code}` });
      }
    });
    
    queryProcess.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
  });
});
