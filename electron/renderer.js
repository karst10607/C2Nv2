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
const retryBtn = document.getElementById('retry-btn');
const stopBtn = document.getElementById('stop-btn');
const logOutput = document.getElementById('log-output');

// Upload mode elements
const uploadModeSelect = document.getElementById('upload-mode');
const modeDescription = document.getElementById('mode-description');
const fileioConfig = document.getElementById('fileio-config');
const tunnelConfig = document.getElementById('tunnel-config');
const s3Config = document.getElementById('s3-config');
const cloudflareConfig = document.getElementById('cloudflare-config');
const notionConfig = document.getElementById('notion-config');

// Summary elements
const summarySection = document.getElementById('summary-section');
const summaryPages = document.getElementById('summary-pages');
const summaryBlocks = document.getElementById('summary-blocks');
const summaryImages = document.getElementById('summary-images');
const summaryTime = document.getElementById('summary-time');

// Progress elements
const progressSection = document.getElementById('progress-section');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const progressPercent = document.getElementById('progress-percent');
const progressTime = document.getElementById('progress-time');
const progressEta = document.getElementById('progress-eta');

// Handle upload mode changes
uploadModeSelect.addEventListener('change', () => {
  const mode = uploadModeSelect.value;
  
  // Hide all config sections  
  tunnelConfig.style.display = 'none';
  s3Config.style.display = 'none';
  cloudflareConfig.style.display = 'none';
  notionConfig.style.display = 'none';
  
  // Show relevant config
  const configMap = {
    's3': s3Config,
    's3_permanent': s3Config,
    'tunnel': tunnelConfig,
    'cloudflare': cloudflareConfig,
    'notion_native': notionConfig
  };
  
  if (configMap[mode]) {
    configMap[mode].style.display = 'block';
  }
  
  // Update description
  const descriptions = {
    's3': '☁️ Upload to S3 temp storage. AUTO-DELETES after 1 day via lifecycle rule. Reliable! (~$0.001 cost)',
    'notion_native': '📦 Uses S3 temp bridge. Notion converts to "file" type. Auto-deletes after 1 day. Experimental.',
    'tunnel': '🌐 Fast local serving. May cause 404s if tunnel closes too early. For quick tests only.',
    's3_permanent': '☁️ Permanent S3 storage. Manual cleanup needed. Costs ~$1-5/month ongoing.',
    'cloudflare': '☁️ Cloudflare R2 with lifecycle auto-delete. 3x cheaper than S3. Requires custom domain.'
  };
  
  modeDescription.textContent = descriptions[mode] || '';
  modeDescription.className = 'mode-help';
});

// Load config on startup
(async () => {
  currentConfig = await electronAPI.loadConfig();
  notionTokenInput.value = currentConfig.NOTION_TOKEN || '';
  parentIdInput.value = currentConfig.PARENT_ID || '';
  sourceDirInput.value = currentConfig.SOURCE_DIR || '';
  maxColumnsInput.value = currentConfig.MAX_COLUMNS || 6;
  preserveLayoutCheckbox.checked = currentConfig.PRESERVE_LAYOUT !== false;
  minColumnHeightInput.value = currentConfig.MIN_COLUMN_HEIGHT || 3;
  
  // Load upload mode settings
  uploadModeSelect.value = currentConfig.UPLOAD_MODE || 's3';
  uploadModeSelect.dispatchEvent(new Event('change'));  // Trigger mode change
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
  const uploadMode = uploadModeSelect.value;
  
  const config = {
    NOTION_TOKEN: notionTokenInput.value.trim(),
    PARENT_ID: parentIdInput.value.trim(),
    SOURCE_DIR: sourceDirInput.value.trim(),
    MAX_COLUMNS: parseInt(maxColumnsInput.value) || 6,
    PRESERVE_LAYOUT: preserveLayoutCheckbox.checked,
    MIN_COLUMN_HEIGHT: parseInt(minColumnHeightInput.value) || 3,
    UPLOAD_MODE: uploadMode,
    USE_ASYNC: document.getElementById('use-async').checked
  };
  
  // Add mode-specific settings
  if (uploadMode === 'tunnel') {
    config.TUNNEL_KEEPALIVE_SEC = parseInt(document.getElementById('tunnel-keepalive')?.value) || 600;
  }
  
  if (uploadMode === 's3' || uploadMode === 's3_permanent' || uploadMode === 'notion_native') {
    config.S3_BUCKET = document.getElementById('s3-bucket')?.value || '';
    config.S3_REGION = document.getElementById('s3-region')?.value || 'us-west-2';
    config.S3_ACCESS_KEY = document.getElementById('s3-access-key')?.value || '';
    config.S3_SECRET_KEY = document.getElementById('s3-secret-key')?.value || '';
    config.S3_USE_PRESIGNED = document.getElementById('s3-use-presigned')?.checked !== false;
    config.S3_LIFECYCLE_DAYS = parseInt(document.getElementById('s3-lifecycle-days')?.value) || 1;
  }
  
  if (uploadMode === 'cloudflare') {
    config.CF_BUCKET = document.getElementById('cf-bucket')?.value || '';
    config.CF_ACCOUNT_ID = document.getElementById('cf-account-id')?.value || '';
    config.CF_ACCESS_KEY = document.getElementById('cf-access-key')?.value || '';
    config.CF_SECRET_KEY = document.getElementById('cf-secret-key')?.value || '';
    config.CF_PUBLIC_DOMAIN = document.getElementById('cf-public-domain')?.value || '';
  }

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

// Retry failed images
retryBtn.addEventListener('click', async () => {
  if (isImporting) return;
  
  const confirmed = confirm('This will check all previously failed pages and retry verification. Continue?');
  if (!confirmed) return;
  
  await runRetry();
});

// Stop import
stopBtn.addEventListener('click', async () => {
  await electronAPI.stopImport();
  stopBtn.style.display = 'none';
  importBtn.disabled = false;
  dryRunBtn.disabled = false;
  isImporting = false;
  
  // Stop progress timer
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  
  appendLog('\n[Stopped by user]\n');
});

// Progress tracking variables
let startTime = null;
let totalFiles = 0;
let processedFiles = 0;
let progressTimer = null;

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
  
  // Initialize progress tracking
  startTime = Date.now();
  totalFiles = 0;
  processedFiles = 0;
  progressSection.style.display = 'block';
  updateProgress();
  
  // Start timer to update elapsed time
  progressTimer = setInterval(updateElapsedTime, 1000);

  appendLog(`Starting ${dryRun ? 'dry run' : 'import'}...\n\n`);

  const result = await electronAPI.startImport(config, dryRun);

  stopBtn.style.display = 'none';
  importBtn.disabled = false;
  dryRunBtn.disabled = false;
  isImporting = false;
  
  // Stop progress timer
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }

  if (result.success) {
    appendLog('\n✓ Import process completed!\n');
    // Don't force to 100% - let actual file processing determine progress
    // Progress already updated by parseProgress() from log output
    updateProgress(); // Final update with actual counts
  } else {
    appendLog('\n✗ Failed: ' + (result.error || 'Unknown error') + '\n');
  }
}

// Listen for import logs
electronAPI.onImportLog((data) => {
  appendLog(data);
  parseProgress(data);
});

function appendLog(text) {
  logOutput.textContent += text;
  logOutput.scrollTop = logOutput.scrollHeight;
}

// Parse progress from log output
function parseProgress(text) {
  // Look for "Scanning X HTML files..."
  const scanMatch = text.match(/Scanning (\d+) HTML files/);
  if (scanMatch) {
    totalFiles = parseInt(scanMatch[1]);
    processedFiles = 0;
    updateProgress();
  }
  
  // Look for Import Summary section
  const pagesMatch = text.match(/Pages:\s+(\d+)/);
  const blocksMatch = text.match(/Blocks:\s+(\d+)/);
  const imagesMatch = text.match(/Images:\s+(\d+)/);
  const timeMatch = text.match(/Est\. time:\s+~(\d+)m\s+(\d+)s/);
  
  if (pagesMatch || blocksMatch || imagesMatch) {
    summarySection.style.display = 'block';
    
    if (pagesMatch) summaryPages.textContent = pagesMatch[1];
    if (blocksMatch) summaryBlocks.textContent = blocksMatch[1];
    if (imagesMatch) summaryImages.textContent = imagesMatch[1];
    if (timeMatch) {
      const mins = parseInt(timeMatch[1]);
      const secs = parseInt(timeMatch[2]);
      summaryTime.textContent = `${mins}m ${secs}s`;
    }
  }
  
  // Look for file processing "- filename.html -> Title (X blocks, X images)"
  // Count ALL matches in the chunk, not just presence
  const fileMatches = text.match(/^- .+\.html -> .+ \(\d+ blocks, \d+ images\)/mg);
  if (fileMatches && fileMatches.length) {
    processedFiles += fileMatches.length;
    // Clamp to totalFiles to avoid going over on noisy logs
    if (totalFiles > 0) {
      processedFiles = Math.min(processedFiles, totalFiles);
    }
    updateProgress();
  }
}

// Update progress display
function updateProgress() {
  if (totalFiles === 0) {
    progressText.textContent = 'Initializing...';
    progressPercent.textContent = '0%';
    progressFill.style.width = '40px';
    return;
  }
  
  const percent = Math.round((processedFiles / totalFiles) * 100);
  progressText.textContent = `${processedFiles} / ${totalFiles} files`;
  progressPercent.textContent = `${percent}%`;
  progressFill.style.width = `${Math.max(5, percent)}%`;
  
  // Update ETA
  if (processedFiles > 0 && processedFiles < totalFiles) {
    const elapsed = Date.now() - startTime;
    const avgTimePerFile = elapsed / processedFiles;
    const remainingFiles = totalFiles - processedFiles;
    const eta = Math.round((avgTimePerFile * remainingFiles) / 1000);
    progressEta.textContent = `ETA: ${formatTime(eta)}`;
  } else if (processedFiles >= totalFiles) {
    progressEta.textContent = 'Complete!';
  }
}

// Update elapsed time display
function updateElapsedTime() {
  if (!startTime) return;
  
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  progressTime.textContent = `Time: ${formatTime(elapsed)}`;
}

// Format seconds to MM:SS
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Run retry
async function runRetry() {
  if (isImporting) return;
  
  logOutput.textContent = '';
  isImporting = true;
  importBtn.disabled = true;
  dryRunBtn.disabled = true;
  retryBtn.disabled = true;
  
  appendLog('Starting retry of failed images...\n\n');
  
  const result = await electronAPI.retryFailed();
  
  importBtn.disabled = false;
  dryRunBtn.disabled = false;
  retryBtn.disabled = false;
  isImporting = false;
  
  if (result.success) {
    appendLog('\n✓ Retry completed!\n');
  } else {
    appendLog('\n✗ Retry failed: ' + (result.error || 'Unknown error') + '\n');
  }
}

})(); // End of IIFE
