# Do a planning step yourself

When you are done you will have filled, designed or planned a PRD yourself, in a session you drive, while the fleet left that step alone instead of starting a second copy of it.

## Why the fleet has to be told

Under a driven program the fleet asks for every planning step by itself. If you are designing a PRD on your own branch, nothing the fleet reads shows that until your branch reaches GitHub, and by then it may have started its own design of the same PRD. So your session tells it first. That is a planning hold.

> **Why:** 77 minutes passed between the fleet starting its own design of a PRD and the operator's local branch for the same design reaching GitHub. Only the session saying so as it starts arrives in time.

## Hold a step and do it

1. [you] **Connect your session to Fleet.** Your terminal needs Fleet's session tools, through your own key. See [Connect your terminal](guides/your-tools/connect-your-terminal).
2. [you] **Run the command for the step.** For a design or a plan, run it with the PRD's number. The command calls `hold_planning` as its first step, naming the PRD, the step and your branch.

   `prd:design` — Technical + UX design grounded in a PRD; produces design.md (+ optional ux-design.md).
3. [fleet] **The fleet leaves that step alone.** It does not ask for that step of that PRD while the hold is live. The program's **Delivery** box lists the step under **Not started yet**, with "held: being worked on in *your branch* by *you*" and a **Release hold** button beside it.
4. [you] **Finish and merge.** Your pull request moves the PRD's status on.
5. [nobody] **The hold ends by itself.** It lapses the moment the PRD's status moves.

A hold names one of three steps, each taken from the status it starts from: **fill** from a stub, **design** from drafted (or from designed, to design again), and **plan** from designed. Only a person's key can take a hold; a fleet run cannot.

> **Careful:** If you give up the step, release the hold. From that session, call `hold_planning` again with
> `release=true`; or, if the session is already closed, open the program's page and press **Release
> hold** beside the step under **Not started yet**. Otherwise the fleet stays off that step until the
> PRD's status changes. Releasing from the page is recorded with your name.

## Shaping steps run in a session instead

For a program, a slice or a PRD stub, the shaping box on its page offers **Run it yourself in an agent session**. It opens a session on a machine that asks you the same things in a conversation instead of on question cards. Where a session cannot open, the box shows the command to run in a terminal of your own.

Next: Fill and design a PRD (guides/plan/fill-and-design-a-prd) · Shape a program and hand it to the fleet (guides/plan/shape-a-program) · Open a session (guides/sessions/open-a-session)

---
- **planning hold**: A note your own session gives the fleet that it is doing a planning step itself, so the fleet does not start the same step.
