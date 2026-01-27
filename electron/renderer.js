// Wrap in IIFE to avoid global scope pollution
(function() {
  const { electronAPI } = window;
  let currentConfig = {};
  let isImporting = false;
  let currentTab = 'md-export';

// DOM elements - Common
const sourceDirInput = document.getElementById('source-dir');
const browseBtn = document.getElementById('browse-btn');
const statisticsBtn = document.getElementById('statistics-btn');
const statisticsModal = document.getElementById('statistics-modal');
const statisticsClose = document.getElementById('statistics-close');
const statisticsContent = document.getElementById('statistics-content');
const logOutput = document.getElementById('log-output');

// DOM elements - Markdown Export tab
const exportMdBtn = document.getElementById('export-md-btn');
const mdImageWidthInput = document.getElementById('md-image-width');
const mdTableImageWidthInput = document.getElementById('md-table-image-width');
const imageWidthGroup = document.getElementById('image-width-group');
const tableImageWidthGroup = document.getElementById('table-image-width-group');

// DOM elements - Analyze tab
const analyzeSourceDirInput = document.getElementById('analyze-source-dir');
const analyzeBrowseBtn = document.getElementById('analyze-browse-btn');
const analyzeBtn = document.getElementById('analyze-btn');
const analysisResults = document.getElementById('analysis-results');
const analysisSummaryContent = document.getElementById('analysis-summary-content');
const analysisCategoriesContent = document.getElementById('analysis-categories-content');
const analysisExtensionsContent = document.getElementById('analysis-extensions-content');
const videoSection = document.getElementById('video-section');
const videoList = document.getElementById('video-list');
const convertAllMp3Btn = document.getElementById('convert-all-mp3-btn');
const deleteOriginalsCheckbox = document.getElementById('delete-originals-checkbox');
const largeFilesSection = document.getElementById('large-files-section');
const largeFilesList = document.getElementById('large-files-list');

// Handle markdown format radio buttons
document.querySelectorAll('input[name="md-format"]').forEach(radio => {
  radio.addEventListener('change', (e) => {
    const isGitHub = e.target.value === 'github';
    if (imageWidthGroup) imageWidthGroup.style.display = isGitHub ? 'block' : 'none';
    if (tableImageWidthGroup) tableImageWidthGroup.style.display = isGitHub ? 'block' : 'none';
  });
});

function getSelectedMdFormat() {
  const selected = document.querySelector('input[name="md-format"]:checked');
  return selected ? selected.value : 'obsidian';
}

// DOM elements - Notion Import tab
const notionTokenInput = document.getElementById('notion-token');
const parentIdInput = document.getElementById('parent-id');
const sourceDirNotionInput = document.getElementById('source-dir-notion');
const browseBtnNotion = document.getElementById('browse-btn-notion');
const maxColumnsInput = document.getElementById('max-columns');
const preserveLayoutCheckbox = document.getElementById('preserve-layout');
const minColumnHeightInput = document.getElementById('min-column-height');
const skipMissingMediaCheckbox = document.getElementById('skip-missing-media');
const testConnectionBtn = document.getElementById('test-connection');
const connectionStatus = document.getElementById('connection-status');
const saveBtn = document.getElementById('save-btn');
const statisticsBtnNotion = document.getElementById('statistics-btn-notion');
const importBtn = document.getElementById('import-btn');
const retryBtn = document.getElementById('retry-btn');
const cleanupBtn = document.getElementById('cleanup-btn');
const stopBtn = document.getElementById('stop-btn');

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

// ===== Tab Navigation =====
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tabId = btn.dataset.tab;
    
    // Update active tab button
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    // Update active tab content
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
    
    currentTab = tabId;
  });
});

// Sync source directories between tabs
// Each tab has independent source directory - no syncing between tabs

// ===== Theme Toggle =====
const themeToggle = document.getElementById('theme-toggle');
const themeIcon = themeToggle?.querySelector('.theme-icon');

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  if (themeIcon) {
    themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
  }
  localStorage.setItem('theme', theme);
}

// Load saved theme or default to dark
const savedTheme = localStorage.getItem('theme') || 'dark';
setTheme(savedTheme);

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    setTheme(currentTheme === 'dark' ? 'light' : 'dark');
  });
}

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
  
  // Don't auto-fill source directory - let user browse each session
  // This avoids confusion when switching between different exports
  sourceDirInput.value = '';
  if (sourceDirNotionInput) sourceDirNotionInput.value = '';
  if (analyzeSourceDirInput) analyzeSourceDirInput.value = '';
  
  maxColumnsInput.value = currentConfig.MAX_COLUMNS || 6;
  preserveLayoutCheckbox.checked = currentConfig.PRESERVE_LAYOUT !== false;
  minColumnHeightInput.value = currentConfig.MIN_COLUMN_HEIGHT || 3;
  skipMissingMediaCheckbox.checked = currentConfig.SKIP_MISSING_MEDIA !== false;
  document.getElementById('use-async').checked = currentConfig.USE_ASYNC !== false;
  document.getElementById('skip-verification').checked = currentConfig.SKIP_VERIFICATION === true;
  
  // Load markdown export settings
  if (mdImageWidthInput) mdImageWidthInput.value = currentConfig.MD_IMAGE_WIDTH || 600;
  if (mdTableImageWidthInput) mdTableImageWidthInput.value = currentConfig.MD_TABLE_IMAGE_WIDTH || 400;
  
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

// Browse folder - Markdown tab
browseBtn.addEventListener('click', async () => {
  const folder = await electronAPI.browseFolder();
  if (folder) {
    sourceDirInput.value = folder;
  }
});

// Browse folder - Notion tab
if (browseBtnNotion) {
  browseBtnNotion.addEventListener('click', async () => {
    const folder = await electronAPI.browseFolder();
    if (folder) {
      sourceDirNotionInput.value = folder;
    }
  });
}

// Save config
saveBtn.addEventListener('click', async () => {
  const uploadMode = uploadModeSelect.value;
  
  // Use Notion source dir if available, otherwise use the common one
  const sourceDir = sourceDirNotionInput ? sourceDirNotionInput.value.trim() : sourceDirInput.value.trim();
  
  const config = {
    NOTION_TOKEN: notionTokenInput.value.trim(),
    PARENT_ID: parentIdInput.value.trim(),
    SOURCE_DIR: sourceDir,
    MAX_COLUMNS: parseInt(maxColumnsInput.value) || 6,
    PRESERVE_LAYOUT: preserveLayoutCheckbox.checked,
    MIN_COLUMN_HEIGHT: parseInt(minColumnHeightInput.value) || 3,
    SKIP_MISSING_MEDIA: skipMissingMediaCheckbox.checked,
    UPLOAD_MODE: uploadMode,
    USE_ASYNC: document.getElementById('use-async').checked,
    SKIP_VERIFICATION: document.getElementById('skip-verification').checked,
    // Markdown export settings
    MD_IMAGE_WIDTH: parseInt(mdImageWidthInput?.value) || 600,
    MD_TABLE_IMAGE_WIDTH: parseInt(mdTableImageWidthInput?.value) || 400
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

// Show statistics - shared function
async function showStatistics() {
  // Get source dir from current tab
  const sourceDir = currentTab === 'md-export' 
    ? sourceDirInput.value.trim() 
    : (sourceDirNotionInput ? sourceDirNotionInput.value.trim() : sourceDirInput.value.trim());
  
  if (!sourceDir) {
    alert('Please select a source directory first');
    return;
  }
  
  statisticsModal.style.display = 'block';
  statisticsContent.innerHTML = '<div class="statistics-loading">Scanning HTML files...</div>';
  
  try {
    const result = await electronAPI.getStatistics(sourceDir);
    if (result.success) {
      displayStatistics(result.stats);
    } else {
      statisticsContent.innerHTML = `<div class="statistics-loading" style="color: #e53e3e;">Error: ${result.error || 'Failed to get statistics'}</div>`;
    }
  } catch (error) {
    statisticsContent.innerHTML = `<div class="statistics-loading" style="color: #e53e3e;">Error: ${error.message}</div>`;
  }
}

// Show statistics - Markdown tab
statisticsBtn.addEventListener('click', showStatistics);

// Show statistics - Notion tab
if (statisticsBtnNotion) {
  statisticsBtnNotion.addEventListener('click', showStatistics);
}

// Close statistics modal
statisticsClose.addEventListener('click', () => {
  statisticsModal.style.display = 'none';
});

// Close modal when clicking outside
statisticsModal.addEventListener('click', (e) => {
  if (e.target === statisticsModal) {
    statisticsModal.style.display = 'none';
  }
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

  await runImport();
});

// Export to GitHub Markdown
exportMdBtn.addEventListener('click', async () => {
  const sourceDir = sourceDirInput.value.trim();
  
  if (!sourceDir) {
    alert('Please select a source directory first');
    return;
  }
  
  // Ask user for output directory
  const outputDir = await electronAPI.browseSaveFolder();
  if (!outputDir) {
    return; // User cancelled
  }
  
  await runMarkdownExport(sourceDir, outputDir);
});

// ===== Analyze Tab Event Handlers =====

// Browse for analyze source directory
if (analyzeBrowseBtn) {
  analyzeBrowseBtn.addEventListener('click', async () => {
    const folder = await electronAPI.browseFolder();
    if (folder) {
      analyzeSourceDirInput.value = folder;
    }
  });
}

// Run attachment analysis
if (analyzeBtn) {
  analyzeBtn.addEventListener('click', async () => {
    const sourceDir = analyzeSourceDirInput.value.trim();
    
    if (!sourceDir) {
      alert('Please select a Confluence export folder first');
      return;
    }
    
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '🔄 Analyzing...';
    
    try {
      const result = await electronAPI.analyzeAttachments(sourceDir);
      displayAnalysisResults(result);
    } catch (err) {
      alert('Analysis failed: ' + err.message);
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = '🔍 Analyze Attachments';
    }
  });
}

// Convert all videos to MP3
if (convertAllMp3Btn) {
  convertAllMp3Btn.addEventListener('click', async () => {
    const sourceDir = analyzeSourceDirInput.value.trim();
    const deleteOriginals = deleteOriginalsCheckbox?.checked || false;
    
    if (!sourceDir) {
      alert('Please run analysis first');
      return;
    }
    
    const confirmMsg = deleteOriginals
      ? 'This will convert all videos to MP3 and DELETE the original video files. Continue?'
      : 'This will convert all videos to MP3 (keeping originals). Continue?';
    
    if (!confirm(confirmMsg)) return;
    
    convertAllMp3Btn.disabled = true;
    convertAllMp3Btn.textContent = '🔄 Converting...';
    
    try {
      const result = await electronAPI.convertVideosToMp3({
        sourceDir,
        deleteOriginals
      });
      
      if (result.success) {
        alert(`Converted ${result.converted} videos to MP3${result.failed ? ` (${result.failed} failed)` : ''}`);
        // Re-run analysis to refresh the list
        analyzeBtn.click();
      } else {
        alert('Conversion failed: ' + (result.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Conversion failed: ' + err.message);
    } finally {
      convertAllMp3Btn.disabled = false;
      convertAllMp3Btn.textContent = '🎵 Convert All to MP3';
    }
  });
}

// Display analysis results
function displayAnalysisResults(result) {
  if (!result.success) {
    alert('Analysis failed: ' + (result.error || 'Unknown error'));
    return;
  }
  
  analysisResults.style.display = 'block';
  
  // Summary
  analysisSummaryContent.innerHTML = `
    <div class="summary-grid">
      <div class="summary-item">
        <div class="value">${result.total_files}</div>
        <div class="label">Total Files</div>
      </div>
      <div class="summary-item">
        <div class="value">${result.total_size_formatted}</div>
        <div class="label">Total Size</div>
      </div>
      <div class="summary-item">
        <div class="value">${Object.keys(result.categories || {}).length}</div>
        <div class="label">Categories</div>
      </div>
      <div class="summary-item">
        <div class="value">${Object.keys(result.extensions || {}).length}</div>
        <div class="label">Extensions</div>
      </div>
    </div>
  `;
  
  // Categories
  const categoryIcons = {
    video: '🎬',
    audio: '🎵',
    image: '🖼️',
    document: '📄',
    data: '📊',
    archive: '📦',
    code: '💻',
    other: '📎',
    no_extension: '❓'
  };
  
  let categoriesHtml = '<div class="tag-list">';
  for (const [category, data] of Object.entries(result.categories || {})) {
    const icon = categoryIcons[category] || '📎';
    categoriesHtml += `
      <div class="category-tag ${category}">
        <span>${icon} ${category}</span>
        <span class="tag-count">${data.count}</span>
        <span class="tag-size">${data.size_formatted}</span>
      </div>
    `;
  }
  categoriesHtml += '</div>';
  analysisCategoriesContent.innerHTML = categoriesHtml;
  
  // Extensions (sorted by count)
  const sortedExtensions = Object.entries(result.extensions || {})
    .sort((a, b) => b[1].count - a[1].count);
  
  let extensionsHtml = '<div class="tag-list">';
  for (const [ext, data] of sortedExtensions) {
    extensionsHtml += `
      <div class="extension-tag">
        <span>${ext}</span>
        <span class="tag-count">${data.count}</span>
        <span class="tag-size">${data.size_formatted}</span>
      </div>
    `;
  }
  extensionsHtml += '</div>';
  analysisExtensionsContent.innerHTML = extensionsHtml;
  
  // Video files
  if (result.has_videos && result.video_files?.length > 0) {
    videoSection.style.display = 'block';
    
    let videoHtml = '';
    for (const video of result.video_files) {
      videoHtml += `
        <div class="file-item" data-path="${video.path}">
          <div class="file-info">
            <div class="file-name">🎬 ${video.name}</div>
            <div class="file-path">${video.relative_path}</div>
          </div>
          <div class="file-size">${video.size_formatted}</div>
          <div class="file-actions">
            <button class="delete-btn" onclick="deleteFile('${video.path.replace(/'/g, "\\'")}')">🗑️ Delete</button>
          </div>
        </div>
      `;
    }
    videoList.innerHTML = videoHtml;
  } else {
    videoSection.style.display = 'none';
  }
  
  // Large files (>10MB)
  const largeFiles = [];
  const SIZE_THRESHOLD = 10 * 1024 * 1024; // 10MB
  
  for (const category of Object.values(result.categories || {})) {
    for (const file of category.files || []) {
      if (file.size > SIZE_THRESHOLD) {
        largeFiles.push(file);
      }
    }
  }
  
  if (largeFiles.length > 0) {
    largeFilesSection.style.display = 'block';
    largeFiles.sort((a, b) => b.size - a.size);
    
    let largeHtml = '';
    for (const file of largeFiles.slice(0, 20)) {
      const icon = categoryIcons[file.category] || '📎';
      largeHtml += `
        <div class="file-item" data-path="${file.path}">
          <div class="file-info">
            <div class="file-name">${icon} ${file.name}</div>
            <div class="file-path">${file.relative_path}</div>
          </div>
          <div class="file-size">${file.size_formatted}</div>
          <div class="file-actions">
            <button class="delete-btn" onclick="deleteFile('${file.path.replace(/'/g, "\\'")}')">🗑️ Delete</button>
          </div>
        </div>
      `;
    }
    if (largeFiles.length > 20) {
      largeHtml += `<div style="text-align: center; color: #888; padding: 10px;">... and ${largeFiles.length - 20} more large files</div>`;
    }
    largeFilesList.innerHTML = largeHtml;
  } else {
    largeFilesSection.style.display = 'none';
  }
}

// Delete a single file
async function deleteFile(filePath) {
  if (!confirm(`Delete this file?\n${filePath}`)) return;
  
  try {
    const result = await electronAPI.deleteAttachment(filePath);
    if (result.success) {
      // Remove from UI
      const item = document.querySelector(`.file-item[data-path="${filePath}"]`);
      if (item) {
        item.remove();
      }
    } else {
      alert('Failed to delete: ' + (result.error || 'Unknown error'));
    }
  } catch (err) {
    alert('Failed to delete: ' + err.message);
  }
}

// Make deleteFile available globally for onclick handlers
window.deleteFile = deleteFile;

// Retry failed images
retryBtn.addEventListener('click', async () => {
  if (isImporting) return;
  
  const confirmed = confirm('This will check all previously failed pages and retry verification. Continue?');
  if (!confirmed) return;
  
  await runRetry();
});

// Cleanup old failures
cleanupBtn.addEventListener('click', async () => {
  if (isImporting) return;
  
  const confirmed = confirm('This will remove old failed page records where the Notion pages no longer exist.\n\nThis helps clean up the retry list to focus on current failures. Continue?');
  if (!confirmed) return;
  
  await runCleanup();
});

// Stop import
stopBtn.addEventListener('click', async () => {
  await electronAPI.stopImport();
  stopBtn.style.display = 'none';
  importBtn.disabled = false;
  statisticsBtn.disabled = false;
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
async function runImport() {
  if (isImporting) return;

  // Use Notion-specific source dir if available
  const sourceDir = sourceDirNotionInput ? sourceDirNotionInput.value.trim() : sourceDirInput.value.trim();

  const config = {
    NOTION_TOKEN: notionTokenInput.value.trim(),
    PARENT_ID: parentIdInput.value.trim(),
    SOURCE_DIR: sourceDir,
    MAX_COLUMNS: parseInt(maxColumnsInput.value) || 6,
    PRESERVE_LAYOUT: preserveLayoutCheckbox.checked,
    MIN_COLUMN_HEIGHT: parseInt(minColumnHeightInput.value) || 3
  };

  logOutput.textContent = '';
  isImporting = true;
  importBtn.disabled = true;
  statisticsBtn.disabled = true;
  stopBtn.style.display = 'inline-block';
  
  // Initialize progress tracking
  startTime = Date.now();
  totalFiles = 0;
  processedFiles = 0;
  progressSection.style.display = 'block';
  updateProgress();
  
  // Start timer to update elapsed time
  progressTimer = setInterval(updateElapsedTime, 1000);

  appendLog('Starting import...\n\n');

  const result = await electronAPI.startImport(config);

  stopBtn.style.display = 'none';
  importBtn.disabled = false;
  statisticsBtn.disabled = false;
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

// Run markdown export
async function runMarkdownExport(sourceDir, outputDir) {
  if (isImporting) return;

  logOutput.textContent = '';
  isImporting = true;
  importBtn.disabled = true;
  exportMdBtn.disabled = true;
  statisticsBtn.disabled = true;

  const mdFormat = getSelectedMdFormat();
  const imageWidth = parseInt(mdImageWidthInput?.value) || 600;
  const tableImageWidth = parseInt(mdTableImageWidthInput?.value) || 400;

  const formatLabel = mdFormat === 'github' ? 'GitHub Flavored' : 'Standard Markdown (Obsidian/VS Code)';
  appendLog(`Starting Markdown export (${formatLabel})...\n`);
  appendLog(`Source: ${sourceDir}\n`);
  appendLog(`Output: ${outputDir}\n`);
  if (mdFormat === 'github') {
    appendLog(`Image width: ${imageWidth}px, Table image width: ${tableImageWidth}px\n`);
  }
  appendLog('\n');

  const config = {
    SOURCE_DIR: sourceDir,
    OUTPUT_DIR: outputDir,
    TABLE_IMAGE_WIDTH: tableImageWidth,
    IMAGE_WIDTH: imageWidth,
    MD_FORMAT: mdFormat
  };

  const result = await electronAPI.exportMarkdown(config);

  importBtn.disabled = false;
  exportMdBtn.disabled = false;
  statisticsBtn.disabled = false;
  isImporting = false;

  if (result.success) {
    appendLog('\n✓ Markdown export completed!\n');
    appendLog(`\nOutput written to: ${outputDir}\n`);
    alert(`Export complete!\n\nMarkdown files and assets saved to:\n${outputDir}`);
  } else {
    appendLog('\n✗ Export failed: ' + (result.error || 'Unknown error') + '\n');
  }
}

// Listen for import logs (single handler - also refreshes error panel)
electronAPI.onImportLog((data) => {
  appendLog(data);
  parseProgress(data);
  
  // Refresh error panel when import completes
  if (data.includes('Import Complete') || data.includes('Parsing/Conversion Errors')) {
    setTimeout(() => {
      if (typeof loadRunsWithErrors === 'function') {
        loadRunsWithErrors();
        loadErrors();
      }
    }, 1000);
  }
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
  statisticsBtn.disabled = true;
  retryBtn.disabled = true;
  
  appendLog('Starting retry of failed images...\n\n');
  
  const result = await electronAPI.retryFailed();
  
  importBtn.disabled = false;
  statisticsBtn.disabled = false;
  retryBtn.disabled = false;
  isImporting = false;
  
  if (result.success) {
    appendLog('\n✓ Retry completed!\n');
  } else {
    appendLog('\n✗ Retry failed: ' + (result.error || 'Unknown error') + '\n');
  }
}

// Run cleanup
async function runCleanup() {
  if (isImporting) return;
  
  logOutput.textContent = '';
  isImporting = true;
  importBtn.disabled = true;
  statisticsBtn.disabled = true;
  retryBtn.disabled = true;
  cleanupBtn.disabled = true;
  
  appendLog('Cleaning up old failed page records...\n\n');
  
  const result = await electronAPI.cleanupOldFailures();
  
  importBtn.disabled = false;
  statisticsBtn.disabled = false;
  retryBtn.disabled = false;
  cleanupBtn.disabled = false;
  isImporting = false;
  
  if (result.success) {
    appendLog(result.output);
    appendLog('\n✓ Cleanup completed!\n');
  } else {
    appendLog('\n✗ Cleanup failed: ' + result.error + '\n');
  }
}

// Display statistics in modal with pie charts and export buttons
function displayStatistics(stats) {
  // Store stats for export
  window.currentStats = stats;
  
  let html = '';
  
  // Export buttons
  html += '<div class="statistics-export-bar">';
  html += '<span class="export-label">📥 Export:</span>';
  html += '<button class="export-btn" data-format="html">🌐 HTML</button>';
  html += '<button class="export-btn" data-format="csv">📊 CSV</button>';
  html += '<button class="export-btn" data-format="pdf">📄 PDF</button>';
  html += '<button class="export-btn" data-format="json">{ } JSON</button>';
  html += '</div>';
  
  // Summary cards
  html += '<div class="statistics-summary-grid">';
  html += `<div class="stat-card"><div class="stat-value">${stats.total_files}</div><div class="stat-label">Total Files</div></div>`;
  html += `<div class="stat-card"><div class="stat-value">${stats.tables?.total || 0}</div><div class="stat-label">Tables</div></div>`;
  html += `<div class="stat-card"><div class="stat-value">${stats.drawio?.total || 0}</div><div class="stat-label">Draw.io</div></div>`;
  html += `<div class="stat-card"><div class="stat-value">${stats.layouts?.total || 0}</div><div class="stat-label">Layouts</div></div>`;
  html += `<div class="stat-card"><div class="stat-value">${Object.keys(stats.authors || {}).length}</div><div class="stat-label">Contributors</div></div>`;
  html += `<div class="stat-card"><div class="stat-value">${stats.metadata_count || 0}</div><div class="stat-label">With Metadata</div></div>`;
  html += '</div>';
  
  // Content Distribution Pie Chart
  const contentData = {
    'Tables': stats.tables?.total || 0,
    'Layouts': stats.layouts?.total || 0,
    'Videos': stats.videos?.total || 0,
    'Draw.io': stats.drawio?.total || 0,
    'PlantUML': stats.plantuml?.total || 0
  };
  const filteredContent = Object.entries(contentData).filter(([k,v]) => v > 0);
  
  if (filteredContent.length > 0) {
    html += '<div class="statistics-section">';
    html += '<h3>📊 Content Type Distribution</h3>';
    html += '<div class="pie-chart-container">';
    html += generatePieChart(Object.fromEntries(filteredContent));
    html += '</div>';
    html += '</div>';
  }
  
  // Authors/Contributors section
  if (stats.authors && Object.keys(stats.authors).length > 0) {
    html += '<div class="statistics-section">';
    html += '<h3>👥 Top Contributors</h3>';
    html += '<table class="contributors-table">';
    html += '<thead><tr><th>Name</th><th>Created</th><th>Edited</th><th>Total</th></tr></thead>';
    html += '<tbody>';
    
    const authorList = Object.entries(stats.authors)
      .map(([name, data]) => ({ name, created: data.created, edited: data.edited, total: data.created + data.edited }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 10);
    
    for (const author of authorList) {
      html += `<tr><td>${author.name}</td><td>${author.created}</td><td>${author.edited}</td><td><strong>${author.total}</strong></td></tr>`;
    }
    html += '</tbody></table>';
    
    if (Object.keys(stats.authors).length > 10) {
      html += `<div class="statistics-note">... and ${Object.keys(stats.authors).length - 10} more contributors</div>`;
    }
    html += '</div>';
  }
  
  // Yearly Activity
  if (stats.yearly?.modified && Object.keys(stats.yearly.modified).length > 0) {
    html += '<div class="statistics-section">';
    html += '<h3>📆 Activity by Year</h3>';
    html += '<div class="bar-chart-container">';
    html += generateBarChart(stats.yearly.modified, 'Pages Modified');
    html += '</div>';
    html += '</div>';
  }
  
  // Monthly Timeline
  if (stats.timeline?.modified && Object.keys(stats.timeline.modified).length > 0) {
    html += '<div class="statistics-section">';
    html += '<h3>📅 Monthly Activity (Last Modified)</h3>';
    html += '<div class="timeline-chart-container">';
    const timelineData = Object.fromEntries(
      Object.entries(stats.timeline.modified).slice(-12)  // Last 12 months
    );
    html += generateBarChart(timelineData, 'Pages');
    html += '</div>';
    html += '</div>';
  }
  
  // Detailed content sections (collapsible)
  html += '<details class="statistics-details">';
  html += '<summary>📋 Detailed Content Analysis</summary>';
  
  html += '<div class="statistics-section">';
  html += '<h3>📊 Tables</h3>';
  html += `<div class="statistics-item"><span class="statistics-label">Total tables</span><span class="statistics-value">${stats.tables?.total || 0}</span></div>`;
  html += `<div class="statistics-item"><span class="statistics-label">Files with tables</span><span class="statistics-value">${stats.tables?.files_with_tables || 0}</span></div>`;
  html += `<div class="statistics-item"><span class="statistics-label">Tables with merged cells</span><span class="statistics-value">${stats.tables?.with_merged_cells || 0}</span></div>`;
  html += '</div>';
  
  html += '<div class="statistics-section">';
  html += '<h3>🎥 Media</h3>';
  html += `<div class="statistics-item"><span class="statistics-label">Videos</span><span class="statistics-value">${stats.videos?.total || 0}</span></div>`;
  html += `<div class="statistics-item"><span class="statistics-label">Draw.io diagrams</span><span class="statistics-value">${stats.drawio?.total || 0}</span></div>`;
  html += `<div class="statistics-item"><span class="statistics-label">PlantUML diagrams</span><span class="statistics-value">${stats.plantuml?.total || 0}</span></div>`;
  html += '</div>';
  
  html += '</details>';
  
  statisticsContent.innerHTML = html;
  
  // Add export button handlers
  document.querySelectorAll('.export-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const format = btn.dataset.format;
      const sourceDir = sourceDirInput.value.trim();
      if (!sourceDir) {
        alert('No source directory selected');
        return;
      }
      
      btn.disabled = true;
      btn.textContent = '⏳ Exporting...';
      
      try {
        const result = await electronAPI.exportStatistics(sourceDir, format);
        if (result.success) {
          alert(`✓ Exported to:\n${result.path}`);
        } else {
          alert(`Export failed: ${result.error}`);
        }
      } catch (err) {
        alert(`Export error: ${err.message}`);
      }
      
      // Restore button
      const labels = { html: '🌐 HTML', csv: '📊 CSV', pdf: '📄 PDF', json: '{ } JSON' };
      btn.textContent = labels[format];
      btn.disabled = false;
    });
  });
}

// Generate CSS-based pie chart
function generatePieChart(data) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return '<p>No data</p>';
  
  const colors = ['#4ecdc4', '#ff6b6b', '#45b7d1', '#96ceb4', '#ffeaa7', '#dfe6e9'];
  let cumulativePercent = 0;
  let gradientParts = [];
  let legendHtml = '<div class="pie-legend">';
  
  Object.entries(data).forEach(([label, value], index) => {
    const percent = (value / total) * 100;
    const color = colors[index % colors.length];
    const startPercent = cumulativePercent;
    cumulativePercent += percent;
    
    gradientParts.push(`${color} ${startPercent}% ${cumulativePercent}%`);
    legendHtml += `<div class="legend-item"><span class="legend-color" style="background:${color}"></span>${label}: ${value} (${percent.toFixed(1)}%)</div>`;
  });
  
  legendHtml += '</div>';
  
  const pieStyle = `background: conic-gradient(${gradientParts.join(', ')})`;
  
  return `
    <div class="pie-chart-wrapper">
      <div class="pie-chart" style="${pieStyle}"></div>
      ${legendHtml}
    </div>
  `;
}

// Generate CSS-based bar chart
function generateBarChart(data, label) {
  const maxValue = Math.max(...Object.values(data), 1);
  let html = '<div class="bar-chart">';
  
  Object.entries(data).forEach(([key, value]) => {
    const percent = (value / maxValue) * 100;
    html += `
      <div class="bar-row">
        <span class="bar-label">${key}</span>
        <div class="bar-container">
          <div class="bar-fill" style="width: ${percent}%"></div>
          <span class="bar-value">${value}</span>
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  return html;
}

// ===== Error Panel Functionality =====

// Error panel elements
const errorPanel = document.getElementById('error-panel');
const panelToggle = document.getElementById('panel-toggle');
const errorRunFilter = document.getElementById('error-run-filter');
const errorStageFilter = document.getElementById('error-stage-filter');
const refreshErrorsBtn = document.getElementById('refresh-errors');
const errorList = document.getElementById('error-list');
const errorDetail = document.getElementById('error-detail');
const detailContent = document.getElementById('detail-content');
const errorBackBtn = document.getElementById('error-back');
const totalErrorsEl = document.getElementById('total-errors');
const parsingErrorsEl = document.getElementById('parsing-errors');
const uploadErrorsEl = document.getElementById('upload-errors');

// State for error panel
let currentErrors = [];
let runsWithErrors = [];

// Toggle panel collapsed state
panelToggle.addEventListener('click', () => {
  errorPanel.classList.toggle('collapsed');
});

// Refresh errors
refreshErrorsBtn.addEventListener('click', () => {
  loadErrors();
});

// Filter change handlers
errorRunFilter.addEventListener('change', () => {
  loadErrors();
});

errorStageFilter.addEventListener('change', () => {
  loadErrors();
});

// Back button in detail view
errorBackBtn.addEventListener('click', () => {
  errorDetail.style.display = 'none';
  errorList.style.display = 'block';
});

// Load runs with errors for the filter dropdown
async function loadRunsWithErrors() {
  const result = await electronAPI.getParsingErrors({ runsWithErrors: true });
  
  if (result.success && result.data) {
    runsWithErrors = result.data;
    
    // Update the run filter dropdown
    let options = '<option value="all">All Runs</option>';
    options += '<option value="latest">Latest Run</option>';
    
    for (const run of runsWithErrors) {
      const date = new Date(run.timestamp).toLocaleDateString();
      options += `<option value="${run.run_id}">Run #${run.run_id} (${date}) - ${run.error_count} errors</option>`;
    }
    
    errorRunFilter.innerHTML = options;
  }
}

// Load errors based on current filters
async function loadErrors() {
  const runValue = errorRunFilter.value;
  const stageValue = errorStageFilter.value;
  
  const options = {};
  
  if (runValue === 'latest' && runsWithErrors.length > 0) {
    options.runId = runsWithErrors[0].run_id;
  } else if (runValue !== 'all') {
    options.runId = parseInt(runValue);
  }
  
  if (stageValue !== 'all') {
    options.stage = stageValue;
  }
  
  const result = await electronAPI.getParsingErrors(options);
  
  if (result.success && result.data) {
    currentErrors = result.data.errors || [];
    const summary = result.data.summary || { total: 0, parsing_count: 0, upload_count: 0 };
    
    // Update summary stats
    totalErrorsEl.textContent = summary.total || 0;
    parsingErrorsEl.textContent = summary.parsing_count || 0;
    uploadErrorsEl.textContent = summary.upload_count || 0;
    
    // Render error list
    renderErrorList(currentErrors);
  } else {
    errorList.innerHTML = '<div class="error-empty">Failed to load errors.</div>';
  }
}

// Render the error list
function renderErrorList(errors) {
  if (!errors || errors.length === 0) {
    errorList.innerHTML = '<div class="error-empty">No errors recorded yet.</div>';
    return;
  }
  
  let html = '';
  
  for (const err of errors) {
    const timestamp = new Date(err.timestamp).toLocaleString();
    const shortMessage = err.error_message.length > 80 
      ? err.error_message.substring(0, 80) + '...' 
      : err.error_message;
    
    html += `
      <div class="error-item stage-${err.stage}" data-error-id="${err.id}">
        <div class="error-item-header">
          <span class="error-filename">${err.filename}</span>
          <span class="error-stage">${err.stage}</span>
        </div>
        <div class="error-message">${err.error_type}: ${shortMessage}</div>
        <div class="error-meta">
          <span>Run #${err.run_id}</span>
          <span>${timestamp}</span>
        </div>
      </div>
    `;
  }
  
  errorList.innerHTML = html;
  
  // Add click handlers to show detail
  document.querySelectorAll('.error-item').forEach(item => {
    item.addEventListener('click', () => {
      const errorId = parseInt(item.dataset.errorId);
      showErrorDetail(errorId);
    });
  });
}

// Show error detail view
function showErrorDetail(errorId) {
  const error = currentErrors.find(e => e.id === errorId);
  if (!error) return;
  
  let html = `
    <div class="detail-section">
      <h4>File</h4>
      <div class="detail-value">${error.filename}</div>
    </div>
    
    <div class="detail-section">
      <h4>Full Path</h4>
      <div class="detail-value">${error.file_path}</div>
    </div>
    
    <div class="detail-section">
      <h4>Stage</h4>
      <div class="detail-value">${error.stage}</div>
    </div>
    
    <div class="detail-section">
      <h4>Error Type</h4>
      <div class="detail-value">${error.error_type}</div>
    </div>
    
    <div class="detail-section">
      <h4>Error Message</h4>
      <div class="detail-value">${error.error_message}</div>
    </div>
    
    <div class="detail-section">
      <h4>Timestamp</h4>
      <div class="detail-value">${new Date(error.timestamp).toLocaleString()}</div>
    </div>
  `;
  
  if (error.traceback) {
    html += `
      <div class="detail-section">
        <h4>Traceback</h4>
        <div class="detail-traceback">${escapeHtml(error.traceback)}</div>
      </div>
    `;
  }
  
  detailContent.innerHTML = html;
  errorList.style.display = 'none';
  errorDetail.style.display = 'flex';
}

// Escape HTML for safe display
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Load errors on startup and after import
async function initErrorPanel() {
  await loadRunsWithErrors();
  await loadErrors();
}

// Initialize error panel on startup
initErrorPanel();

})(); // End of IIFE
