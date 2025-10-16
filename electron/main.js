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
  
  // Dev tools enabled for debugging
  mainWindow.webContents.openDevTools();
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
      const venvPython = path.join(projectDir, '.venv', 'bin', 'python3');
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

ipcMain.handle('start-import', async (event, config, dryRun) => {
  return new Promise((resolve, reject) => {
    const projectDir = path.join(__dirname, '..');
    let cmd;
    let args = [];
    const env = { ...process.env };
    if (config.NOTION_TOKEN) env.NOTION_TOKEN = config.NOTION_TOKEN;

    if (app.isPackaged) {
      // Use packaged run_import helper
      cmd = path.join(process.resourcesPath, 'python_dist', process.platform === 'win32' ? 'run_import.exe' : 'run_import');
      if (dryRun) args.push('--dry-run'); else args.push('--run');
      if (config.SOURCE_DIR) { args.push('--source-dir', config.SOURCE_DIR); }
      if (config.PARENT_ID) { args.push('--parent-id', config.PARENT_ID); }
      if (config.MAX_COLUMNS) { args.push('--max-columns', String(config.MAX_COLUMNS)); }
      // Pass resource path for bundled tools
      env.APP_RESOURCE_PATH = process.resourcesPath;
      importProcess = spawn(cmd, args, { env });
    } else {
      // Dev: python -m src.importer
      const venvPython = path.join(projectDir, '.venv', 'bin', 'python3');
      const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      const pyArgs = ['-m', 'src.importer'];
      if (dryRun) pyArgs.push('--dry-run'); else pyArgs.push('--run');
      if (config.SOURCE_DIR) { pyArgs.push('--source-dir', config.SOURCE_DIR); }
      if (config.PARENT_ID) { pyArgs.push('--parent-id', config.PARENT_ID); }
      if (config.MAX_COLUMNS) { pyArgs.push('--max-columns', String(config.MAX_COLUMNS)); }
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

ipcMain.handle('stop-import', async () => {
  if (importProcess) {
    importProcess.kill();
    importProcess = null;
    return { success: true };
  }
  return { success: false };
});
