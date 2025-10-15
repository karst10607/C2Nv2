import argparse
import sys
from pathlib import Path
from typing import Optional
from rich import print

from .config import AppConfig
from .image_server import StaticServer, Tunnel
from .html_parser import parse_html_file
from .transform import to_notion_blocks
from .notion_client import Notion


def main(argv: Optional[list] = None):
    ap = argparse.ArgumentParser(description="Import Confluence HTML export into Notion")
    ap.add_argument('--source-dir', default=None)
    ap.add_argument('--run', action='store_true', help='Perform writes to Notion')
    ap.add_argument('--dry-run', action='store_true', help='Parse and plan only')
    ap.add_argument('--max-columns', type=int, default=6)
    ap.add_argument('--parent-id', default=None)
    args = ap.parse_args(argv)

    cfg = AppConfig.load()
    source_dir = args.source_dir or cfg.source_dir
    if not source_dir:
        print('[red]Source directory not set. Use GUI or --source-dir.[/red]')
        return 2

    # Start local static server and tunnel
    srv = StaticServer(Path(source_dir))
    srv.start()
    tunnel = Tunnel(srv.base_url())
    public = tunnel.start()
    print(f"[green]Serving images at:[/green] {public}")

    # Notion
    token = cfg.notion_token
    parent_id = args.parent_id or cfg.parent_id
    if args.run:
        if not token:
            print('[red]NOTION_TOKEN missing. Set via GUI or env.[/red]')
            return 2
        if not parent_id:
            print('[yellow]PARENT_ID missing. You can run --dry-run to preview or set it via GUI.[/yellow]')
            return 2
        notion = Notion(token)
    else:
        notion = None  # type: ignore

    # Walk HTML files
    mapping_path = Path(__file__).resolve().parents[1] / 'out' / 'mapping.jsonl'
    mapping_path.parent.mkdir(parents=True, exist_ok=True)

    html_files = sorted(Path(source_dir).rglob('*.html'))
    print(f"Found {len(html_files)} html files")

    for f in html_files:
        ast = parse_html_file(f)
        title = ast['title']
        blocks = to_notion_blocks(
            ast, 
            image_base_url=public, 
            max_cols=args.max_columns,
            preserve_table_layout=True,
            min_column_height=3
        )
        print(f"- {f.name} -> {title} ({len(blocks)} blocks)")
        if args.run and notion:
            page_id = notion.create_page(parent_id, title)
            notion.append_blocks(page_id, blocks)
            line = f"{{\"source\":\"{str(f)}\",\"page_id\":\"{page_id}\"}}\n"
            with open(mapping_path, 'a', encoding='utf-8') as fp:
                fp.write(line)

    tunnel.stop()

if __name__ == '__main__':
    sys.exit(main())
