#!/usr/bin/env python3
"""Portable skill entry point; no installation required for the stdlib core."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from xactimate_reconcile.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
