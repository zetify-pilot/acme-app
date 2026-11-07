---
title: "Plan what gets built"
kind: job
icon: plan
group: use
for: [owner, developer]
summary: "Features, slices and PRDs: add a feature, decide where work belongs, what is true when it is done, and what one agent builds."
minutes: 4
---

:::lede
Planning in Fleet answers three questions. Where does this belong? What will be true when it is done? What does one agent build? This path shows how each answer is written, and how to hand the rest of the planning to the fleet.
:::

## The big picture

:::ideas
- **Feature.** A part of the product a customer would name, such as "Sign-in", with a short brief and a few uses: the main things people do with it, such as "Sign in with SAML". Every slice is filed under one. It never finishes; how far it has got is read from its work.
- **Slice.** One sentence that says when a deliverable is done, in words someone can check. It finishes by itself once its PRDs are done and the PRD named as its proof has shipped.
- **PRD.** One piece of work one agent can build in one session, with acceptance criteria it must pass. Its status is the only one anyone writes.
- **Program.** In a repository that plans by programs, a larger result that two or more slices add up to and none delivers alone.
:::

The pieces nest. A :term[feature] holds uses, and each use holds capabilities. **Plan this** on a use turns it into slices, which the feature's page calls pieces of work, each with its PRDs, which it calls plans. A :term[feature area], the planning name for a feature, holds slices. A :term[slice] is made true by its PRDs. Nobody marks a slice or a program done: Fleet works that out from the PRDs every time it reads your knowledge base, so the state cannot drift from the work. Whether your repository also uses programs is its planning mode, one setting per repository. In both modes every slice names its area.

A :term[PRD] goes through three planning steps before it is built. **Fill** turns a stub into a drafted PRD. **Design** turns it into a designed one, and you approve its mockup. **Plan** asks you nothing. Each step runs on a machine, asks its questions through cards in your Cockpit, and lands as one pull request. After that, a PRD is built and verified like any other issue. You can let the fleet drive all of this, from a program or with **Start this slice**, or do a step yourself in your own session.

## Read these in order

::path{links="concepts/how-fleet-plans,guides/plan/add-and-plan-a-feature,guides/plan/work-by-area,guides/plan/refine-a-slice,guides/plan/fill-and-design-a-prd"}

## When you need it

::pages{links="guides/plan/read-the-board,guides/plan/shape-a-program,guides/plan/do-a-step-yourself,guides/plan/my-programs"}
