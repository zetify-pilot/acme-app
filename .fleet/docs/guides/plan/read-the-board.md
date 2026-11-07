# Read the Programs list, and set its order

When you are done you will know which programs need you, which are moving and which are stuck, and you will have put the programs in the order you want the fleet to work them.

(If this repository plans by areas.)
Your repository plans by feature area. Most of your work lives on the **Features** page; see [Use the Features page](guides/plan/work-by-area). The Programs list still shows any programs your repository had before it moved to areas, and everything below applies to them.

(If this repository plans by programs.)
Your repository plans by program. The **Programs** page is where you see them all.

## Read a row

Open **Programs** in the sidebar. Each row is one program and links to its page.

| Column | What it says |
|---|---|
| **Id** and **Program** | The program's id and name, with its state |
| **Delivery** | Whether the fleet is driving the program: **driven** or **not driven**. The time estimate, a range of hours drawn from past work and never a date, sits in the **Progress · proof** cell |
| **Priority** | The fleet priority, `P1` to `P4`, or a dash when the program has no rank |
| **To do** | How many moves a person owes on it. The program's page says which |
| **Progress · proof** | Slices done out of slices kept, and whether its proof is named and shipped |
| **Responsible** | Who is responsible for it. See [Narrow Fleet to your programs](guides/plan/my-programs) |

The list is drawn from your repository's knowledge base at a commit. A change merged there appears here without anyone redeploying Fleet.

## Narrow and sort it

**Search id or name…** finds a program by either. **Filter** narrows the list three ways:

- **Status**: **Needs you**, **Stalled**, **Has live work** and **No proof named**. You can tick several.
- **Proven**: **Hidden** when the page opens, so finished programs stay out of the way, or **Shown**. When every program in play is proven, the page shows them anyway rather than open empty.
- **Assigned**: **Assigned to me** (when Fleet knows who you are), **Unassigned**, or one named person.

Each count beside a choice is how many programs it would show. Each filter in force shows as a chip; its × removes it.

**Sort** offers **your priority order** (the default), **most open actions**, **blocks the most**, **live work** and **id**. Under your priority order the list has two groups: **In your order**, top first, and **Not in your order** after it.

Clearing the filters returns the page to how it opens: your priority order, with proven programs hidden — unless every program in play is proven, when they stay in view.

## Set the priority order

The order says which programs matter most. The fleet works by it: an issue takes the higher of the ranks of the program and slice it belongs to.

1. [you] **Press Reorder.** It sits above the list. Filter and sort step aside while you reorder, so the order you save is always the whole list.
2. [you] **Move programs.** Use a row's **Top**, **Up**, **Down** or **Bottom**, or type a number into its position box (3 puts it third). **Take out** removes a program from your order. A program not in your order offers **Place at top** and **Place at bottom**. You can also drag a row by its handle.
3. [you] **Save it.** The bar at the bottom of the screen says whether you have unsaved changes. **Save order** writes the whole order at once; **Cancel** drops your changes.
4. [fleet] **The new order reaches the work.** Issues under each program take its new rank.

> **Tip:** From the keyboard: focus a program row and press Alt Enter to start reordering. ↑ ↓ choose a row, Alt ↑ Alt ↓ move it one place, Alt Home Alt End move it to the top or bottom, a number opens its position box, Delete takes it out, and Escape leaves. Nothing is written until you press **Save order**.

> **Careful:** If someone else saved an order while you were editing, the bar says so and keeps your draft. **Show their order** lets you look at it first; **Save mine over it** replaces it with yours.

A parked program keeps its place in your order while it is parked, so it comes back where you left it.

[Open Programs](#board)

Next: Shape a program and hand it to the fleet (guides/plan/shape-a-program) · Narrow Fleet to your programs (guides/plan/my-programs) · Use the Features page (guides/plan/work-by-area)

---
- **program**: A larger result that two or more slices add up to and none delivers alone, used only by repositories that plan by programs.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.
