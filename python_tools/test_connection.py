#!/usr/bin/env python3
import os
import sys
import traceback


def main():
    try:
        token = os.environ.get("NOTION_TOKEN") or (sys.argv[1] if len(sys.argv) > 1 else None)
        if not token:
            print("ERROR: NOTION_TOKEN is missing", file=sys.stderr)
            return 1
        from notion_client import Client
        client = Client(auth=token)
        me = client.users.me()
        print("OK")
        print(f"User ID: {me.get('id')}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
