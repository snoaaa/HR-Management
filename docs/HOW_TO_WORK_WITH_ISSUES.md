# How to work with issues — HRMS project

This page explains how our backlog is organised on GitHub and how to use it every day to plan and track work. It applies to every member of the team.

---

## 1. The big picture

| On GitHub | In Scrum | Example |
|---|---|---|
| **Issue** | One task to build | `Sprint2Task7 — US-015 Record bank details and payment method` |
| **Milestone** | One sprint | `Sprint 2` |
| **Label** | A way to filter tasks | `epic:EP-07`, `topic:security`, `priority:M` |
| **Project board** | Our shared board | To do → In progress → In test → Done |
| **Pull request** | The code that delivers a task | `Sprint2Task7 — bank details` with `Closes #45` |

The backlog contains every user story of the Product Backlog (US-001 to US-183) plus the sprint tasks that have no user story (setup, foundations, security measures, release demos, go-live).

---

## 2. How tasks are named

Every issue title starts with **`SprintNTaskM`**:

- **N** = the sprint (0 to 15).
- **M** = the order in which the task should be built inside that sprint.

`Sprint2Task1` comes before `Sprint2Task2`. Following the numbers means you never start something before what it needs.

After the name comes the user story id (when there is one) and a short title:

- `Sprint7Task8 — US-095 Calculate gross, contributions, tax and net pay` (a user story)
- `Sprint0Task6 — UML: actors and use-case diagrams` (a sprint task with no user story)

---

## 3. What is inside an issue

Every issue has the same sections, in this order:

| Section | What it tells you |
|---|---|
| **User story** / **Work to be done** | What the user needs and why |
| **Acceptance criteria** | How the Product Owner will check it (Given / When / Then) |
| **Scope in this sprint** *(some issues only)* | What part is done now and what part is completed later |
| **What to do** | A checklist of the technical steps |
| **Security** | The security checks that apply to this task, with links to the task that provides the protection |
| **Dependencies** | The order, the wave, what blocks this task and what it blocks |
| **Definition of Done** | The checklist that must be complete before closing |
| **The 5 rules we never break** | No rates in code · keep the history · enter data once · show only what the role allows · everything must print |
| **Planning** | User story, business need (BN), module, epic, sprint, release, sprint lead, priority, story points |

### Reading the Dependencies section

- **Order** — the `SprintNTaskM` name of the task.
- **Wave** — tasks with the same wave number in a sprint do not depend on each other, so different people can do them at the same time.
- **Blocked by** — tasks that must be **closed** before you start this one. Click the links to check them.
- **Blocks** — tasks waiting for this one. When you finish, the people on those tasks can start.

---

## 4. Labels

| Label | Meaning |
|---|---|
| `type:user-story` | A user story from the Product Backlog |
| `type:task` | A sprint task with no user story (setup, foundations, demo, go-live…) |
| `epic:EP-01` … `epic:EP-12` | The epic (large functional area). `EP-00` = project setup, delivery and go-live |
| `module:M-01` … `module:M-18` | The module of the Expression of Need |
| `release:R-1` … `release:R-5` | The release the task belongs to |
| `priority:M` / `S` / `C` | MoSCoW: Must, Should, Could |
| `topic:security` | Security, access control, audit, privacy |
| `topic:printing` | Produces a printable document (PDF) |
| `topic:testing`, `topic:documentation` | Testing / demo, documentation / training |
| `area:backend`, `area:frontend`, `area:devops` | Technical area of a sprint task |

Epics are **labels, not issues**. To see all the work of an epic, filter with its label (for example `label:epic:EP-07`).

---

## 5. The life of a task

```
 To do  →  In progress  →  In test  →  Done
              │
              └──→  Blocked (tell the Scrum Master)
```

1. **Choose a task** in the current sprint milestone: the lowest-numbered open task that has **no assignee** and whose *Blocked by* tasks are all **closed**.
2. **Assign yourself** (right-hand panel of the issue → *Assignees*). This tells everyone the task is taken.
3. **Move the card to *In progress*** on the board.
4. **Create a branch** that contains the task name, following `BRANCHING_STRATEGY.md`, for example:
   `feature/Sprint2Task7-bank-details`
5. **Tick the checkboxes** of *What to do* and *Security* in the issue as you progress. Anyone can then see where the task stands without asking.
6. **Open a pull request**:
   - title starts with the task name: `Sprint2Task7 — bank details`
   - description contains **`Closes #<issue number>`** (the number shown after the title, e.g. `#45`)
7. **Move the card to *In test*** while the pull request is reviewed and the acceptance criteria are checked.
8. **Merge** the pull request into `main` once it is reviewed and CI is green. Because of `Closes #45`, the issue **closes automatically** and the milestone progress bar moves.
9. **Move the card to *Done*** if the board does not do it automatically.

### Tasks without code

UML diagrams, studies, Definition of Done, guides, demos: follow the same steps. Put the result in `docs/` (through a pull request) or attach it in a comment on the issue, tick the boxes, then close the issue.

### When you are blocked

- Move the card to **Blocked**.
- Write a comment on the issue explaining what blocks you.
- Tell the Scrum Master straight away (stand-up or message). Do not wait.

---

## 6. Closing an issue properly

Close an issue only when:

- every box of **What to do** and **Security** is ticked (or a comment explains why one does not apply);
- every box of the **Definition of Done** is ticked;
- the acceptance criterion has been checked on the test environment;
- the evidence is visible: merged pull request, file in `docs/`, screenshot or comment.

A task that is 90 % done is still open: it does not count in the sprint. Finishing tasks completely is more valuable than starting many.

---

## 7. Useful searches

Type these in the search bar of the **Issues** tab:

| To see | Search |
|---|---|
| The tasks of a sprint | `is:issue milestone:"Sprint 0"` |
| What is still open in a sprint | `is:open milestone:"Sprint 0"` |
| Free tasks in a sprint | `is:open no:assignee milestone:"Sprint 0"` |
| My open tasks | `is:open assignee:@me` |
| All security work | `is:issue label:topic:security` |
| One epic | `is:issue label:epic:EP-07` |
| Must-have tasks still open | `is:open label:priority:M` |
| Tasks that produce documents | `is:issue label:topic:printing` |

The **Milestones** page (Issues → Milestones) shows the progress bar of each sprint.

---

## 8. Issues in our Scrum events

| Event | How we use the issues |
|---|---|
| **Sprint planning** | Open the sprint milestone. Read the tasks in order, confirm the estimates, and share the tasks of the same wave between members so they can work in parallel. Each member assigns themselves. |
| **Daily stand-up (15 min)** | Open the board. Each member points to their cards: what was done, what is next, what is blocked. |
| **During the sprint** | Keep cards and checkboxes up to date; comment on the issue instead of discussing only in chat, so decisions stay with the task. |
| **Sprint review** | Show the closed issues and the milestone progress to the Product Owner; the release demo tasks (end of Sprints 3, 6, 10, 12, 15) hold the scenario to play. |
| **Retrospective** | Look at the tasks that stayed *Blocked* or *In progress* the longest and agree how to avoid it. |

---

## 9. Rules to keep the backlog reliable

- **Do not delete the first line of an issue description** (`<!-- hrms-key: ... -->`). It is hidden and identifies the task for our backlog script.
- **Do not rename the `SprintNTaskM` part of a title.**
- **Do not create duplicate issues** for work that already exists. If something is missing, tell the Scrum Master, who agrees it with the Product Owner.
- **Editing is welcome:** ticking boxes, adding comments, attaching files, assigning yourself and moving cards are exactly how the issues should be used.
- **Security is part of every task:** the *Security* section of an issue is part of its Definition of Done, not an optional extra.

---

## 10. Quick questions

**Can I work on a task from the next sprint?**
Only if every task of the current sprint is taken or blocked, and the next-sprint task's *Blocked by* list is closed. Tell the team at stand-up.

**Two tasks have the same wave. Which one first?**
Either. The same wave means they are independent. Take the one with the lower number if you are alone.

**The task is too big for me alone.**
Say it at stand-up. Pair with someone (both can be assignees), or ask the Scrum Master to split it.

**I found a bug in a closed task.**
Open a new issue describing the bug, reference the original task (`Related to #45`) and tell the Scrum Master so it is prioritised.

**Where are the conventions and the order of all tasks?**
In `docs/SPRINT_PLAN.md`.
