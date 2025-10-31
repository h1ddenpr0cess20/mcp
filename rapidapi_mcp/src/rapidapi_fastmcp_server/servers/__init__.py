from __future__ import annotations
import sys
from pathlib import Path
# Ensure sibling packages (e.g., rapidapi_tools) are importable whether scripts are
# launched from the repository root or the ``python`` directory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))
