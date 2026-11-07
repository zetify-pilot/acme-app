# Plan what gets built

Planning in Fleet answers three questions. Where does this belong? What will be true when it is done? What does one agent build? This path shows how each answer is written, and how to hand the rest of the planning to the fleet.

## The big picture

- **Feature.** A part of the product a customer would name, such as "Sign-in", with a short brief and a few uses: the main things people do with it, such as "Sign in with SAML". Every slice is filed under one. It never finishes; how far it has got is read from its work.
- **Slice.** One sentence that says when a deliverable is done, in words someone can check. It finishes by itself once its PRDs are done and the PRD named as its proof has shipped.
- **PRD.** One piece of work one agent can build in one session, with acceptance criteria it must pass. Its status is the only one anyone writes.
- **Program.** In a repository that plans by programs, a larger result that two or more slices add up to and none delivers alone.

The pieces nest. A feature holds uses, and each use holds capabilities. **Plan this** on a use turns it into slices, which the feature's page calls pieces of work, each with its PRDs, which it calls plans. A feature area, the planning name for a feature, holds slices. A slice is made true by its PRDs. Nobody marks a slice or a program done: Fleet works that out from the PRDs every time it reads your knowledge base, so the state cannot drift from the work. Whether your repository also uses programs is its planning mode, one setting per repository. In both modes every slice names its area.

A PRD goes through three planning steps before it is built. **Fill** turns a stub into a drafted PRD. **Design** turns it into a designed one, and you approve its mockup. **Plan** asks you nothing. Each step runs on a machine, asks its questions through cards in your Cockpit, and lands as one pull request. After that, a PRD is built and verified like any other issue. You can let the fleet drive all of this, from a program or with **Start this slice**, or do a step yourself in your own session.

## Read these in order

1. **How Fleet plans: one piece of work, start to finish** (concepts/how-fleet-plans): Follow one real piece of work from a feature request to merged code, and learn the few words Fleet uses on the way.
2. **Add a feature and plan its work** (guides/plan/add-and-plan-a-feature): Add a feature and check the brief Fleet drafts, write the brief of a feature that has none, plan one use or the whole feature, and add more later.
3. **Use the Features page** (guides/plan/work-by-area): Read what each feature is and how far it has got, find what is open and what waits on you, give every slice a feature, and start a slice no program drives.
4. **Refine a slice** (guides/plan/refine-a-slice): Sharpen a slice cut from a brief into a clear Done when, its promises and the bar it is held to, by answering one or two rounds of questions.
5. **Fill and design a PRD** (guides/plan/fill-and-design-a-prd): Turn a PRD stub into a drafted PRD, then a designed one, by answering the fleet's questions and approving its mockup.

## When you need it

- **Read the Programs list, and set its order** (guides/plan/read-the-board): See where every program stands, narrow the list to what needs you, and set the priority order the fleet works in.
- **Shape a program and hand it to the fleet** (guides/plan/shape-a-program): Turn a bare program into slices and a proof through a few rounds of questions, then start it so the fleet plans and builds the rest.
- **Do a planning step yourself** (guides/plan/do-a-step-yourself): Fill, design or plan a PRD in your own session, and tell the fleet so it does not start the same step.
- **Narrow Fleet to your programs** (guides/plan/my-programs): Name who is responsible for each program, then see only your own programs on the Programs list.

---
- **feature**: A part of the product a customer would name, such as sign-in or parts management, described by a short brief and a few uses; it never finishes.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.
- **slice**: One deliverable with a one-sentence "Done when", which finishes by itself once its PRDs are done and its proof has shipped.
- **PRD**: A piece of work one agent builds in one session, with acceptance criteria, and the only thing whose status anyone writes.
