import sys
import importlib.util
from pathlib import Path
import pytest


def test_python_path():
    assert len(sys.path) > 0, "Python path should not be empty"


def test_working_directory():
    project_root = Path(__file__).resolve().parent.parent
    assert Path.cwd() == project_root, (
        f"Working directory should be project root, got {Path.cwd()}"
    )


def test_root_import():
    try:
        import uplan

        assert uplan.__file__ is not None
    except ImportError as e:
        pytest.fail(f"Failed to import root: {e}")


@pytest.mark.parametrize(
    "module_name",
    [
        "uplan.main",
        "uplan.process",
        "uplan.question",
        "uplan.models.todo",
        "uplan.utils.display",
    ],
)
def test_module_imports(module_name):
    try:
        module = importlib.import_module(module_name)
        assert module.__file__ is not None
    except ImportError as e:
        pytest.fail(f"Failed to import {module_name}: {e}")
