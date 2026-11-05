# FOXORY user guide

How to use each part of FOXORY 8. Commands run in the FOXORY folder; after changing `.env`,
apply it with `python3 scripts/foxory.py start`.

## Models

**Settings → Recommended local models** lists small, free models with their download size,
estimated memory, context length and license. **Starter set for this PC** picks one model per
job that fits your hardware (or the smallest ones when the hardware has not been measured).
Download or uninstall with one click; any other Ollama model can be added by name.

Leave chat on **Auto · task-aware**: coding, analysis, writing and image questions go to the
installed model best suited to them, within your memory limits. **Settings → Model quality on
this PC → Check installed models** asks each model eight short, rule-checked questions; Auto
then prefers the models that scored well for each kind of request.

The optional CPU companion (`python3 scripts/foxory_ai.py enable`) adds a small llama.cpp model
for quick replies without using the GPU. Eco, balanced and quality modes are in
**Tools & context → AI runtime**.

## Chat, files and images

Press **+** to attach up to eight documents (PDF, DOCX, XLSX, CSV, TXT, MD, JSON) or up to
four images (PNG, JPEG, WebP) to a message. Images need a model that can read them, such as
`gemma3:4b`; FOXORY tells you if none is installed. Generated documents and source files open
in a reader beside the conversation, with Markdown, PDF, DOCX or ZIP downloads.

Chat can also act: create projects and skills, schedule routines ("every Monday at 9, draft a
weekly summary") and write artifacts. Actions are recorded and shown under the reply.

## Voice

`python3 scripts/foxory_voice.py enable` installs local speech-to-text: whisper.cpp with the
multilingual Whisper small model (190 MB, MIT), verified by hash. Then use the microphone next
to **+**: speak, press stop, check the text and send. Replies to spoken questions are read
aloud with your system's voices, and every reply has **Read aloud**. Audio never leaves your
computer and is not stored.

## Documents and research

**Documents** answers questions from your uploaded files with references to the passages it
used. Install `nomic-embed-text` and index documents for semantic search. **Deep Research**
searches the web (through the bundled private SearXNG), reads sources and writes a cited
report. **Model Council** has several models answer independently, then compares them.

### Watched folder

Set `FOXORY_WATCH_DIR=/absolute/path` in `.env`. Supported documents in that folder and its
subfolders sync into the local workspace every minute: new and changed files are imported,
deleted files removed. The folder is mounted read-only, symbolic links and hidden files are
skipped, and every file goes through the isolated parser. Up to 500 files of 10 MiB each.

## Agents, projects and automation

**AI Workforce** creates agents from templates with explicit tools and permissions. Tasks run
as bounded plans with step, model-call and time budgets; writes wait for your approval.
**Projects** keep a body of work (writing or business) with its facts, chapters, actions,
deliverables and linked sources; project chats see only that project.

**Automation** runs routines for selected projects on a schedule, within a daily job budget,
and maintains reusable data-only **skills** that are tested before they activate. Everything it
produces is a draft for you to review. Every add has a matching remove: projects, items,
skills, members, workspaces and models can be deleted from the same screens.

## Notifications

The bell in the header lists your tasks that finished, failed or need approval in the last
seven days; **Enable desktop notifications** in that panel notifies you while FOXORY is open.
For your phone, run a self-hosted [ntfy](https://ntfy.sh) server and set
`FOXORY_NTFY_URL=http://your-ntfy-host/your-topic`. Pushes contain only the task title and
status. A public ntfy server would receive those titles, so host your own.

## On your phone

With [Tailscale](https://tailscale.com) installed and signed in on the computer and phone, run
`python3 scripts/foxory_phone.py enable`. It serves FOXORY over private HTTPS to your own
devices only and prints the address. Open it on the phone and choose **Add to Home Screen** or
**Install app**. `status` and `disable` check or undo it. The app caches only its own files,
never your data.

## Accounts and workspaces

The first account is the installation owner. Workspaces keep data separate; administrators
add or remove members with admin, editor or viewer roles. Viewers can read but not change
anything.

## Profiles and appearance

`profiles/default.json` sets the machine name shown in the app, time zone, currency, default
models, the assistant's default instructions and the welcome-screen starters. Copy it to
`profiles/personal.json` and edit it, or select another file with `FOXORY_PROFILE=<name>`.
Invalid profiles stop startup with a clear message. Colours, branding, navigation and layout are
editable under **Appearance**.

## Backups and updates

`python3 scripts/foxory_backup.py` writes a private recovery set (database, uploads, settings)
to `backups/`; `python3 scripts/verify_backup_restore.py backups/<folder>` proves it restores
without touching your live data. Keep backups private: they contain your data and secrets.
Signed local updates and the self-review lab are described in
[docs/DEPLOYMENT.md](DEPLOYMENT.md) and [ARCHITECTURE.md](../ARCHITECTURE.md).
