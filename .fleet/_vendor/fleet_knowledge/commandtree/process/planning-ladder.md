### The planning ladder — which kind of thing is this?

**This ladder is the same in every repository.** It says what each kind of work is and in which
order to test for it. Where each kind *lives* in this repository — the file, the register, the
tracker project — and the local examples are the repository's own answer, `slot:entity-model`.
When the two seem to disagree about what a thing *is*, this ladder wins; when they disagree about
*where* it goes, the slot wins.

**Why it exists.** A router that judged size by feel turned a bug ("a session ignores new
messages while it waits on a long pull-request watch"), a one-page screen change and a request
for documentation into three new programs in one day. Each of them failed a test below that
nobody ran. Run the tests; do not judge by how big the request sounds.

#### First, two questions about the situation

These are about the request, not about an entity. Ask them before anything else.

| Ask | If yes |
|---|---|
| **Is something broken?** Something that used to work, or that the product already says it does, does not. A wrong or missing documentation page for something that ships counts. | **bug** — however large the fix turns out to be |
| **Is it early or exploratory** — "for later", not ready to build, nobody can yet say what done looks like? | **idea** — parked, not sized |

A bug stays a bug when the fix is big. A big fix is a reason for the bug to name a slice or a PRD
later; it is never a reason to make the bug a program.

#### Then the ladder — top down, the first match wins

The order is what removes the doubt: things that never finish are caught before anything is sized
as work, and the small work rungs are tested before the large ones.

| # | Ask | If yes |
|---|---|---|
| **1** | Can you point at the code it owns — a directory, a service, a set of tables? | **component** (built, never finished) |
| **2** | Is it a lasting property of the product? *One sentence a person can check* → | **capability** |
| | *…it emerges from several components and owns no code* → | **outcome** |
| **3** | Would a customer name it when describing what the product does, and does it group several capabilities? | **feature area** |
| **4** | Is it only a way to *filter* things that each already stand alone (security, onboarding, a release)? | **theme** — a label, never a container |
| **5** | Is it small, scoped work that needs no design decision and gives nobody a new thing to see or use? | **task** |
| **6** | Can one agent build it end to end in one working session, with acceptance criteria and a change a person can see or use? | **PRD** |
| **7** | Is it one deliverable — one feature, one capability and what it needs, or one set of gaps — with a "Done when" that none of its PRDs proves alone? | **slice** |
| **8** | Do **all** the program tests below pass? **Never in a repository that plans by area** — see below. | **program** |

**If nothing matches, you have not finished thinking.** (In a repository that plans by area, rung 8
never matches: work bigger than one slice is several slices.) The two usual landings: something that
never finishes but owns no code is an **outcome** (rung 2); something that finishes but holds one
deliverable is a **slice** (rung 7), not a program.

Components, capabilities, outcomes, feature areas and themes are **durable**: they never finish
and carry no status. Tasks, PRDs, slices and programs are work that finishes.

**A use is not a rung — and it is how a customer-facing feature is cut.** The customer page is *Features, uses and capabilities* (`knowledge-base/feature-areas`). A request is a **capability** when a use already covers its ground, a **use** when it is a main thing people do that no use says and it is not already one of them, a **feature** only when it passes the sub-feature test below; a row that fits none waits under `### Misfits (to move)` (*Writing a feature brief*, moment 2). A feature area's capabilities are grouped under its three to six **uses** —
the main things a person does with it (*Sign in with SAML* under sign-in) — so a request a customer
calls a "sub-feature" lands at rung 3 as an existing area plus a use, never as an area of its own.
It becomes its own feature area only when it needs its own brief or owner (*Writing a feature
brief*, feature-doc reconcile process document).

#### The size tests, smallest first

Each rung is the smallest one whose test the work passes. Test them in this order and stop at the
first pass.

- **Task** — scoped work that needs no design: a dependency bump, a configuration change, a
  refactor with no visible change, a wording fix. If two people
  could disagree about how it should look or behave, it needs a design, and it is not a task.
- **PRD** — one agent, one working session, one surface a person touches (a page, a control, an
  API behaviour, a command). It carries acceptance criteria that can each be shown to pass. One
  new screen is a PRD, however important it is.
- **Slice** — one deliverable that finishes, with a "Done when" a person can observe on the
  running product, which none of its PRDs carries alone. A slice usually holds two or more PRDs;
  a one-PRD slice is allowed but worth a second look, because it is often a PRD that has not yet
  found what ships beside it.
- **Program** — only when the work holds **at least two slices** under one result that neither
  slice delivers alone. **One deliverable is a slice, not a program**, however large it is.
  **In a repository that plans by area there is no program rung at all** (next section).

#### In a repository that plans by area, "program" is not a rung

Run `python3 knowledge/scripts/planning_mode.py`. It prints `programs` or `areas` (the setting is
`[fleet.planning] mode` in `.fleet/fleet.toml`; no setting means `programs`).

**When it prints `areas`, the ladder stops at rung 7. No new program is ever proposed or created**<!-- home -->
(owner, 2026-10-28: *"in area mode we dont accept programs anymore! we dont want more to migrate
later!"*, `FLT-1285`)<!-- /home -->. Programs that already exist keep running until their slices finish; nothing new joins
them.

Work that is bigger than one slice does not become a program. It becomes **several slices**:

- **Each deliverable is its own slice**, with its own "Done when", under the **feature area** that
  owns it. Two deliverables in one area are two slices in that area; deliverables that belong to
  different areas are slices in different areas.
- **The order between them is written as dependencies, not as a container.** A slice that cannot
  start before another finishes says so in its `Depends on`; a PRD that builds on another PRD says
  so in its own `depends_on`. That is all the grouping the work needs.
- **The program tests still help you think** — a literal title, a person who notices, a day it
  becomes true — but what they describe is the *set* of slices. Nothing is created for the set itself.
- **When you route such a request, propose the first slice** (the one the others depend on), and
  describe the other slices in plain words in `alsoWeighed`, so the person who accepts sees the whole
  shape of the work. Each further slice is its own proposal, when its turn comes.

**Worked example (areas mode).** *"A new customer account is set up and served without an engineer
in the loop."* In a repository that plans by program this is the program in the worked examples
below. In a repository that plans by area it becomes two slices:

1. *Accounts are provisioned from the sign-up form, with no engineer* — a slice in the
   `accounts` area. Done when a sign-up creates a working account on the running product.
2. *A first run that needs no help* — a slice in the `onboarding` area, with `Depends on:` the
   first slice. Done when a new account finishes the first run without a support ticket.

Route proposes slice 1 and names slice 2 in `alsoWeighed`; when slice 1 is accepted, slice 2 is
proposed in its turn. No program row is written, so there is nothing to migrate later.

#### When no feature area fits: a new area, with its first slice

In a repository that plans by area every slice names a **feature area** (`planning_mode.py --areas` lists them).
When the request fits none of them, route proposes the slice **together with a new feature area**, and the one
accept creates both: the area's feature map and the slice, in one pull request, with the person who accepted as the
area's first owner<!-- home --> (owner, 2026-10-28, `FLT-1292`)<!-- /home -->. In a repository that plans by program
this does not happen: new work goes under an open program.

**The bar is high, because every new area is one more place every filing must choose between.** Propose a new area
only when all of these hold:

1. **No existing area fits — and you can say why for each close one.** Name the closest existing areas and, for
   each, why the work does not belong there, as evidence from the request. If you cannot write the reason for an
   area, the slice goes under that area. This is the same check as *Say why it is not each smaller rung*, applied
   to areas.
2. **A customer would name it** when describing what the product does (rung 3's test), and it groups capabilities.
3. **It will keep receiving work.** You can name at least two more capabilities it will hold after this first slice.
   A one-off — a single feature, a migration, one customer's list of gaps, a cleanup — is never a new area: put it
   under the closest existing area and say plainly that the fit is weak.

The new area's sentence says what a person can do there, for as long as the area exists; it is never the first
slice's "Done when". The proposal also carries the new map's **feature brief** and its **uses** — the
things a person will do in the area, written to *Writing a feature brief* in the feature-doc reconcile process document.
An area you cannot cut into three uses fails test 3.

**Worked examples (areas mode).**

| Request | Existing areas | Lands on | Why |
|---|---|---|---|
| *"Customers get an invoice each month for what they used."* | accounts, sessions, board | **slice, in a new area `billing`** | Charging for use is a job a customer names on its own ("billing"). Not *accounts*: that is who may sign in. Not *sessions*: that runs the work, it does not charge for it. Billing will keep receiving work: payment methods, refunds, spending limits. |
| *"Show the session's cost next to its duration."* | accounts, sessions, board | **slice (or PRD) in `sessions`** | One more fact on a page that already exists. Even if cost later belongs to billing, this one change does not make a new area. |
| *"Migrate the old export files to the new format."* | accounts, sessions, board | **task, under the area that owns the export** | A one-off. Nothing will keep arriving in a "migration" area. |

#### The program tests — every one must pass

1. **The title is literal.** Someone who reads only the title can say what will be delivered. A
   title that reads well and says nothing fails ("Make it great", "Interrupt PR polling").
2. **A person or a surface.** Either name a person, in a situation, who is stuck today — *when
   `<situation>`, I want to `<motivation>`, so I can `<outcome>`* — or name the thing that lands and
   the customer surface it shows up on. "Runtime work" names neither.
3. **A day it becomes true, and somebody notices.** "A new customer account is set up and
   served without an engineer in the loop" has such a day. "Scalability" does not: a program that
   cannot be shown false on a day is a **theme**.
4. **At least two slices.** Describe the two (or more) deliverables in plain words, each one
   finishing on its own. If you can describe only one, it is a slice.
5. **No existing open home fits.** Create a **new** program only when no existing open home can
   take the work **and** the work holds at least two slices. Joining a home that already exists is
   always the first thing to check.

#### Homes: prefer an existing open one

A **home** is the existing container new work goes into. Before you propose anything new, look for
an existing open home that the work genuinely serves.

- **A home is open when it still takes new work.** One that is withdrawn, or complete, is closed.
- **A closed home is never stretched to fit.** New work for a finished slice is new work: it needs
  an open home of its own. Name the closed home you passed over, and why, so the reader sees it.
- **Never invent a container to give a small piece of work somewhere to go.** A one-deliverable
  request with no good home is still one deliverable; say plainly that the fit is weak and let the
  person who accepts decide.

#### Say why it is not each smaller rung

Whatever rung you land on, write one line for **each smaller work rung** saying why it is not that
rung: a program says why it is not a bug, a task, a PRD or a slice; a slice why it is not a bug, a
task or a PRD; a PRD why it is not a bug or a task; a task why it is not a bug. The line is
evidence from the request, not a restatement of the rung's name. **If you cannot write the line
for a smaller rung, the work is that smaller rung.** This is the check that makes a wrong size
visible to the person who accepts it.

#### Worked examples

| Request | Lands on | Why |
|---|---|---|
| *"A session ignores new messages while it waits on a long PR watch."* | **bug** | Something is broken. A big fix does not change that. |
| *"Maybe one day we support single sign-on with more providers."* | **idea** | Nobody can say yet what done looks like. |
| *"The setup guide is missing the step that creates the API key."* | **bug** | The page is wrong for something that already ships: a docs defect, corrected where the docs live. |
| *"Bump the HTTP client library to the current version."* | **task** (5) | No design, nothing new for anyone to see. |
| *"Add a page listing filings that are still waiting for an answer."* | **PRD** (6) | One screen, one session, testable acceptance criteria. Important is not the same as large. |
| *"Add CSV export to the audit log."* | **PRD** (6) | One agent-session, one surface. |
| *"A reviewer can read the audit record and act on it."* | **slice** (7) | One capability with a "Done when" none of its PRDs proves alone. |
| *"Everything still missing for the acme pilot."* | **slice** (7) | One set of gaps for one customer; the members share nothing else. |
| *"A new customer account is set up and served without an engineer in the loop."* | **program** (8) | A named person notices on a day, and it holds at least two separate deliverables (provisioning, and a first-run that needs no help). **In a repository that plans by area: two slices**, in their own areas, the second depending on the first (see above). |
| *"Rate limiting."* | **component** (1) | You can name the directory. A mechanism is never a planning level. |
| *"Scalability."* | **outcome** (2) | No code owns it and it never finishes; it earns slices while it is being built. |
| *"Security."* | **theme** (4) | A filter across work that already stands alone. Never a new program. |

#### Smell tests

- **A program with one deliverable** is a slice wearing a program's name.
- **A program created from a single request on the day it was filed** almost always failed test 4
  or test 5. Look again.
- **A program whose title describes a defect** ("X ignores Y") is a bug.
- **A slice you cannot write "Done when" for** is not a small slice; it is a label (a theme).
- **A "task" that needs a mockup or an argument about behaviour** is a PRD.
