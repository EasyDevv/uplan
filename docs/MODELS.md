## 🤖 Supported models

We recommend models with Reasoning capabilities. Follow [Litellm format](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json).

### OpenAI
```bash
uplan --model o3-mini
```
```env
OPENAI_API_KEY=sk-your-key
```

### Anthropic
```bash
uplan --model claude-3-7-sonnet-latest
```
```env
ANTHROPIC_API_KEY=sk-your-key
```

### Gemini
```bash
uplan --model gemini/gemini-2.0-flash-thinking-exp
```
```env
GEMINI_API_KEY=sk-your-key
```

### Deepseek
```bash
uplan --model deepseek/deepseek-reasoner
```
```env
DEEPSEEK_API_KEY=sk-your-key
```

### OpenRouter
```bash
uplan --model openrouter/deepseek/deepseek-r1
```
```env
OPENROUTER_API_KEY=sk-your-key
```

### Ollama
```bash
uplan --model ollama/deepseek-r1:32b
```