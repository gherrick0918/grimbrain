"""Simple TUI placeholder for future development."""

import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description="Grimbrain TUI preview")
    parser.add_argument("--search", help="Search for a monster or spell")
    parser.add_argument("--scene", help="Start a scene", default=None)
    parser.add_argument("--log", help="Write logs to file", default="logs/tui.log")
    parser.parse_args(argv)
    # Real TUI deferred; this placeholder just validates CLI usage.
    return 0


if __name__ == "__main__":  # pragma: no cover
    main()
