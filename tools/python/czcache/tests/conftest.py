"""Make the czcache scripts importable from tests without installing them.

The modules are flat scripts run in place (see the package README), so the test run needs
the package directory on sys.path exactly the way `python build.py` gets it for free.
"""
import sys
from pathlib import Path

CZCACHE = Path(__file__).resolve().parents[1]
if str(CZCACHE) not in sys.path:
    sys.path.insert(0, str(CZCACHE))
