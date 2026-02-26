import sys
import os

# Add src/ to sys.path so absolute imports (core.*, doc_types.*, etc.) work.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_project_root, "src"))
sys.path.insert(0, _project_root)
