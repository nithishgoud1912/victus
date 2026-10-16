"""Freeze support must run before application imports or argument parsing."""

import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if sys.argv[1:2] == ["mcp-note-server"]:
        from victus.adapters.mcp.reference_server import main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        main()
    else:
        from victus.cli import main

        main()
