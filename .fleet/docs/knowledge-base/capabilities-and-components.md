# Capabilities and components

Two maps of the same product. Capabilities describe it the way a person uses it: "approve an order", "see what has been checked". Components describe it the way it is built: "the API service", "the worker daemon". The knowledge base keeps both, and links them.

## Capabilities: what someone can do

A capability is one thing the product lets a person do, small enough to check at any time and still true tomorrow. "Search works" is too big; "the Save button is enabled" is too small. "A reviewer can approve an order a second time" is about right.

Capabilities are grouped. A [feature](knowledge-base/feature-areas) has a few uses, the main things a person does with it, such as "Sign in with SAML" under sign-in, and each capability sits under exactly one use. Each is one row in the feature's map, under its use:

| Column | What it says |
|---|---|
| ID | `CAP-` and a number. Permanent, never reused. |
| Capability | A short name, then one sentence a person can check. |
| Ships in | The PRD (on the feature's page, the plan) that delivers it. Whether it is built is read from that PRD. |
| Tested by | The test or journey that proves it works. |
| Needs | Other capabilities it builds on. |

A capability with nothing in **Tested by** and no journey criterion naming it is a gap the Quality desk lists, because nothing could catch it breaking.

A capability that fits no use waits under `### Misfits (to move)` until a person decides where it goes; see [When nothing fits](knowledge-base/feature-areas).

Capabilities get written when you plan a use from the feature's page (one row for each piece of work in the plan), when a PRD that ships one is drafted, and when an existing code base is first described. On the feature's page each one shows its state, from **Not built** to **Built**; what each word means is in [Features, uses and capabilities](knowledge-base/feature-areas).

## Components: what you build

A component is a part of the system you would draw once on an architecture diagram, defined by the code it owns: a directory, a service, a set of tables. It never finishes and has no status.

The components are listed in the component registry, `knowledge/specs/architecture/components.md`:

| Column | What it says |
|---|---|
| ID | A short name, such as `fleet-service`. |
| Layer | The tier it sits in. |
| Owns | The code paths that belong to it. |
| Depends on | The components it uses. |
| Description | One line saying what it is. |

A bug is filed against a component, because a bug is about code. A slice can name the components it touches.

`component:create` — Register one durable subsystem as a row in the component registry — a thing that is built, never shipped, and therefore never carries ship-state.

## Outcomes: what owns no code

Some lasting properties of a product come out of several components working together and belong to none of them: "every action leaves an audit record", "a page loads in under a second". That is an outcome. If you can point at the code that delivers it, it is a component instead.

## Why the two maps differ

Features, their uses and their capabilities are how a customer sees the product. Components are how the code is split. One feature usually draws on several components, and one component serves several features. Each feature map lists the components it draws on in its front matter, which is how a slice or a bug filed against a component finds its feature.

> **Tip:** If your repository's capability ids were ever renumbered, it keeps `knowledge/capability-aliases.md`: the frozen list of old ids and the new ones they became, so a citation in a shipped PRD or an old issue still leads somewhere.

## Where you see them

The Knowledge page lists every capability and component, each linked to its feature, its PRD and its journeys. A feature's own page, under **Features**, shows its capabilities inside each use. The Architecture page draws the component registry.

[Open Architecture](#arch)

Next: Features, uses and capabilities (knowledge-base/feature-areas) · Journeys (knowledge-base/journeys) · Promises and requirements (knowledge-base/promises)

---
- **capability**: One concrete thing the product lets a person do, small enough to check at any time and still true tomorrow; it sits under one use of a feature, is shipped by a PRD, and never finishes.
- **component**: A part of the product you can point at in the code, such as a directory, a service or a set of tables; it is built and never finishes.
- **outcome**: A lasting property that comes from several components working together and owns no code of its own, such as "an order page loads in under a second".
