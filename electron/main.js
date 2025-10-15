const { app, BrowserWindow, ipcMain, dialog } = require('electron');
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
    icon: path.join(__dirname, 'icon.png')
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  
  // Dev tools enabled for debugging
  mainWindow.webContents.openDevTools();
}

app.whenReady().then(createWindow);

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
    // Try to use venv python if it exists
    const projectDir = path.join(__dirname, '..');
    const venvPython = path.join(projectDir, '.venv', 'bin', 'python3');
    const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
    console.log('Using Python:', pythonCmd);
    
    const pythonCode = `import sys
import os
sys.path.insert(0, '${projectDir}')
try:
    from notion_client import Client
    token = """${token}"""
    print(f"Token starts with: {token[:10]}...", file=sys.stderr)
    print(f"Token length: {len(token)}", file=sys.stderr)
    client = Client(auth=token)
    result = client.users.me()
    print(f"User ID: {result.get('id')}", file=sys.stderr)
    print("OK")
except Exception as e:
    import traceback
    print(f"ERROR: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)
`;
    
    const python = spawn(pythonCmd, ['-c', pythonCode]);

    let output = '';
    let errors = '';
    python.stdout.on('data', (data) => { 
      output += data.toString();
      console.log('Python stdout:', data.toString());
    });
    python.stderr.on('data', (data) => { 
      errors += data.toString();
      console.log('Python stderr:', data.toString());
    });
    
    python.on('close', (code) => {
      console.log('Python process closed with code:', code);
      if (code === 0 && output.includes('OK')) {
        resolve({ success: true });
      } else {
        resolve({ success: false, error: errors || output || 'Unknown error' });
      }
    });
    
    python.on('error', (err) => {
      resolve({ success: false, error: `Failed to spawn python: ${err.message}` });
    });
  });
});

ipcMain.handle('start-import', async (event, config, dryRun) => {
  return new Promise((resolve, reject) => {
    const projectDir = path.join(__dirname, '..');
    const venvPython = path.join(projectDir, '.venv', 'bin', 'python3');
    const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
    
    const args = ['-m', 'src.importer'];
    
    if (dryRun) {
      args.push('--dry-run');
    } else {
      args.push('--run');
    }
    
    if (config.SOURCE_DIR) {
      args.push('--source-dir', config.SOURCE_DIR);
    }
    
    if (config.PARENT_ID) {
      args.push('--parent-id', config.PARENT_ID);
    }
    
    if (config.MAX_COLUMNS) {
      args.push('--max-columns', String(config.MAX_COLUMNS));
    }

    const env = { ...process.env };
    if (config.NOTION_TOKEN) {
      env.NOTION_TOKEN = config.NOTION_TOKEN;
    }

    importProcess = spawn(pythonCmd, args, {
      cwd: projectDir,
      env: env
    });

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
