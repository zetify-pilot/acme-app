---
type: slice-register
---

# Slices

<!-- APPEND ONLY. Next id: SL-004 -->

| ID | Name | Kind | Program | Done when | Verified by | Depends on | Components | Disposition |
|---|---|---|---|---|---|---|---|---|
| SL-001 | Customers can export their tasks as CSV. | feature | PG-01 | Customers can export their tasks as CSV. — observed on the running product, not a definition. | — | — | — | superseded by SL-002, SL-003 |
| SL-002 | A task list exports as a CSV file | feature | PG-01 | A person asks for the export and gets one row per task, with titles containing commas and quotes intact, and an empty list producing a file with only a header. | — | — | — | adopted |
| SL-003 | One customer's tasks are separable from another's | capability | PG-01 | Two people's exports produce two files that each hold only that person's tasks. | — | SL-002 | — | adopted |
