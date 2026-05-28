from __future__ import annotations

import argparse
import os

from fire_api.server import run_server


def main() -> None:
    default_port = int(os.getenv("PORT", "8000"))
    default_host = os.getenv("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")

    parser = argparse.ArgumentParser(description="Local API for deterministic fire-separation calculations.")
    parser.add_argument("--host", default=default_host)
    parser.add_argument("--port", default=default_port, type=int)
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
