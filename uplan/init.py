# uplan/init.py 의 전체 내용 (aiofiles 적용)

from pathlib import Path
import asyncio
import httpx
import logging
import shutil
import tomllib
import aiofiles  # aiofiles 추가

from uplan.models.todo import TodoModel

# 로깅 설정 (rich.logging 사용 권장)
# TODO: rich.logging으로 전환 고려
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Configuration Paths ---
DEFAULT_CONFIG_DIR = Path.cwd() / "input"
FORMS_DIR = Path(__file__).parent / "forms"
DEFAULT_FORM_SUBDIR = "dev"

# --- LiteLLM Model Data ---
LITELLM_MODELS_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
LITELLM_MODELS_FILENAME = "litellm_models.json"
LITELLM_MODELS_PATH = DEFAULT_CONFIG_DIR / LITELLM_MODELS_FILENAME


async def _download_file_async(url: str, dest_path: Path) -> None:
    """지정된 URL에서 파일을 비동기적으로 다운로드하여 dest_path에 비동기적으로 저장합니다."""
    logger.info(f"Downloading {url} to {dest_path}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # aiofiles를 사용하여 비동기적으로 파일 쓰기
        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(response.content)  # await 추가
        logger.info(f"Successfully downloaded and saved {dest_path.name}")

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error downloading {url}: {e.response.status_code} - {e.response.text}"
        )
        raise
    except httpx.RequestError as e:
        logger.error(f"Network error downloading {url}: {e}")
        raise
    except IOError as e:  # aiofiles도 IOError 발생 가능
        logger.error(f"File error writing to {dest_path}: {e}")
        raise
    except Exception as e:
        logger.exception(f"An unexpected error occurred during download of {url}")
        raise


def initialize(force: bool = False, form_dir: str = DEFAULT_FORM_SUBDIR) -> None:
    """
    구성 디렉토리를 초기화하고 LiteLLM 모델 가격/컨텍스트 창 파일을 다운로드합니다.

    Args:
        force (bool): 대상 디렉토리나 파일이 이미 존재하는 경우 덮어쓸지 여부.
        form_dir (str): 사용할 폼 디렉토리 이름 (기본값: 'dev').
    """
    logger.info(f"Initializing configuration (force={force}, form_dir='{form_dir}')...")

    # 1. 폼 파일 복사 (동기 작업)
    try:
        source_dir = FORMS_DIR / form_dir
        if not source_dir.is_dir():
            raise ValueError(
                f"Form directory '{form_dir}' not found or is not a directory in {FORMS_DIR}"
            )

        target_dir = DEFAULT_CONFIG_DIR / form_dir

        if target_dir.exists():
            if not force:
                logger.info(
                    f"Form directory {target_dir} already exists. Skipping copy."
                )
            else:
                logger.info(
                    f"Removing existing form directory {target_dir} due to force=True."
                )
                shutil.rmtree(target_dir)
                logger.info(
                    f"Copying form directory from {source_dir} to {target_dir}..."
                )
                shutil.copytree(source_dir, target_dir)
                logger.info(f"Recreated {target_dir} from form '{form_dir}'")
        else:
            logger.info(f"Copying form directory from {source_dir} to {target_dir}...")
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_dir, target_dir)
            logger.info(f"Created {target_dir} from form '{form_dir}'")

    except Exception as e:
        logger.exception(f"Form initialization failed for form_dir '{form_dir}'")

    # 2. LiteLLM 모델 정보 파일 다운로드 (비동기 작업 호출)
    try:
        if LITELLM_MODELS_PATH.exists() and not force:
            logger.info(
                f"{LITELLM_MODELS_PATH.name} already exists. Skipping download."
            )
        else:
            if LITELLM_MODELS_PATH.exists() and force:
                logger.info(
                    f"Removing existing {LITELLM_MODELS_PATH.name} due to force=True."
                )
                try:
                    LITELLM_MODELS_PATH.unlink()
                except OSError as e:
                    logger.error(
                        f"Error removing existing file {LITELLM_MODELS_PATH}: {e}"
                    )

            logger.info("Starting download of LiteLLM models file...")
            try:
                # initialize 함수 자체가 동기 함수이므로 asyncio.run 사용 유지
                asyncio.run(
                    _download_file_async(LITELLM_MODELS_URL, LITELLM_MODELS_PATH)
                )
            except RuntimeError as e:
                if "cannot run loop while another loop is running" in str(e):
                    logger.warning(
                        "Asyncio loop already running. Consider restructuring if initialize is called from async context."
                    )
                else:
                    raise
            except Exception as download_error:
                logger.error(
                    f"Error during LiteLLM model file download: {download_error}"
                )

    except Exception as e:
        logger.exception(
            "An error occurred during the LiteLLM model file download process."
        )

    logger.info("Initialization process completed.")


def validate_forms(category: str) -> None:
    """입력 디렉토리의 TOML 파일 유효성을 검사합니다."""
    input_dir = DEFAULT_CONFIG_DIR / category
    logger.info(f"Validating TOML files in directory: {input_dir}")

    try:
        if not input_dir.is_dir():
            raise ValueError(
                f"Input directory '{input_dir}' not found or is not a directory."
            )

        toml_files_found = False
        for file_path in input_dir.glob("*.toml"):
            toml_files_found = True
            logger.debug(f"Validating file: {file_path}")
            try:
                # TOML 파일 읽기는 동기적으로 처리해도 무방할 수 있음
                # 만약 매우 큰 TOML 파일이 예상된다면 aiofiles 사용 고려
                with open(file_path, "rb") as f:
                    data = tomllib.load(f)
                logger.info(f"Successfully parsed TOML file: {file_path.name}")

                if file_path.name == "todo.toml":
                    logger.debug(
                        f"Performing specific validation for {file_path.name} using TodoModel..."
                    )
                    try:
                        TodoModel(**data)
                        logger.info(
                            f"Pydantic validation successful for {file_path.name}"
                        )
                    except Exception as pydantic_error:
                        logger.error(
                            f"Pydantic validation failed for {file_path.name}: {pydantic_error}"
                        )

            except tomllib.TOMLDecodeError as e:
                logger.error(f"Invalid TOML format in {file_path}: {e}")
            except IOError as e:
                logger.error(f"Could not read file {file_path}: {e}")
            except Exception as e:
                logger.exception(
                    f"An unexpected error occurred while validating {file_path}"
                )

        if not toml_files_found:
            logger.warning(f"No .toml files found in directory: {input_dir}")

    except ValueError as e:
        logger.error(f"Validation failed: {e}")
        raise
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during the validation process for category '{category}'"
        )


# 스크립트로 직접 실행될 경우 초기화 함수 호출 (테스트용)
if __name__ == "__main__":
    print("Running initialization directly (for testing)...")
    initialize()
    validate_forms("dev")
    print("Direct execution finished.")
