# feature-areas

The feature areas an issue can be filed against. The set is closed: it is exactly the feature maps
under knowledge/features/, and nothing else.

## Enumerate it — never recall it

```bash
grep -h '^area:' knowledge/features/*.md knowledge/features/*.md.tmpl 2>/dev/null | sed 's/^area: *//' | sort -u
```

## Answers

- **areas** — the names the command above prints. Never pick an area by analogy to an older issue.
- **no-maps-yet** — `fleet init` writes no feature map, so on a new repository the command prints
  nothing. Until the first map exists, file and release work with no feature area. Fleet refuses an
  area that has no map.
- **first-area** — the first slice in `knowledge/slices.md` names the area `product`. It stays a name
  until its feature map, knowledge/features/product.md, is written. Until then the check only notes it.
- **tracker** — Fleet keeps the area on each issue, from the `triage` tool's `feature_area`. On a
  tracker with projects, Fleet also sets the project of the same name.
- **no-fit** — when maps exist but none covers the ground, pick the closest and say so in the issue. Name
  the gap in your report: work that no feature map claims is a finding.
