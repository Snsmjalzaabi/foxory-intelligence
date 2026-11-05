# FOXORY Intelligence 8.0

**A private AI workspace that runs entirely on your own computer, with free local models.**
No cloud account, no subscription, no data leaving your machine for inference.

FOXORY gives you chat, document questions, web research, a council of models, bounded AI
agents, scheduled routines, image reading and voice. Everything runs on local models through
[Ollama](https://ollama.com) and an optional CPU [llama.cpp](https://github.com/ggml-org/llama.cpp)
companion.

## Quick start (Linux)

You need Docker Engine with Compose v2 and Python 3.11 or newer. An NVIDIA GPU is optional:
FOXORY uses it automatically when Docker can, and runs on the CPU otherwise.

```sh
git clone https://github.com/Snsmjalzaabi/foxory-intelligence.git
cd foxory-intelligence
python3 scripts/foxory.py doctor
python3 scripts/foxory.py start
```

The first start creates a private `.env` with random secrets and builds the containers
(internet needed for that first build). Then:

1. Open **http://localhost:3636**.
2. Create your administrator account with the `FOXORY_TOKEN` value from `.env`.
3. In **Settings → Recommended local models**, download a starter set sized for your
   computer (for example `qwen3:4b` for chat and `nomic-embed-text` for document search).

`python3 scripts/foxory.py status` shows the services; `python3 scripts/foxory.py stop`
stops them and keeps your data.

## What you can do

| Feature | Where |
| --- | --- |
| Chat with automatic, task-aware model choice | Chat |
| Attach files and images; ask about photos and screenshots | Chat (+ button) |
| Speak your message and hear replies | Chat (microphone), after enabling voice |
| Questions grounded in your documents, with references | Documents |
| Web research with retrieved, checked sources | Deep Research |
| Several models answer independently, then compare | Model Council |
| Agents with explicit tools, step limits and approval gates | AI Workforce |
| Projects for writing and business work, with knowledge and deliverables | Projects |
| Scheduled routines, reusable skills and project automation | Automation |
| Notifications for finished tasks, on the desktop or your phone | Bell icon |
| A watched folder whose documents stay in sync | Settings |
| Measure which installed model answers best on your computer | Settings |

The [user guide](docs/GUIDE.md) explains each feature and the optional add-ons.

## Optional add-ons

```sh
python3 scripts/foxory_ai.py enable      # small CPU model for quick replies
python3 scripts/foxory_voice.py enable   # local speech-to-text (whisper.cpp)
python3 scripts/foxory_phone.py enable   # private HTTPS on your phone via Tailscale
```

A watched folder, phone push notifications and other settings are described in the
[guide](docs/GUIDE.md) and [CONFIGURATION.md](CONFIGURATION.md).

## Make it yours

Names, time zone, currency, default models, the assistant's default instructions and the
welcome-screen starters come from a profile. Copy `profiles/default.json` to
`profiles/personal.json` and edit it; FOXORY uses `personal.json` automatically when it
exists. Appearance (colours, layout, branding) is editable in the app.

## Privacy and safety

- Models run locally. Web research contacts public search engines and websites only when you
  use it.
- The app listens only on this computer (`127.0.0.1`). Phone access uses Tailscale, so only
  your own signed-in devices can reach it.
- Accounts use Argon2id passwords, server-side sessions and CSRF protection; workspaces keep
  data separate.
- Agents only use tools you grant, within step and time budgets; actions that change data
  need your approval. Retrieved content is treated as untrusted.
- Uploaded documents are parsed in an isolated, network-less process.
- Optional code execution runs in a separately installed sandbox and is off by default.

See [SECURITY.md](SECURITY.md) for reporting and design details and
[ARCHITECTURE.md](ARCHITECTURE.md) for how the parts fit together.

## Documentation

[User guide](docs/GUIDE.md) · [Installation](INSTALLATION.md) ·
[Configuration](CONFIGURATION.md) · [Troubleshooting](TROUBLESHOOTING.md) ·
[Development](DEVELOPMENT.md) · [Changelog](CHANGELOG.md) · [Roadmap](ROADMAP.md) ·
[Project status](PROJECT_STATUS.md)

## License

Apache-2.0. Third-party components keep their own licenses; see
[THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt). Model weights are downloaded separately
under their own licenses, which the model list in Settings shows.
