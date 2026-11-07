# Features, uses and capabilities

A feature is a part of the product the way a customer describes it: "Sign-in", "Approvals", "Parts management". It has a short brief that says what it is, a few uses that say what people do with it, and under each use the capabilities that make it work. It never finishes, so it never has a status of its own: how far it has got is read from the work under it.

## Three layers, one example

Take sign-in. A customer would name it, so it is a feature. Here is how it reads in Fleet:

| Layer | What it is | In the sign-in example |
|---|---|---|
| **Feature** | A part of the product a customer would name, with a brief. | Sign-in |
| **Use** | One of the main things a person does with it: a name, one plain sentence and a state. | "Sign in with username and password", "Sign in with your company's provider" (the single sign-on the company already runs, through a standard called OIDC), "Sign in with SAML" (an older single sign-on standard many large companies use), "Manage your sessions" |
| **Capability** | One concrete thing inside a use, one row each, shipped by one plan. | Under "Sign in with your company's provider": "Connect a provider", "Send people to the provider and back", "Give people roles from their provider groups" |

A sub-feature is a use. "Sign in with SAML" is not a feature of its own: it is one of the things people do with sign-in, so it is a use of it.

A use that grows too big becomes its own feature. When it needs a brief of its own to be understood, or a person of its own to own it, it has outgrown being one line on another feature's page: add it as a feature, and the old use either goes or keeps the part that still belongs there.

## The brief: understand it in thirty seconds

Every feature's page opens with its feature brief:

- **A summary.** One sentence: what it is, and for whom.
- **The problem.** Two or three sentences: what goes wrong without it, and why that matters.
- **For example.** Three or four sentences about a named person doing a real job with it.
- **What it is not.** One to three lines, each naming the neighbouring feature that does that instead.

The brief never says how far the feature has got. Words like "planned" or "partly built" go stale the day the next piece of work lands, so the page works the progress out from the work every time it is read.

## Uses: what people do with it

A feature has a few uses. Each one is named for something a person does, with a verb first ("Book a repair", "Decide what it may see"), and has one or two plain sentences under it. There is no limit on how many uses a feature has: a new request is a use when no existing one says it, and a feature of its own when it is a different thing altogether.

Opening a use on the feature's page shows what is inside it:

- **What it does**: its capabilities, each with its state.
- **Who it serves**: the journeys that use it, and whether each is ready.
- **What it promises**: the rules it must keep, and which are met.
- **Being worked on**: the plans and pieces of work open on it.

## Capabilities: one row per concrete thing

A capability is one thing a person can do, small enough to check at any time and still true tomorrow. Each sits under exactly one use, and each is shipped by one plan (a PRD). When Fleet plans a use, it writes one capability row for each piece of work in the plan, so the use reads as planned the moment the plan lands. See [Capabilities and components](knowledge-base/capabilities-and-components).

## Which one is it: a feature, a use or a capability?

When something new comes up, ask these in order and stop at the first yes.

| Ask | If yes, it is | Example, on a repair-shop product |
|---|---|---|
| Is it one concrete thing a person can do, small enough to check, and does a use of a feature already cover its ground? | a **capability**, under that use | "Mark a part as used on a repair", under the use "Reserve parts for a repair" |
| Is it a main thing people do with a feature that no use says yet, and no use says it already? | a **use** of that feature | "Reserve parts for a repair", on Parts management |
| Would a customer name it on its own, does it need its own brief to be understood, or is it too different from the feature's other uses to be one of them? | a **feature** | "Supplier ordering", once it outgrows being a use of Parts management |
| Is it broken, or a small change to something that exists? | none of these: it is a bug or a task | "The part count is wrong after a return" |

Two habits keep the cut honest. Read the feature's brief and every use before you add anything: if a use already says it, the request extends that use and nothing is added. And never stretch a use to hold something it does not say, or invent one to hold a stray row; that is how a feature stops being readable.

## Naming a use

A use is named for something a person does, in a few words, with a verb first: "Book a repair", "Decide what it may see", "Sign in with SAML". Under the name goes one paragraph of one or two plain sentences saying what the person does with it and why. Never write how far it has got ("shipped", "planned", "partly built", "still open"), never a bare number such as a plan or issue number, and never code. A rule the product promises is cited by its id from the rules register, never restated. The same wording standard covers capabilities: a short name, then one sentence a person could check.

## When nothing fits

A new capability goes under the use it serves. If it fits no use, do not force it:

1. If it belongs to another feature, put it in that feature's map instead.
2. If it is a real thing a person does and no use of the feature says it already, add a use for it, with its paragraph.
3. Otherwise the feature is cut wrongly, or the row belongs somewhere not decided yet. Put the row under a last section headed `### Misfits (to move)` and say so: a person decides where it goes, an agent files a task naming the map, the row and why no use fits. The check lists the waiting rows as a note, never an error, so this is a safe place to wait and not a place to leave rows.

Rows that were retired or withdrawn sit under `### Retired`, which is a permanent home. They count in no use and no progress figure, and their ids stay.

## Filling the maps of an existing repository

A map written before uses existed has a table of capabilities and no brief. A change that only updates cells in it, such as recording the plan that shipped a row, can land as it is. A change that adds, removes or moves a row, or touches its headings, must bring the brief and the cut with it, in the same change.

1. [you] **Read the rows first.** Group them by what a person does, never by the component or the plan that built them. Three to six groups; a map with fewer than three rows takes fewer uses.
2. [you] **Write the brief.** A summary, the problem, an example drawn from a journey the map links, and what the feature is not.
3. [you] **Cut the rows into uses.** Add a `###` heading and a paragraph for each use, and move each row whole under the one it serves. Never edit a row's cells while you move it, and never renumber its id.
4. [you] **Park what does not fit.** Rows that fit no use go under `### Misfits (to move)`, and the pull request says where each belongs.
5. [you] **Run the check.** `fleet check --only feature-briefs` reports a missing brief, a count of uses outside three to six, a use with no paragraph, a row under no use, and any ship-state word or bare id in the prose.

You do not have to do this by hand. On the **Features** page, a feature with no brief, or no uses, offers **Write the brief**: Fleet drafts the brief and sorts the rows into uses, you check and change it, and it is saved as one reviewed change. Rows are only regrouped, never reworded, renumbered or dropped. See [Add a feature and plan its work](guides/plan/add-and-plan-a-feature).

The **Features** page lists every feature, even one with no brief, no capabilities and no work yet. Finished features sit at the bottom under a quiet **Finished** line, and retired ones come last.

A repository you are describing for the first time gets this for free: [`knowledge:bootstrap`](guides/knowledge/describe-existing-code) proposes the features from the capabilities you confirmed, drafts each brief and the uses with their rows, and asks you once.

## What each state means

Nobody writes a state by hand. Fleet reads each one from the plans under it.

**A capability or a use** says one of these:

| State | What it means |
|---|---|
| **Not built** | Nothing is planned for it yet. On a use, this is when **Plan this** is offered (a use you have just added is already being planned, and says so). |
| **Drafted**, **Planned**, **Being built**, **Partly built** | Fleet has some of its work written down. On a use, **Plan what's missing** is offered while one of its capabilities is still **Not built**. |
| **Drafted** | Its plans are written down but not designed yet. |
| **Planned** | Its plans are designed and ready to build. |
| **Being built** | An agent is building or checking one of its plans. |
| **Partly built** | Some of it is built and some is still to come. |
| **Built** | Every plan under it has shipped. |
| **Retired** | It was built and has since been removed. It is out of every count. |

While Fleet is drafting a plan for a use, the use says **Fleet is planning this…**; when the plan waits for your yes, it says **A plan waits on you**.

**The feature as a whole** says one of these, beside a bar of how much is built:

| State | What it means |
|---|---|
| **Not started** | Nothing on it is built yet. |
| **Being built** | Something on it is planned or being built. |
| **Complete, with gaps** | What is built works, and some capabilities are still not built. |
| **Complete** | Every capability is built. |
| **Retired** | Every capability is retired. |

Open bugs and tasks never change these words. The page counts them beside the state instead.

## Where it lives: the feature map

Each feature is one feature map: a file under `knowledge/features/` named for the feature, such as `knowledge/features/fleet-quality-desk.md`. It holds the brief in its front matter, a `###` heading for each use (with its paragraph) under `## Capabilities`, the capability rows under each heading, and the code paths it describes. The use a row belongs to is the heading it sits under; it is written nowhere else. In planning, a feature is called a feature area, and the map's `area:` line is its short name.

> An example from Fleet's own planning: **Fleet Quality Desk** (fleet-quality-desk)
> How Fleet records what its checks found and shows what has been checked, how deeply and how recently. The job: open one page, see every area against every kind of check, ask the team to look at one area, and see the result appear.

## What a feature is used for

- **Every slice and every PRD names its feature.** In both planning modes. See [Planning by areas or by programs](knowledge-base/planning-modes).
- **Every task and bug is filed under one.** In your tracker, each feature is a project, so new work always has somewhere to go. Work made for a feature is filed under it the moment it is created: the task or bug a request on that feature becomes, a bug filed from that request, and anything an agent files for that feature. Nobody links it by hand afterwards. Work that names no feature is placed by the check, and you can move any of it on the Cockpit.
- **Every code path is claimed by one.** A new file that no map claims fails the check, so a map cannot quietly stop describing the code. See [Keep the maps current](guides/knowledge/keep-maps-current).

A feature is not a component. A component is how the code is split; a feature is how a customer sees the product, and one feature can draw on several components.

## Adding and growing a feature

You add a feature from the **Features** page with **New feature**: you describe it, Fleet drafts the brief and the uses, and you check them before it is added. You add a use later with **+ Add something this feature should do**, or by answering **Where does this go?** on a **Feature request**; Fleet plans a use you add as soon as it lands. You turn any other use into work with **Plan this**, or with **Plan what's missing** when part of the use is planned and part is not, or every use at once with **Plan the whole feature**. Anything Fleet's planning needs you to answer is listed on the feature's page under **Waiting on you**. The steps are in [Add a feature and plan its work](guides/plan/add-and-plan-a-feature).

For a code base that has no features yet, the bootstrap drafts them from the capabilities a person has confirmed:

`knowledge:bootstrap` — Describe an existing code base into the knowledge corpus one resumable step at a time — survey, components, per-component capabilities and rules, feature areas, journeys — drafting from the code and confirming every promise with a person in batches, so new work builds on it and the QA Desk checks it out of the box.

Next: Add a feature and plan its work (guides/plan/add-and-plan-a-feature) · Use the Features page (guides/plan/work-by-area) · Capabilities and components (knowledge-base/capabilities-and-components)

---
- **feature**: A part of the product a customer would name, such as sign-in or parts management, described by a short brief and a few uses; it never finishes.
- **feature brief**: The few lines at the top of a feature's page: one summary sentence, the problem it solves, an example of a real person using it, and what it is not.
- **use**: One of the main things a person can do with a feature, such as "Sign in with SAML", with one plain sentence and a state read from the work under it.
- **capability**: One concrete thing the product lets a person do, small enough to check at any time and still true tomorrow; it sits under one use of a feature, is shipped by a PRD, and never finishes.
- **PRD**: A piece of work one agent builds in one session, with acceptance criteria, and the only thing whose status anyone writes.
- **feature map**: The file under `knowledge/features/` for one feature, holding its brief, its uses and the capabilities under each use.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.
- **component**: A part of the product you can point at in the code, such as a directory, a service or a set of tables; it is built and never finishes.
