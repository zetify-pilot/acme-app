# MCP tools

Every tool Fleet's MCP address serves to a session. Use it to see what an agent can do through Fleet, or which API route stands behind a tool.

Each row carries the first sentence of the description the session itself reads, and the tools API route the tool calls under `/api/tools/v1`.

## Tools

| Tool | What it does | Calls |
|---|---|---|
| `ask` | Ask a person to decide something, and wait for their answer. | `POST /ask`, `GET /bundles/{bundle_id}/viewer` |
| `record_answer` | Record a person's answers to a question set that `ask` returned unanswered. | `POST /ask/{question_set_id}/answer` |
| `get_issue` | Read one item by KEY-123, Fleet id INTAKE-10 or wk_...: kind, `lane` {name, repo}, position, `levers` (the moves and comment you may make now), `parked` {reason, question, since, parkId}, blockers/blocks, body, newest comments, recorded decisions, PR links with CI facts. | `GET /issues/{key}` |
| `queue` | List what waits on a person, as compact briefs, in drain order: `Needs My Decision` (blocked-decision, failed) and `My Action Queue` (blocked-action, awaiting-merge), each with its question, age, how many issues it blocks and whether it holds a PRD. | `GET /queue` |
| `capabilities` | Which facets (position, priority, labels, blockedBy, comments, attachments) this deployment's tracker carries natively, emulates, holds only in fleet, or does not support, and which verbs are served. | `GET /capabilities` |
| `search_issues` | Search issues by text in title and body, or by either name of an item. | `GET /issues` |
| `file_issue` | File a new tracker issue: a bug (something is broken), a task (small scoped work), an idea, an audit finding or a cleanup. | `POST /issues` |
| `triage` | Record this issue's triage verdict (e.g. KEY-123), in Fleet's own words. | `POST /issues/{key}/triage` |
| `relate` | Add or withdraw a relation (e.g. KEY-123) between two issues Fleet holds, in Fleet's own words. | `POST /issues/{key}/relations` |
| `comment` | Add a comment to a tracker issue, attributed to this run or to the person using this session. | `POST /issues/{key}/comments` |
| `comments` | Read an issue's comments typed: filter by `kind` and `since` (ISO instant). | `GET /issues/{key}/comments` |
| `latest_comment` | The newest comment of one kind on an issue (heartbeat, verdict, stop, rework, ...), or null. | `GET /issues/{key}/comments/latest` |
| `move_issue` | Move a tracker issue to another fleet position. | `POST /issues/{key}/move` |
| `hold_planning` | Say this session is doing a PRD's fill, design or plan itself, so the fleet does not start a second run of it (a person's key only). | `POST /planning/hold`, `POST /planning/unhold` |
| `decide` | Answer an issue parked at Blocked · decision. | `POST /decide` |
| `close` | Close (cancel) or withdraw a person's own filing, with the reason a person will read. | `POST /close` |
| `get_draft` | Read where one of your drafts stands: drafted (awaiting the person), confirmed (released), expired, superseded (a newer draft or the issue moved) or refused. | `GET /drafts/{draft_id}` |
| `link` | Link a pull request, a page, or evidence to an issue (instead of editing its description). | `POST /issues/{key}/comments` |
| `board` | List open issues: filter by position slugs (comma-separated), kind, program (PG-NN), and blocked (any, or stale: the blocker is closed or parked). | `GET /board` |
| `work_fields` | Read the priority, labels and blocker edges fleet holds for an issue, with recent edits and any drift from the tracker. | `GET /work/{key}` |
| `set_field` | Set an issue's priority (value 1 urgent..4 low) or one label group: type, component or repo (value an existing label's name; empty clears), or the feature it is filed under (feature: a slug from the Features page; empty files it under none; an unknown slug is refused with the valid ones). | `POST /work/{key}/priority`, `POST /work/{key}/labels`, `POST /work/{key}/feature` |
| `set_free_label` | Add or remove FREE labels on one item — an issue, a filing, a slice, a program or a PRD. | `POST /work/{key}/free-labels` |
| `set_release_label` | Set one declared release-group label on one open issue, from a CI key. | `POST /work/{key}/release-label` |
| `reset_runs` | Draw the run-reset line under an issue that spent a ceiling (runs, attempts, silence or never-launched) and is parked after it (or refused as budget-spent), so it can be claimed again; moves a parked issue back to its queue. | `POST /resets` |
| `clear_drain` | Lift a worker seat's consecutive-failure auto-drain: draw the clear line (`POST /api/drain-clears`) so the seat is offered work again. | `POST /drain-clears` |
| `refuse_qa_run` | Record that this QA run refused to run (its environment guard said no at start: paused, leftovers, production write limit, or a manual start), with the guard's sentence, on the Quality desk's ledger row for this run's own issue. | `POST /qa-refusals` |
| `begin_qa_run` | Mark that this QA run has begun driving its environment, on the Quality desk's ledger row for this run's own issue. | `POST /qa-beginnings` |
| `attest_qa_review` | Attest one review record this QA verifier run just wrote, by the digest qa_review.py printed for it. | `POST /qa-attestations` |
| `record_verdict` | Record a verify verdict for one PR head commit, with its ledger. | `POST /verdicts` |
| `get_verdict` | Read the newest verdict for a pull request (omit head_sha), or the one at a specific head commit, with its ledger and the neuter check its verify run recorded. | `GET /verdicts` |
| `upload_link` | Ask Fleet for a short-lived upload link and the one command that sends a folder or files to it. | `POST /uploads` |
| `publish_page` | Publish an uploaded bundle under a stable page name, so one address always shows its newest version. | `PUT /pages/{name}` |
| `list_pages` | List the published pages (name, bundleId, entry, publishedBy, publishedAt, openPath), newest first. | `GET /pages`, `GET /pages/{name}` |
| `read_bundle_file` | Read one text file back out of an uploaded bundle, e.g. the brief, CSV results or helper scripts an earlier session uploaded before its box was recycled. | `GET /bundles/{bundle_id}/file`, `GET /pages/{name}/file` |
| `list_docs` | List Fleet's own docs: how to use Fleet, and how a repository's knowledge base (feature areas, slices, PRDs, programs) is built. | `GET /docs` |
| `read_doc` | Read one of Fleet's docs as plain markdown — the same page a person reads in the Docs view, with this repository's live facts (slices, areas, PRDs, its planning mode, its commands) filled in at the commit Fleet serves. | `GET /docs/page` |
