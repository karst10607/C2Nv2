# Install (macOS + Linux)

## Prereqs
- Python 3.10+
- Recommended: virtualenv

## Dependencies
```bash
pip install -r requirements.txt
```

## Tunnel Provider
- Preferred: cloudflared
  - macOS: `brew install cloudflared`
  - Ubuntu/Debian: `sudo apt-get install cloudflared` (or use Cloudflare repo)
  - CentOS/RHEL: use the Cloudflare RPM
- Fallback: ngrok
  - macOS: `brew install ngrok/ngrok/ngrok`
  - Linux: snap or binary from ngrok.com

If neither is installed, the importer will still run but images may not be accessible to Notion.
