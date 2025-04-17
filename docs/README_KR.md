<div align="center">

# 📋uPlan

`uplan`은 AI를 활용하여 개발 계획과 할 일 목록을 구조화된 문서로 생성하는 Python 패키지입니다.

[![PyPI version](https://img.shields.io/pypi/v/uplan.svg)](https://pypi.org/project/uplan/)
[![Python Versions](https://img.shields.io/pypi/pyversions/uplan.svg)](https://pypi.org/project/uplan/)
[![License](https://img.shields.io/github/license/username/uplan.svg)](https://github.com/easydevv/uplan/blob/main/LICENSE)

#### [English](../README.md) | 한국어
</div>

## 📖 소개

<p align="center">
  <a href="https://youtu.be/nWtd01v2w9w" target="_blank">
        <img src="http://img.youtube.com/vi/nWtd01v2w9w/0.jpg" alt="uplan_usage">
    </a>
</p>

uPlan은 개발 계획 수립 과정을 자동화하여 일관되고 구조화된 프로젝트 문서를 생성합니다. 

**기존 AI 채팅 기반 계획 수립의 문제점:**
- 세션마다 질문 내용과 방식이 달라짐
- 대화가 누적될수록 컨텍스트 증가로 인한 성능 저하
- 반복 가능한 워크플로우 부재

**uPlan의 해결책:**
- 템플릿 기반의 구조화된 질문
- 필요한 경우에만 AI 호출하여 자원 사용 효율화
- TOML 형식의 구조화된 출력으로 호환성 확보

## ✨ 주요 기능

- 🎯 AI를 통한 개발 계획 자동 생성
- ✅ 계획 기반의 세부 할 일 목록 생성
- 📝 TOML 형식의 구조화된 출력
- 🔄 대화형 템플릿 커스터마이징
- 🛠️ 다양한 AI 모델 지원 (OpenAI, Anthropic, Gemini, Deepseek, Ollama 등)

## 🔄 작동 방식
uPlan은 다음과 같은 워크플로우를 통해 작동합니다:

<p align="center">
  <img src="assets/workflow.png" alt="uplan Workflow" width="700">
</p>

1. **구조화된 질문 생성** (코드): 사용자 제공 템플릿 기반 질문 구성
2. **질문 응답** (사용자): 구조화된 질문에 답변 제공
3. **계획 생성** (AI): 사용자 답변 기반 개발 계획 생성
4. **계획 확인** (사용자): 생성된 계획 검토 및 승인
5. **할 일 목록 생성** (AI): 승인된 계획 기반 세부 할 일 목록 작성
6. **최종 확인** (사용자): 할 일 목록 최종 검토 및 승인

이 과정을 통해 코드(자동화), 사용자(의사 결정), AI(생성) 간의 효율적인 상호작용으로 최적의 개발 계획을 도출합니다.

## 🚀 빠른 시작

### 설치
```bash
pip install uplan
```

### 기본 설정으로 실행
```bash
uplan
```
> 기본 모델은 ollama/qwq 입니다.

### 특정 모델 지정
```bash
uplan --model gemini/gemini-2.0-flash-thinking-exp
```
>`.env` 파일에 `GEMINI_API_KEY` 키값을 추가해주세요. [여기](https://gemini.ai/pricing)에서 무료로 키를 발급받을 수 있습니다.

## 🤖 지원 모델

자세한 내용은 [MODELS.md](docs/MODELS.md)를 참조하세요.

## 📋 상세 사용법

uPlan은 다음과 같은 명령어 구조를 지원합니다:

```
uplan [전역 옵션] [명령어] [명령어 옵션]
```

### 전역 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--model` | 사용할 LLM 모델 | `"ollama/qwq"` |
| `--retry` | LLM 요청 최대 재시도 횟수 | `5` |
| `--category` | 템플릿 종류 | `"dev"` |
| `--input` | 입력 템플릿 폴더 경로 | `"./input"` |
| `--output` | 출력 파일 저장 폴더 | `"./output"` |
| `--debug` | 디버그 모드 활성화 | `false` |

### 출력 파일

실행 결과로 다음 파일들이 생성됩니다:

- `plan.toml`: 개발 계획 문서
- `todo.toml`: 할 일 목록
- `todo.md`: 마크다운 형식의 할 일 목록
- `todo.json`: 체크리스트 형식의 할 일 목록 (완료 상태 포함)

### 명령어

#### 기본 실행 (계획 생성)

명령어 없이 실행하면 계획 생성 모드로 동작합니다:

```bash
uplan [전역 옵션]
```

예시:
```bash
# 기본 모델과 dev 카테고리로 실행
uplan

# 특정 모델과 카테고리 지정
uplan --model "ollama/qwq" --category "custom"

# 입출력 경로 변경
uplan --input "./my-form" --output "./my-plans"
```

> **참고**: 지정한 `--input/[category]` 경로에 템플릿이 없으면 자동으로 초기화합니다.

#### init - 템플릿 초기화

템플릿 파일을 생성합니다:

```bash
uplan init [form] [--force]
```

**옵션:**
- `form`: 초기화할 템플릿 이름 (기본값: "dev")
- `--force`: 기존 파일을 강제로 덮어쓰기

예시:
```bash
# 기본 dev 템플릿 초기화
uplan init

# 커스텀 템플릿 초기화
uplan init dev_kr

# 기존 템플릿 강제 덮어쓰기
uplan init dev --force
```

## 🛠️ 템플릿 커스터마이징

### plan.toml

기본적인 계획에 대한 프롬프트 및 질답 구성이 포함된 템플릿입니다.

```toml
[prompt]
role = "You are a good code architect and have a good understanding of the development process."
goal = "Create a plan for development."
preferred_language = "English"
instructions = [
    "Review what's already entered in <form>.",
    "<select> can contain multiple contents.",
    "Fill in the <select> parts to create the final deliverable."
]
output_structure = [
    "Write it in JSON format inside a ```json ``` codeblock.",
    "Key values use lowercase"
]
```

**템플릿 질문 구성:**
```toml
[form.project_basics.overview]
ask = "Please describe the overview of the project"
description = "What you are making (app, service, etc.), target platform (web, mobile, desktop, etc.), main users, etc."
required = true
```

| 속성 | 설명 |
|------|------|
| `ask` | 기본 질문 |
| `description` | 추가 설명 (답변 미입력시 AI가 자동 생성) |
| `required` | 질문 제시 여부 (기본값: false) |

### todo.toml

계획을 바탕으로 세부 할 일 목록을 생성하기 위한 템플릿입니다.

```toml
[form.frontend]
framework = ["<select> (e.g., react, vue, angular)"]
tasks = [
    "<select> (e.g., design login page UI, design sign up page UI, implement user input validation logic)",
]
```
| 속성 | 설명 |
| --- | --- |
| `frameworks` | `output/dev/plan.toml`의 내용을 기준으로 AI가 지정 |
| `tasks` | `output/dev/plan.toml`의 내용을 기준으로 구체적인 할 일 목록을 AI가 생성 |

## 👨‍💻 기여하기

이슈와 풀 리퀘스트를 환영합니다!

## 📄 라이센스

자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

<div align="center">

Made with ❤️ by [EasyDev](https://github.com/easydevv)

</div>