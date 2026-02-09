# Upload Modes Guide - v3.1.0

## Overview

The importer now supports **5 different image upload modes** to solve the 404 problem.

---

## Quick Comparison

| Mode | Setup | Cost | Speed | Reliability | Auto-Cleanup | Best For |
|------|-------|------|-------|-------------|--------------|----------|
| **Notion Native** | None | Free | Medium | Medium | ✅ YES | Corporate employee/ generla users without high permission|
| **AWS S3** | AWS account | $1-5/mo | Fast | Very High | ✅ Yes | Ease of migratione |
| **GCS** | Company GCP account | $?/mo | Fast | Very High | ✅ yes | Security-conscious |


---

## Detailed Mode Explanations


---

### 📦 **Notion Native (Default, need Notion token issued by company)**

**How it works:**
```
1. Using Notion's offical fle uploading api
2. Send URL to Notion as 'external' type
3. Image is Notion-hosted forever

```

**Pros:**
- ✅ Images become 'file' type (not 'external')
- ✅ Hosted by Notion permanently. No extra cost (unless you're moving awasy from Notion)
- ✅ Safe, no need for external services & cdn temp exposure. 

**Cons:**
- ⚠️ **Critical** - many domain knowledge spaces have important files > 20mb (qa / mobile feature demo videos, huge diagrams or slides, pdf)
- ⚠️ Need apply for mercari notion token first, and it's only working in sandbox now 
- 🟡 File size limitation (20mb) 

**When to use:**
- ✅ Want Notion-hosted images
- ✅ Willing to test experimental features
- ✅ Prefer 'file' type over 'external'

**Setup:**
```
1. Select "Notion Native"
2. Fill in Notion token and target Notino page id
```

---

### ☁️ **AWS S3 (security issues, disabled)**

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

## Feature Matrix

### **Auto-Delete After Use:**
- ✅ Notion Native (via Notion api)
- ✅ S3 (usually set as 24hr for notion api to fetch)
- ✅ GCS (usually set as 24hr for notion api to fetch)

### **No Account Needed:**
- ✅ Notion Native
- ❌ AWS S3
- ❌ GCP GCS

### **Permanent URLs:**
- ✅ Notion Native (Notion-hosted)
- ✅ S3 (Can be, but will not be used)
- ✅ Cloudflare (Can be, but will not be used)

### **No 404 Possibility:**
- ✅ Notion Native
- ✅ S3 (temp public)
- ✅ GCS (when temp public)

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

**For over 1000-page import, recommend using cdn to save effort and time esp. if there're larger files **

