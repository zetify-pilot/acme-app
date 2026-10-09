# Slots — where this repository's answers live

The shipped questionnaire (`fleet slots --emit questions`) asks the questions; this file
holds only `fill` — the repo-relative path(s) that answer each. Every slot the shipped
core commands require is answered below, so `fleet slots --repo .` finds every core
command runnable. Where *this* repository keeps a document is the only part of a slot a
repository is entitled to have an opinion about.

```json
{
  "version": 2,
  "fill": {
    "architecture": [
      "knowledge/slots/architecture.md"
    ],
    "codegen": [
      "knowledge/slots/codegen.md"
    ],
    "commitments": [
      "knowledge/requirements/product.md"
    ],
    "dev-environment": [
      "knowledge/slots/dev-environment.md"
    ],
    "entity-model": [
      "knowledge/slots/entity-model.md"
    ],
    "feature-areas": [
      "knowledge/slots/feature-areas.md"
    ],
    "file-conventions": [
      "knowledge/slots/file-conventions.md"
    ],
    "gate": [
      "knowledge/slots/gate.md"
    ],
    "git-workflow": [
      "knowledge/slots/git-workflow.md"
    ],
    "journeys": [
      "knowledge/slots/journeys.md"
    ],
    "languages": [
      "knowledge/slots/languages.md"
    ],
    "planning-model": [
      "knowledge/slots/planning-model.md"
    ],
    "product-vision": [
      "knowledge/strategy/product-vision.md"
    ],
    "programs": [
      "knowledge/programs.md"
    ],
    "slices": [
      "knowledge/slices.md"
    ],
    "tracker-identity": [
      "knowledge/slots/tracker-identity.md"
    ]
  }
}
```
