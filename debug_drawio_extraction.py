#!/usr/bin/env python3
"""Debug Draw.io name extraction"""
from pathlib import Path
from bs4 import BeautifulSoup
import re

def debug_extraction():
    html_path = Path("EP/2753397032.html")
    html = html_path.read_text(encoding='utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'lxml')
    
    # Find Draw.io containers
    containers = soup.find_all('div', class_='ap-container')
    
    for i, container in enumerate(containers):
        if 'diagramly' not in container.get('id', ''):
            continue
            
        print(f"\nContainer {i+1}: {container.get('id')}")
        
        # Find script
        script = container.find('script')
        if script and script.string:
            script_content = script.string
            
            # Try to find productCtx
            product_ctx_match = re.search(r'"productCtx"\s*:\s*"([^"]+)"', script_content)
            if product_ctx_match:
                ctx_str = product_ctx_match.group(1)
                print(f"Found productCtx (length: {len(ctx_str)})")
                
                # Look for diagramName variations
                patterns = [
                    r'diagramName\\":\\"([^"\\]+)',
                    r'"diagramName":"([^"]+)"',
                    r'diagramName=([^&]+)',
                    r'diagramName%22%3A%22([^%]+)%22',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, ctx_str)
                    if match:
                        print(f"  Pattern '{pattern}' found: {match.group(1)}")
                
                # Show a sample around diagramName
                if 'diagramName' in ctx_str:
                    idx = ctx_str.find('diagramName')
                    print(f"  Context around 'diagramName': ...{ctx_str[max(0,idx-20):idx+50]}...")
            
            # Look for aspectHash
            aspect_match = re.search(r'"aspectHash"\s*:\s*"([^"]+)"', script_content)
            if aspect_match:
                print(f"  aspectHash: {aspect_match.group(1)}")

if __name__ == "__main__":
    debug_extraction()








