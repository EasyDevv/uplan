from pathlib import Path
import shutil

from uplan.models.todo import TodoModel

# Configuration paths
DEFAULT_CONFIG_DIR = Path.cwd() / "input"
TEMPLATES_DIR = Path(__file__).parent / "templates"
DEFAULT_TEMPLATE_SUBDIR = "dev"


def initialize(
    force: bool = False, template_dir: str = DEFAULT_TEMPLATE_SUBDIR
) -> None:
    """Initialize configuration directory by copying all files from specified template directory"""
    try:
        source_dir = TEMPLATES_DIR / template_dir
        if not source_dir.exists():
            raise ValueError(f"Template directory '{template_dir}' not found")

        target_dir = DEFAULT_CONFIG_DIR / template_dir

        # Check if target directory exists and whether to overwrite
        if target_dir.exists():
            if not force:
                print(f"{target_dir} confirmed.")
                return
            shutil.rmtree(target_dir)

        # Copy entire template directory
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target_dir)
        print(f"Created {target_dir} from template '{template_dir}'")

    except Exception as e:
        print(f"Initialization failed: {str(e)}")
        raise


def validate_templates(category: str) -> None:
    """Validate TOML files in the input directory"""
    input_dir = Path(f"./input/{category}")

    try:
        if not input_dir.exists():
            raise ValueError(f"Input directory '{category}' not found")

        # Find all .toml files in the directory
        for file_path in input_dir.glob("*.toml"):
            try:
                with open(file_path, "rb") as f:
                    import tomllib  # Import here since only needed for validation

                    data = tomllib.load(f)

                # Additional validation for todo.toml
                if file_path.name == "todo.toml":
                    TodoModel(**data)

                print(f"{file_path} is valid")
            except Exception as e:
                print(f"Warning: Failed to validate {file_path}: {str(e)}")

    except Exception as e:
        print(f"Validation failed: {str(e)}")
        raise
