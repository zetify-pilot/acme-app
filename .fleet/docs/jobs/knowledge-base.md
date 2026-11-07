# Learn the knowledge base

Every repository Fleet works on keeps a `knowledge/` folder beside its code. It says what the product lets people do, what it promised, what was decided and what is changing now. Read this path and you will know what each part is for, which parts finish, and how to keep it true as the code changes.

## The big picture

| In the knowledge folder | Part | Holds |
|---|---|---|
| Planning: what is changing | Features | Parts of the product a customer names; never finish |
| | Slices | One sentence each that will be true when a piece of work is done |
| | PRDs | What one agent session builds, with the checks it must pass |
| | Programs (optional) | A larger result several slices add up to |
| The product: what is true | Capabilities and components | What someone can do; what is built |
| | Journeys | How a person gets a whole job done |
| Commitments: what must stay true | Promises | Numbered requirements, never deleted |
| | Decisions | Why a choice was made, so it outlives the conversation |
| About your repository | Slots | Your answers to the questions the commands ask |
| | Records | Check results, audits and retros |
| | Generated tables | Rendered from files, never edited by hand |

The folder answers four questions. **Planning** says what is changing: feature areas hold slices, and slices are made true by PRDs, with programs grouping slices in some repositories. **The product** says what is true now: the capabilities a person can use, the components that are built, and the journeys people take through them. **Commitments** say what must stay true: promises written as numbered requirements, and decisions that record what was chosen and why. **About your repository** holds the rest: slots that answer the questions Fleet's commands ask, records of what checks and runs found, and tables generated from files.

Most of it never finishes. A feature area, a capability or a requirement is true for as long as the product is, so it has no status. Only work finishes: a slice, a PRD, a program. Only a PRD's status is ever written, and Fleet works out the rest. Every change to the folder arrives as a pull request, reviewed like code. Agents read it before they build, the Programs and Features pages are drawn from it, and the Quality desk checks the running product against its promises.

## Read these in order

1. **The knowledge base** (knowledge-base/overview): The knowledge folder each repository keeps: what the product does, what it promised, and what is changing. Fleet plans and checks against it.
2. **The knowledge folder, file by file** (knowledge-base/the-folder): Where each kind of knowledge lives under knowledge/, what each file holds, and who writes it.
3. **Features, uses and capabilities** (knowledge-base/feature-areas): A feature is a part of the product a customer would name: a brief says what it is, uses say what people do with it, capabilities make each use work.
4. **Slices** (knowledge-base/slices): A slice is one deliverable with one sentence that says when it is done. What makes a good one, where it lives, and how it finishes.
5. **PRDs** (knowledge-base/prds): A PRD is one piece of work one agent can build in one session, with criteria that each can be shown to pass. It is the only thing whose status is written.
6. **Promises and requirements** (knowledge-base/promises): What the product has committed to, kept as numbered requirements that are never deleted, cited by id, and checked by the Quality desk.

## Then, keep it true

- **Start a knowledge base in a repository** (guides/knowledge/start-a-knowledge-base): Give a repository its planning record and Fleet's commands, from the Set up page or with fleet init in a terminal.
- **Build the knowledge for code you already have** (guides/knowledge/describe-existing-code): Run the knowledge bootstrap: an agent drafts your product's description from the code, one part at a time, and you confirm what it promises.
- **Answer the questions the commands ask about your repository** (guides/knowledge/fill-slots): Replace the placeholder slot answers fleet init wrote, so every command can run in your repository and none runs half-blind.
- **Record a decision so it outlives the conversation** (guides/knowledge/record-a-decision): Your answers to Fleet's questions are kept on the issue for you; a decision the whole product should follow goes in a dated decision record.
- **Keep your feature maps true to the code** (guides/knowledge/keep-maps-current): When you change code a feature map describes, correct the map's facts in the same pull request, and never rewrite its intent to match the code.
- **Move a repository from programs to feature areas** (guides/knowledge/move-to-areas): Give every live slice its feature area with fleet planning migrate, and optionally stop programs taking new slices, by one pull request you review.
- **Fix a failing knowledge check** (guides/knowledge/fix-a-failing-check): Read what fleet check printed, find the file and the fix it names, and get your pull request green without weakening the check.
- **Run the knowledge checks in your CI** (guides/knowledge/run-checks-in-your-ci): Add one GitHub Actions job that runs fleet check on every pull request, so a broken knowledge base fails the build before it merges.

## When you need it

- **Planning by areas or by programs** (knowledge-base/planning-modes): A repository plans in one of two modes. Both put every slice under a feature area; only one also groups slices into programs.
- **Sorting something new: which kind of thing is it?** (knowledge-base/what-is-it): Walk the planning ladder to decide whether a request is a bug, an idea, a task, a PRD, a slice or a program, in the order that removes the doubt.
- **Programs** (knowledge-base/programs): In a repository that plans by programs, a program is a larger result that two or more slices add up to, proven by a check of its own.
- **Capabilities and components** (knowledge-base/capabilities-and-components): A capability is something a person can do with the product. A component is a part of the system you build. They are mapped to each other, never one to one.
- **Journeys** (knowledge-base/journeys): A journey is how one kind of person gets a whole job done with the product, written as numbered criteria anyone can check.
- **Decisions** (knowledge-base/decisions): A decision record keeps a choice someone made, the option they turned down and why, so a later change cannot quietly reverse it.
- **Slots: your repository's answers** (knowledge-base/slots): Fleet's commands are the same in every repository. Slots are the questions they ask about yours: how to test it, how branches work, where things live.
- **Records: check results, audits and retros** (knowledge-base/records): What happened, kept as written: a file for every check run, a record for every audit, and the retros agents write after their runs.
- **Generated tables** (knowledge-base/generated-tables): Some tables in the knowledge folder are rendered from one file per row and never edited by hand. Which ones, why, and what to do instead.
