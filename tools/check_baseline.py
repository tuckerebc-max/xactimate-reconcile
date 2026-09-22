"""Run the unchanged C tests from their original import root."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
raise SystemExit(subprocess.call([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT/'baseline_c'))
