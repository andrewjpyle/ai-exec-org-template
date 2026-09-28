"""Load a roster: your `exec_roles.py` if it exists, else the Acme example."""

from __future__ import annotations

import importlib
import importlib.util
import os
from pathlib import Path
from types import ModuleType

from .registry import Registry


def load_roles(path: str | None = None) -> ModuleType:
    """Import a roles module fresh. Order: `path`, $EXEC_ROLES, ./exec_roles.py, the example."""
    Registry.clear()
    target = path or os.environ.get("EXEC_ROLES") or ("exec_roles.py" if Path("exec_roles.py").exists() else None)
    if target:
        spec = importlib.util.spec_from_file_location("exec_roles", target)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load roles from {target}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    from . import roles

    return importlib.reload(roles)
