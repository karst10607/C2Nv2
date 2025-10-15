// Wrap in IIFE to avoid global scope pollution
(function() {
  const { electronAPI } = window;
  let currentConfig = {};
  let isImporting = false;

// DOM elements
const notionTokenInput = document.getElementById('notion-token');
const parentIdInput = document.getElementById('parent-id');
const sourceDirInput = document.getElementById('source-dir');
const maxColumnsInput = document.getElementById('max-columns');
const preserveLayoutCheckbox = document.getElementById('preserve-layout');
const minColumnHeightInput = document.getElementById('min-column-height');
const testConnectionBtn = document.getElementById('test-connection');
const connectionStatus = document.getElementById('connection-status');
const browseBtn = document.getElementById('browse-btn');
const saveBtn = document.getElementById('save-btn');
const dryRunBtn = document.getElementById('dry-run-btn');
const importBtn = document.getElementById('import-btn');
const stopBtn = document.getElementById('stop-btn');
const logOutput = document.getElementById('log-output');

// Load config on startup
(async () => {
  currentConfig = await electronAPI.loadConfig();
  notionTokenInput.value = currentConfig.NOTION_TOKEN || '';
  parentIdInput.value = currentConfig.PARENT_ID || '';
  sourceDirInput.value = currentConfig.SOURCE_DIR || '/home/koto/C2Nv2/work 2';
  maxColumnsInput.value = currentConfig.MAX_COLUMNS || 6;
  preserveLayoutCheckbox.checked = currentConfig.PRESERVE_LAYOUT !== false; // Default true
  minColumnHeightInput.value = currentConfig.MIN_COLUMN_HEIGHT || 3;
})();

// Test connection
testConnectionBtn.addEventListener('click', async () => {
  console.log('Test connection clicked');
  const token = notionTokenInput.value.trim();
  if (!token) {
    connectionStatus.textContent = 'Please enter a token';
    connectionStatus.className = 'error';
    return;
  }

  connectionStatus.textContent = 'Testing...';
  connectionStatus.className = '';
  testConnectionBtn.disabled = true;

  try {
    console.log('Calling testConnection with token:', token.substring(0, 10) + '...');
    const result = await electronAPI.testConnection(token);
    console.log('Test connection result:', result);
    
    if (result.success) {
      connectionStatus.textContent = '✓ Connected';
      connectionStatus.className = 'success';
    } else {
      // Extract just the main error message, not the full traceback
      let errorMsg = result.error || 'Unknown error';
      
      // If it's the common "API token is invalid" error
      if (errorMsg.includes('API token is invalid')) {
        connectionStatus.textContent = '✗ Invalid token. Check: 1) Token is correct 2) Integration is Internal type 3) Connected to a page';
      } else if (errorMsg.includes('ERROR:')) {
        // Extract just the ERROR line
        const match = errorMsg.match(/ERROR: ([^\n]+)/);
        connectionStatus.textContent = '✗ ' + (match ? match[1] : 'Connection failed');
      } else {
        // Show first line only
        const firstLine = errorMsg.split('\n')[0];
        connectionStatus.textContent = '✗ ' + firstLine.substring(0, 100);
      }
      
      connectionStatus.className = 'error';
      connectionStatus.title = errorMsg; // Show full error on hover
      console.error('Full error:', errorMsg); // Log full error to console
    }
  } catch (error) {
    console.error('Test connection error:', error);
    connectionStatus.textContent = '✗ Error: ' + error.message;
    connectionStatus.className = 'error';
  }
  
  testConnectionBtn.disabled = false;
});

// Browse folder
browseBtn.addEventListener('click', async () => {
  const folder = await electronAPI.browseFolder();
  if (folder) {
    sourceDirInput.value = folder;
  }
});

// Save config
saveBtn.addEventListener('click', async () => {
  const config = {
    NOTION_TOKEN: notionTokenInput.value.trim(),
    PARENT_ID: parentIdInput.value.trim(),
    SOURCE_DIR: sourceDirInput.value.trim(),
    MAX_COLUMNS: parseInt(maxColumnsInput.value) || 6,
    PRESERVE_LAYOUT: preserveLayoutCheckbox.checked,
    MIN_COLUMN_HEIGHT: parseInt(minColumnHeightInput.value) || 3
  };

  const result = await electronAPI.saveConfig(config);
  
  if (result.success) {
    alert('Configuration saved successfully!');
    currentConfig = config;
  } else {
    alert('Failed to save configuration: ' + result.error);
  }
});

// Dry run
dryRunBtn.addEventListener('click', async () => {
  await runImport(true);
});

// Start import
importBtn.addEventListener('click', async () => {
  const token = notionTokenInput.value.trim();
  const parentId = parentIdInput.value.trim();
  
  if (!token) {
    alert('Please enter a Notion token');
    return;
  }
  
  if (!parentId) {
    const confirmed = confirm('No Parent ID set. The import will fail without it. Continue anyway?');
    if (!confirmed) return;
  }

  await runImport(false);
});

// Stop import
stopBtn.addEventListener('click', async () => {
  await electronAPI.stopImport();
  stopBtn.style.display = 'none';
  importBtn.disabled = false;
  dryRunBtn.disabled = false;
  isImporting = false;
  appendLog('\n[Stopped by user]\n');
});

// Run import
async function runImport(dryRun) {
  if (isImporting) return;

  const config = {
    NOTION_TOKEN: notionTokenInput.value.trim(),
    PARENT_ID: parentIdInput.value.trim(),
    SOURCE_DIR: sourceDirInput.value.trim(),
    MAX_COLUMNS: parseInt(maxColumnsInput.value) || 6,
    PRESERVE_LAYOUT: preserveLayoutCheckbox.checked,
    MIN_COLUMN_HEIGHT: parseInt(minColumnHeightInput.value) || 3
  };

  logOutput.textContent = '';
  isImporting = true;
  importBtn.disabled = true;
  dryRunBtn.disabled = true;
  stopBtn.style.display = 'inline-block';

  appendLog(`Starting ${dryRun ? 'dry run' : 'import'}...\n\n`);

  const result = await electronAPI.startImport(config, dryRun);

  stopBtn.style.display = 'none';
  importBtn.disabled = false;
  dryRunBtn.disabled = false;
  isImporting = false;

  if (result.success) {
    appendLog('\n✓ Completed successfully!\n');
  } else {
    appendLog('\n✗ Failed: ' + (result.error || 'Unknown error') + '\n');
  }
}

// Listen for import logs
electronAPI.onImportLog((data) => {
  appendLog(data);
});

function appendLog(text) {
  logOutput.textContent += text;
  logOutput.scrollTop = logOutput.scrollHeight;
}

})(); // End of IIFE
