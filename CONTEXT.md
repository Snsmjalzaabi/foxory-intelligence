# FOXORY workspace context

Chat uses relevant saved workspace information by default. In Settings, turn **Use saved workspace context** off when you want only the current conversation. Preferences stay scoped to this browser account/workspace.

**Workspace knowledge** previews retrieved memory, projects, business opportunities, contacts, drafts, tasks, imported source/document passages, saved artifacts, completed reports and earlier conversations. Approved agent facts can be retrieved; generated agent summaries are excluded from shared chat retrieval. Context never reads arbitrary host files, private settings, login sessions, approvals or another workspace.

Each reply’s **Context used** section records the actual saved excerpts and number of history messages passed. Retrieval is bounded: up to 500 recent records, 12 matching full documents and 30 matching earlier messages are candidates; at most 10 ranked excerpts fit the prompt. Chat history is packed against the selected window instead of a fixed 20-message limit. Matching source passages beyond the beginning of a long document can be found. Increase the context window for broader coverage, with additional VRAM/time cost. This is retrieval, not an assertion that every saved byte was considered.

The current question takes precedence over old notes and AI drafts. Context is untrusted data, never instructions. Retrieved assistant statements and model-written business offers remain unverified. Verify pricing, customer demand, dates, capability, citations and delivery promises yourself.

Agents retain their grants. The new **FOXORY Workspace Navigator** template uses **workspace.context**, which requires explicit **workspace.read** permission. That permission gives broad read access to the current workspace, including documents and conversation history; it grants no host filesystem access, writes, sending, publishing or other workspace access. The installed Navigator is configured for the owner’s requested context use. Existing specialist grants remain unchanged.

Repository reviews and deep research keep their separately selected source/evidence scope. Context retrieval does not silently convert old drafts into verified research sources, and a repository URL alone remains insufficient evidence.
