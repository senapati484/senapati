# Senapati ✨

> *"Not a chatbot. A presence on your computer."*

Local-first · Voice-first · Always running · Full system access

![Demo](https://media.giphy.com/media/placeholder.gif)

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/your-username/senapati/main/install.sh | bash
```

After install:
- Say **"Hey Senapati"** to activate
- Or run `senapati --tui` for terminal UI

## Features

- 🎤 **Voice First** — "Hey Senapati, open Chrome and set volume to 60%"
- 🧠 **Local LLM** — Qwen3-2.5B via MLX (Apple Silicon) or GGUF
- 📖 **Memory** — Remembers facts, tasks, past conversations
- 🔧 **Tool Access** — Open apps, run git, read files, OCR screen
- 🌅 **Morning Brief** — Daily summary of calendar, git, tasks
- 🔔 **Notifications** — Triages and reads important ones aloud
- 🎯 **Menu Bar** — macOS menu bar app with quick controls

## Commands

| Command | Description |
|---------|-------------|
| `senapati` | Start daemon (default) |
| `senapati --tui` | Terminal UI with orb |
| `senapati --brief` | Run morning brief |
| `senapati --mini` | Minimal HUD mode |
| `senapati --debug` | Debug logging |

## Wake Words

- "Hey Senapati" — primary
- "Hey Buddy" — alternative
- "Senapati" — single word

## Tech Stack

| Layer | Technology |
|-------|------------|
| LLM | MLX-LM (Apple Silicon) / llama.cpp |
| Model | Qwen3-2.5B Q4 |
| STT | faster-whisper small |
| TTS | Piper |
| UI | Textual |
| Memory | SQLite + FTS5 |
| Tools | FastMCP |

## Requirements

- macOS (Apple Silicon recommended) or Linux
- Python 3.10+
- 8GB RAM minimum (16GB recommended)

## Documentation

- [Architecture](docs/architecture.md)
- [Plugin Guide](docs/plugin-guide.md)
- [Fine-tuning](docs/fine-tuning.md)

## License

MIT — See [LICENSE](LICENSE)