"""Tests use the exported skill, with an explicit local development override."""
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
SKILL=Path(os.environ.get('XR_DEV_SKILL',ROOT/'.agents/skills/xactimate-reconcile'))
sys.path.insert(0,str(SKILL/'scripts'))
