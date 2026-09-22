#!/usr/bin/env python3
"""Repository entry point. Open this folder in Codex, or run python xr.py doctor."""
from pathlib import Path
import sys
scripts=Path(__file__).resolve().parent/'.agents/skills/xactimate-reconcile/scripts'
if not scripts.is_dir():
    raise SystemExit('Skill resources are missing. Extract the complete repository ZIP including .agents.')
sys.path.insert(0,str(scripts))
from xactimate_reconcile.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
