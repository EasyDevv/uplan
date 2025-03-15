<div align="center">

# 📋uPlan

`uPlan` is a Python package that utilizes AI to generate structured development plans and to-do lists.

[![PyPI version](https://img.shields.io/pypi/v/uplan.svg)](https://pypi.org/project/uplan/)
[![Python Versions](https://img.shields.io/pypi/pyversions/uplan.svg)](https://pypi.org/project/uplan/)
[![License](https://img.shields.io/github/license/username/uplan.svg)](https://github.com/easydevv/uplan/blob/main/LICENSE)

#### English | [한국어](docs/README_KR.md)
</div>

## 📖 Introduction

uPlan automates the development planning process to generate consistent and structured project documentation.

**Problems with existing AI chat-based planning:**
- Questions and methods vary with each session
- Performance degradation due to increased context as conversations accumulate
- Lack of repeatable workflow

**uPlan's Solution:**
- Template-based structured questions
- Efficient resource usage by calling AI only when necessary
- Compatibility ensured through structured TOML format output

## ✨ Key Features

- 🎯 Automatic development plan generation using AI
- ✅ Detailed to-do list creation based on plans
- 📝 Structured output in TOML format
- 🔄 Interactive template customization
- 🛠️ Support for various AI models (OpenAI, Anthropic, Gemini, Deepseek, Ollama, etc.)

## 🔄 How It Works
uPlan operates through the following workflow:

<p align="center">
  <img src="docs/assets/uplan-workflow.png" alt="uplan Workflow" width="700">
</p>

1. **Structured Question Generation** (Code): Creates questions based on user-provided templates
2. **Question Response** (User): Provides answers to structured questions
3. **Plan Generation** (AI): Creates development plans based on user responses
4. **Plan Verification** (User): Reviews and approves the generated plan
5. **To-Do List Generation** (AI): Creates detailed to-do lists based on the approved plan
6. **Final Verification** (User): Final review and approval of the to-do list

This process yields optimal development plans through efficient interaction between code (automation), user (decision-making), and AI (generation).

## 🚀 Quick Start

### Installation
```bash
pip install uplan
```

### Run with Default Settings
```bash
uplan
```
> The default model is ollama/qwq.

### Specify a Particular Model
```bash
uplan --model gemini/gemini-2.0-flash-thinking-exp
```
> Add the `GEMINI_API_KEY` key-value pair to your `.env` file. You can get a free key [here](https://gemini.ai/pricing).

## 🤖 Supported Models

For more details, refer to [MODELS.md](docs/MODELS.md).

## 📋 Detailed Usage

uPlan supports the following command structure:

```
uplan [global options] [command] [command options]
```

### Global Options

| Option | Description | Default |
|------|------|--------|
| `--model` | LLM model to use | `"ollama/qwq"` |
| `--retry` | Maximum retry count for LLM requests | `5` |
| `--category` | Template type | `"dev"` |
| `--input` | Input template folder path | `"./input"` |
| `--output` | Output file save folder | `"./output"` |
| `--debug` | Enable debug mode | `false` |

### Output Files

The following files are generated as a result of execution:

- `plan.toml`: Development plan document
- `todo.toml`: To-do list
- `todo.md`: To-do list in markdown format
- `todo.json`: To-do list in checklist format (including completion status)

### Commands

#### Basic Execution (Plan Creation)

Running without a command operates in plan generation mode:

```bash
uplan [global options]
```

Examples:
```bash
# Run with default model and dev category
uplan

# Specify model and category
uplan --model "ollama/qwq" --category "custom"

# Change input/output paths
uplan --input "./my-templates" --output "./my-plans"
```

> **Note**: If templates don't exist in the specified `--input/[category]` path, they will be automatically initialized.

#### init - Template Initialization

Creates template files:

```bash
uplan init [template] [--force]
```

**Options:**
- `template`: Template name to initialize (default: "dev")
- `--force`: Force overwrite of existing files

Examples:
```bash
# Initialize default dev template
uplan init

# Initialize custom template
uplan init dev_en

# Force overwrite existing template
uplan init dev --force
```

## 🛠️ Template Customization

### plan.toml

A template that includes prompts and Q&A structure for basic planning.

```toml
[prompt]
role = "You are a good code architect and have a good understanding of the development process."
goal = "Create a plan for development."
preferred_language = "English"
instructions = [
    "Review what's already entered in <template>.",
    "<select> can contain multiple contents.",
    "Fill in the <select> parts to create the final deliverable."
]
output_structure = [
    "Write it in JSON format inside a ```json ``` codeblock.",
    "Key values use lowercase"
]
```

**Template Question Structure:**
```toml
[template.project_basics.overview]
ask = "Please describe the overview of the project"
description = "What you are making (app, service, etc.), target platform (web, mobile, desktop, etc.), main users, etc."
required = true
```

| Property | Description |
|------|------|
| `ask` | Basic question |
| `description` | Additional explanation (AI auto-generates if answer not provided) |
| `required` | Whether to present the question (default: false) |

### todo.toml

A template for generating detailed to-do lists based on the plan.

```toml
[template.frontend]
framework = ["<select> (e.g., react, vue, angular)"]
tasks = [
    "<select> (e.g., design login page UI, design sign up page UI, implement user input validation logic)",
]
```
| Property | Description |
| --- | --- |
| `frameworks` | AI specifies based on the content of `output/dev/plan.toml` |
| `tasks` | AI generates specific to-do list based on the content of `output/dev/plan.toml` |

## 👨‍💻 Contributing

Issues and pull requests are welcome!

## 📄 License

See the [LICENSE](LICENSE) file for more details.

---

<div align="center">

Made with ❤️ by [EasyDev](https://github.com/easydevv)

</div>