---
type: readme
---

# Feature maps

One file per **feature area** — the durable ledger of what Acme App promises a customer, and
which PRD ships it. A feature area covers the whole product and outlives any one program, so
a program decomposition appends **gap rows** (`Ships in: —`) to the map of the area it
belongs to, and a PRD flips that `—` to its own number in the same change that ships the
capability.

| Area | File | Covers |
|---|---|---|
| tasks | [tasks.md](tasks.md) | Putting tasks in, seeing them, finishing them, and taking them out again. |
