#!/usr/bin/env python3
"""Convenience wrapper for CLI commands.

This script provides a simple entry point for running CLI commands.

Usage:
    python cli.py --help
    python cli.py users create
    python cli.py users list
    python cli.py users delete <email>

This is equivalent to:
    python -m cli --help
    python -m cli users create
    python -m cli users list
"""

if __name__ == "__main__":
    from cli import main

    main()
