# Contributing to Senapati

## Getting Started

1. Fork the repo
2. Clone your fork
3. Create a feature branch

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run in debug mode
python -m app.main --debug
```

## Adding a Tool

1. Add tool to appropriate MCP in `app/tools/`
2. Register in `agent.py._execute_tool()`
3. Add to `playbook.py` TOOL_ROUTING_PROMPT

## Adding a Prompt

1. Add prompt template to `app/prompts/playbook.py`
2. Add builder function in `app/prompts/__init__.py`
3. Integrate in `app/core/agent.py`

## Submitting PRs

- Run tests: `pytest tests/`
- Update docs if needed
- Describe changes in PR template

## Code Style

- Use Black for formatting
- Type hints where possible
- Docstrings for public APIs