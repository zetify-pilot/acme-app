# planning-model

How work is planned in this repository, in the layout `fleet init` wrote. What each kind of work
is ships with the commands, in `.fleet/process/planning-ladder.md`. Change a line here when this
repository plans differently.

## Answers

- **mode** — `[fleet.planning] mode` in `.fleet/fleet.toml` says where a new slice goes. With
  `areas`, every slice names a feature area and no new program is written. With `programs`, a
  slice names an area and may also name a program.
- **registers** — slices are rows in `knowledge/slices.md`, under the header
  `| ID | Name | Kind | Program | Done when | Verified by | Depends on | Components | Disposition |`.
  Programs are rows in `knowledge/programs.md`, under
  `| ID | Name | Kind | Verified by | Requires | Disposition |`. A slice's area rides in its
  Program cell as `area:<slug>`, after the program when it has one (`PG-01, area:product`).
- **ids** — slices `SL-NNN`, programs `PG-NN`, PRDs four digits `NNNN`, requirements `REQ-NNN`.
  Each register's `Next id:` line names the next free id. An id is never reused.
- **artifacts** — a PRD is knowledge/prds/NNNN-<slug>/prd.md. Its design and plans sit beside it
  in the same folder.
- **prd-states** — `stub` → `prd-drafted` → `designed` → `planned` → `implementing` → `verified` →
  `shipped`, or `cancelled` with a reason. The commands move a PRD's `status:`; nobody edits it by
  hand.
- **shipped** — `shipped` rides the PRD's own merge, as the last commit on its branch. It is never a
  separate commit after the merge.
- **durable-vs-versioned** — a slice, a program and a PRD are versioned: each can be finished. A
  feature area, a component and a requirement are durable: each is never finished.
- **computed** — only a PRD's `status:` is written. A slice's or a program's state is computed from
  its PRDs and its `Verified by` proof. Neither register has a status column.
