# Upload Modes Guide - v3.1.0

## Overview

The importer now supports **5 different image upload modes** to solve the 404 problem.

---

## Quick Comparison

| Mode | Setup | Cost | Speed | Reliability | Auto-Cleanup | Best For |
|------|-------|------|-------|-------------|--------------|----------|
| **file.io** ⭐ | None | Free* | Medium | High | ✅ YES | **Most users** |
| **Notion Native** | None | Free | Medium | Medium | ✅ YES | Experimental users |
| **Tunnel** | Install CF | Free | Fast | Low | ❌ No | Quick tests only |
| **AWS S3** | AWS account | $1-5/mo | Fast | Very High | ❌ No | Enterprise |
| **Cloudflare R2** | CF account | $0.50/mo | Fast | Very High | ❌ No | Cost-conscious |

*Free tier: 100MB/file, limited uploads. Paid: $5/mo unlimited.

---

## Detailed Mode Explanations

### 🔥 **file.io (RECOMMENDED)**

**How it works:**
```
1. Upload image to file.io → Get URL
2. Send URL to Notion
3. Notion downloads image (FIRST download)
4. file.io AUTO-DELETES image
5. Notion has cached copy forever
```

**Pros:**
- ✅ **Auto-cleanup!** Files delete after Notion downloads
- ✅ No account needed (free tier works)
- ✅ No 404 issues (URLs valid 14 days)
- ✅ Privacy-friendly (auto-delete)
- ✅ No storage costs long-term

**Cons:**
- 🟡 Rate limited (10-20 uploads/min free, unlimited paid)
- 🟡 100 MB per file (free), 5GB (paid)
- 🟡 Slower than tunnel (upload takes time)

**When to use:**
- ✅ Medium imports (10-500 pages)
- ✅ Don't want permanent storage
- ✅ Want simplest setup

**Setup:**
```
1. Select "file.io" from dropdown
2. (Optional) Add API key for paid tier
3. Set expiry days (default 14)
4. Done!
```

---

### 📦 **Notion Native (Experimental)**

**How it works:**
```
1. Upload to file.io (as bridge)
2. Send URL to Notion as 'external' type
3. Notion downloads and caches
4. Notion CONVERTS from 'external' to 'file' type
5. Image now Notion-hosted forever
6. file.io auto-deletes
```

**Pros:**
- ✅ Images become 'file' type (not 'external')
- ✅ Hosted by Notion permanently
- ✅ No external dependencies after import
- ✅ Auto-cleanup from file.io

**Cons:**
- ⚠️ **Experimental** - relies on Notion's auto-conversion
- ⚠️ Not officially supported behavior
- ⚠️ May not work for all image types
- 🟡 Slower (upload + conversion time)

**When to use:**
- ✅ Want Notion-hosted images
- ✅ Willing to test experimental features
- ✅ Prefer 'file' type over 'external'

**Setup:**
```
1. Select "Notion Native"
2. Check "I understand this is experimental"
3. (Optional) Add file.io API key
4. Test with small batch first!
```

---

### 🌐 **Tunnel (Original Method)**

**How it works:**
```
1. Start local Flask server
2. Create cloudflared tunnel
3. Serve images via tunnel URL
4. Send tunnel URLs to Notion
5. Keep tunnel alive X seconds
6. Close tunnel
⚠️ If Notion fetches after tunnel closes → 404!
```

**Pros:**
- ✅ Fast (no upload needed)
- ✅ Free (no accounts)
- ✅ Works offline

**Cons:**
- ❌ **404 risk** if tunnel closes too early
- ❌ Must babysit (keep app running)
- ❌ Unreliable for large imports

**When to use:**
- ✅ Quick tests (1-5 pages)
- ✅ Development/debugging
- ❌ **NOT for production imports!**

**Setup:**
```
1. Install cloudflared: brew install cloudflared
2. Select "Tunnel"
3. Set keepalive (recommend 1800s = 30min for safety)
4. Keep app running during keepalive!
```

---

### ☁️ **AWS S3**

**How it works:**
```
1. Upload images to S3 bucket
2. Generate public URLs
3. Send S3 URLs to Notion
4. Notion downloads from S3
5. Images stay in S3 forever (until you delete)
```

**Pros:**
- ✅ **Permanent** URLs (never expire)
- ✅ Very reliable (99.99% uptime)
- ✅ Fast (global CDN)
- ✅ No tunnel timeout issues

**Cons:**
- 🟡 Requires AWS account
- 🟡 Storage costs (~$0.023/GB/month)
- 🟡 Setup complexity
- ❌ Manual cleanup needed

**When to use:**
- ✅ Enterprise deployments
- ✅ Need guaranteed reliability
- ✅ Already have AWS infrastructure

**Setup:**
```
1. Create S3 bucket in AWS console
2. Create IAM user with S3 permissions
3. Get access key + secret key
4. Enter in GUI
5. Images stored at: s3://your-bucket/notion-imports/...
```

**Costs:**
```
500 images × 200KB avg = 100 MB
Storage: $0.023/GB/month = $0.002/month
Bandwidth: First 100GB free
Total: ~$0.10/month for typical import
```

---

### ☁️ **Cloudflare R2**

**How it works:**
```
Same as S3, but using Cloudflare R2 (S3-compatible)
```

**Pros:**
- ✅ **Cheaper than S3** ($0.015/GB vs $0.023/GB)
- ✅ **No egress fees** (S3 charges for downloads)
- ✅ S3-compatible API (same code!)
- ✅ Fast global CDN

**Cons:**
- 🟡 Requires Cloudflare account
- 🟡 Requires custom domain setup
- 🟡 Newer service (less mature)

**When to use:**
- ✅ Cost-conscious enterprise
- ✅ Already use Cloudflare
- ✅ Need permanent storage cheaper than S3

**Setup:**
```
1. Create Cloudflare account
2. Enable R2, create bucket
3. Set up custom domain (images.yourdomain.com)
4. Get API keys
5. Enter in GUI
```

**Costs:**
```
500 images × 200KB = 100MB
Storage: $0.015/GB/month = $0.0015/month
Bandwidth: FREE (no egress fees!)
Total: ~$0.05/month (3x cheaper than S3)
```

---

## Recommended Modes by Use Case

### **Small Import (1-50 pages, <100 images):**
```
✅ file.io (free tier)
   - No setup, auto-cleanup
   - Perfect for testing
```

### **Medium Import (50-500 pages, 100-500 images):**
```
✅ file.io (paid tier $5/mo) 
   OR
✅ Notion Native (experimental)
   - Both auto-cleanup
   - file.io faster/more reliable
   - Notion Native for permanent Notion hosting
```

### **Large Import (500-1000+ pages, 500+ images):**
```
✅ Cloudflare R2 (if cost-conscious)
   OR
✅ AWS S3 (if need max reliability)
   - Permanent, reliable
   - Can delete old imports manually
   - Costs: $0.05-0.10/month
```

### **Quick Test/Debug:**
```
✅ Tunnel (with 1800s keepalive)
   - Fastest for dev
   - Don't use for production!
```

---

## Feature Matrix

### **Auto-Delete After Use:**
- ✅ file.io
- ✅ Notion Native (via file.io bridge)
- ❌ Tunnel (no storage)
- ❌ S3 (manual delete)
- ❌ Cloudflare (manual delete)

### **No Account Needed:**
- ✅ file.io (free tier)
- ✅ Notion Native
- ✅ Tunnel
- ❌ S3
- ❌ Cloudflare

### **Permanent URLs:**
- ⏱️ file.io (14 days or first download)
- ✅ Notion Native (Notion-hosted)
- ❌ Tunnel (expires in minutes)
- ✅ S3
- ✅ Cloudflare

### **No 404 Risk:**
- ✅ file.io (if Notion downloads within 14 days - always does)
- ✅ Notion Native
- ❌ Tunnel (high risk)
- ✅ S3
- ✅ Cloudflare

---

## GUI Quick Reference

### **Mode Selector:**
```
🖼️ Image Upload Mode: [file.io ▼]

[Config panel appears below based on selection]

⚡ [✓] Use Async Verification (10x faster)
```

### **file.io Selected:**
```
┌─────────────────────────────────┐
│ file.io Settings                │
├─────────────────────────────────┤
│ API Key: [Optional_______]      │
│ Expiry:  [14] days              │
│                                 │
│ Files auto-delete after first   │
│ download OR expiry              │
└─────────────────────────────────┘
```

### **Notion Native Selected:**
```
┌─────────────────────────────────┐
│ ⚠️ Notion Native (Experimental) │
├─────────────────────────────────┤
│ Uses file.io bridge             │
│ Notion converts to 'file' type  │
│                                 │
│ [✓] I understand experimental   │
└─────────────────────────────────┘
```

---

## What Gets Saved

Config location: `~/.notion_importer/config.json`

```json
{
  "UPLOAD_MODE": "fileio",
  "FILEIO_API_KEY": "",
  "FILEIO_EXPIRY_DAYS": 14,
  "USE_ASYNC": true,
  
  "S3_BUCKET": "",
  "S3_REGION": "",
  "S3_ACCESS_KEY": "",
  "S3_SECRET_KEY": "",
  
  "CF_BUCKET": "",
  "CF_ACCOUNT_ID": "",
  ...
}
```

**Security note:** Credentials stored in config file. Consider encrypting in production.

---

**For your 1000-page import, I recommend: file.io paid tier ($5/mo) or Cloudflare R2 ($0.50/mo)**

