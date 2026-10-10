# HRMS — Remaining Work, Sprint by Sprint

Based on the Expression of Need (HRMS-EDB-001 v1.0) and the Scrum Master's Sprint Plan (10/09/2026),
checked against the code on `main` at commit `7c3c140` (10/10/2026).

Each item keeps its BN reference so traceability to the Expression of Need is preserved.
Priority: **M** = Must, **S** = Should, **C** = Could.

---

## 1. Where we are today

| Sprint | Module | Status | Notes |
|---|---|---|---|
| 0 | Setup | ✅ Done | Repo, CI (black/flake8/eslint), Swagger docs, seed data |
| 1 | M-01 Organisation | ✅ Mostly done | BN-01 → BN-05 done (company, sites, cost centres, departments hierarchy, classifications, positions). **Missing:** BN-06, BN-07, BN-08 |
| 1 | M-17 Security | 🟡 Partial | Done: BN-169 individual login (JWT), roles (8 profiles), forced password change, 15-min access token, audit log on auth / users / organisation. **Missing:** BN-170 per-module/per-action permissions, BN-171 data perimeter, BN-173 audit on employee data & exports, BN-175 audit export, BN-176, BN-177 |
| 2 | M-02 Employee records | ✅ Mostly done | BN-09 → BN-18, BN-21 done (CRUD + archive, auto matriculation, identity, contacts, family, IDs, bank, admin situation, documents, education, change history). **Missing:** BN-19 *export* of search results, BN-20 expiry alerts |
| 2 | Salary confidentiality | ❌ Not done | Employee API is open to any authenticated user (`IsAuthenticated`), so an employee can read every record → breaks BN-154 / BN-171 |
| 3 → 15 | M-03 … M-16, M-18 | ❌ Not started | Only `contract_type` exists on the employee (no Contract object) |

---

## 2. Adjustment to the original plan

The original plan has attendance (Sprint 4) before work schedules (Sprint 6). But **BN-38** computes
lateness/overtime *by comparison with the employee's schedule*, and **BN-52** excludes public holidays
from leave. Both need schedules and calendars first.

➡️ **Schedule models and calendars (BN-59, 60, 61, 08) move to Sprint 4.** Sprint 6 keeps the
timetable planning and closes attendance. Everything else follows the original order and leads.

---

## 3. Remaining sprints

> 2-week sprints. Dates assume we start Monday 12/10/2026 with no break, so adjust them to the school calendar
> (Sprint 8 falls over the end-of-year holidays).

### Release 1 — Core (finish)

#### Sprint 3 — Contracts + close Release 1 · 12/10 → 23/10/2026
**Goal:** Contracts exist as real objects, access is restricted by role, and Release 1 is demoed end to end.
**Leads:** Dihou (contracts), Abbe (security carry-over)

| Ref | Item | P |
|---|---|---|
| BN-28 | Contract types: permanent, fixed-term, internship, temporary, apprenticeship, service | M |
| BN-29 | Contract details: dates, trial period, notice, weekly hours, workplace, position, remuneration | M |
| BN-30 | Amendments with successive versions and effective dates | M |
| BN-31 | Alert before end of fixed-term contract / trial period (configurable notice) | M |
| BN-34 | Termination: reason, date, notice, leave balance, final settlement placeholder | M |
| BN-32 | Renewal of fixed-term contract with max-renewal control | S |
| BN-33 | Contract suspension and its effect on seniority | S |
| BN-35 | Printable contract / amendment from template | S |
| BN-171 / BN-154 | *Carry-over:* data perimeter on the employee API (own / team / department / all) | M |
| BN-170 | *Carry-over:* permissions per module and per action (consult, create, modify, validate, print, export) | M |
| BN-173 / BN-175 | *Carry-over:* audit trail on employee changes and exports, plus audit-trail export | M |
| BN-19 | *Carry-over:* export employee search results (CSV / Excel) | M |
| BN-174 | *Carry-over:* check password policy and auto-close of inactive sessions | M |

**Demo:** create, search, print and archive an employee with a contract, logged in as HR. Then log in as an employee and show that only their own record is visible.

---

### Release 2 — Time and absence

#### Sprint 4 — Calendars, schedules & attendance capture · 26/10 → 06/11/2026
**Goal:** The system knows when each employee *should* work and records when they *did*.
**Leads:** Noumsi

| Ref | Item | P |
|---|---|---|
| BN-61 | Calendar of working days, rest days and public holidays per site | M |
| BN-08 | Several sites with different calendars (from M-01) | S |
| BN-59 | Work schedule models: fixed, flexible, rotating shifts, part time, breaks | M |
| BN-60 | Assign schedule to employee / position / team / site with effective date | M |
| BN-36 | Record entries/exits, several per day | M |
| BN-37 | Recording methods: manual (HR), self-clocking, file import | M |
| BN-38 | Auto-compute hours worked, lateness, early departure, missing hours, overtime | M |
| BN-39 | Overtime categories: day, night, rest day, public holiday | M |
| BN-180 | Import badge/biometric file in a documented format (see OP-04) | S |

#### Sprint 5 — Leave · 09/11 → 20/11/2026
**Goal:** Every leave balance is always correct and visible, with an online request → approval flow.
**Leads:** Noumsi (leave), Abbe (approval notifications)

| Ref | Item | P |
|---|---|---|
| BN-46 | Configurable catalogue of leave/absence types | M |
| BN-47 | Per type: paid/unpaid, consumes entitlement, proof required, payroll/seniority effect | M |
| BN-48 | Auto-computed entitlement (configurable rule, seniority, extras), with no rule hard-coded | M |
| BN-49 | Acquired / taken / pending / remaining balance per period, visible to the employee | M |
| BN-50 | Leave request with automatic balance control | M |
| BN-51 | Configurable approval circuit (manager → HR): approve / refuse / ask modification | M |
| BN-52 | Exclude rest days and public holidays (uses Sprint 4 calendars) | M |
| BN-56 | Leave allowance computation rule | M |
| BN-57 | Print leave decision, leave certificate, balance summary | M |
| BN-58 | Unpaid absences + leave allowances flagged for payroll (consumed in Sprint 8) | M |
| BN-149 | Employee: see balance, request leave, follow progress | M |
| BN-163 | Notify actors at each step of a request | M |
| BN-53 | Team overlap threshold warning | S |
| BN-54 | Cancel / interrupt / postpone an approved leave | S |
| BN-55 | Annual leave plan as calendar per team / department | S |

#### Sprint 6 — Timetables + close attendance — end of Release 2 · 23/11 → 04/12/2026
**Goal:** Timetables are planned and published, attendance is consolidated and locked, and deadline alerts work.
**Leads:** Noumsi (timetables), Abbe (alerts)

| Ref | Item | P |
|---|---|---|
| BN-62 | Build a timetable over a period; weekly / monthly grid | M |
| BN-63 | Conflict checks: on leave, double assignment, min rest, weekly max | M |
| BN-64 | Publish, notify and print timetable | M |
| BN-40 | Manager approval of overtime before payroll | M |
| BN-41 | Unjustified absences → payroll deduction | M |
| BN-42 | Daily / weekly / monthly attendance sheets, printable and exportable | M |
| BN-45 | Consolidate and lock attendance of the period | M |
| BN-164 | HR deadline alerts: trial end, contract end, document expiry, retirement, anniversary | M |
| BN-20 | Document expiry alert (from M-02) | C |
| BN-43 | Missions / field work not counted as absence | S |
| BN-44 | Clocking regularisation with approval, original kept | S |
| BN-65 | Shift exchange with manager approval | S |
| BN-66 | Duplicate a timetable to another period | S |
| BN-67 | Planned vs actual comparison | S |
| BN-166 | Multi-level approval circuits with substitute | S |
| BN-167 | In-app notification centre + e-mail, user-chosen channels | S |

**Demo (R2):** a month of attendance is captured, a leave request goes from the employee to the manager to HR and the balance updates, and a team timetable is published, printed and compared with actual attendance.

---

### Release 3 — Payroll (main goal)

> Before Sprint 7, the PO must close **OP-01** (list of bonuses/allowances and their rules).
> Before Sprint 10, they must close **OP-02** (consolidated vs per-department entry) and **OP-03** (bank file format).
> Risk **RQ-07** says to run a technical spike on payroll and OHADA during Sprints 5–6.

#### Sprint 7 — Payroll engine · 07/12 → 18/12/2026
**Goal:** A correct payslip for a normal employee, with every rate stored as a dated parameter.
**Leads:** Tsobeng; whole team

| Ref | Item | P |
|---|---|---|
| BN-87 | Configurable catalogue of salary elements | M |
| BN-88 | Element rules: gain/deduction, method, contributory, taxable, leave base, payslip order | M |
| BN-89 | Contribution & tax parameters as **dated versions** (CNPS, IRPP, etc.) | M |
| BN-90 | Salary grid by category / grade / echelon + minimum wage control | M |
| BN-91 | Element values at 3 levels: default → category/department → individual | M |
| BN-92 | History of every parameter change | M |
| BN-93 | Payroll period life cycle: opened → … → closed, traced | M |
| BN-95 | Gross, bases, employee + employer contributions, tax, net payable | M |
| BN-96 | Pro-rata for hire / departure / suspension / unpaid absence | M |
| BN-104 | Run for whole organisation, a department, or one employee | M |

#### Sprint 8 — Payroll hard cases · 21/12/2026 → 01/01/2027 ⚠️ holidays
**Goal:** Overtime, advances, back pay and final settlement work, and an invalid payroll cannot be validated.
**Leads:** Tsobeng; whole team

| Ref | Item | P |
|---|---|---|
| BN-94 | Variable elements: manual or auto-pulled from attendance / leave / career | M |
| BN-97 | Overtime pay by category and rate | M |
| BN-98 | Advances and loans with repayment schedule | M |
| BN-100 | Retroactive adjustments (back pay) | M |
| BN-103 | Final settlement on departure | M |
| BN-106 | Block validation on anomalies (negative net, < minimum, no bank, no contract, zero base) | M |
| BN-108 | Lock after validation; correction only by reversal | M |
| BN-109 | Full payroll history, reprint any past period | M |
| BN-172 | Salary data visible only to authorised payroll/HR profiles; access logged | M |
| BN-99 | Third-party deductions (garnishment, alimony, union dues) | S |
| BN-101 | Periodic bonuses (13th month, seniority, leave allowance) | S |
| BN-102 | Benefits in kind valuation | S |
| BN-105 | Simulation mode | S |
| BN-107 | Period-over-period comparison before validation | S |
| BN-112 | Provision for untaken leave | S |

#### Sprint 9 — Payslips & documents · 04/01 → 15/01/2027
**Goal:** Every payroll and HR document prints correctly, individually or in batch, from a template.
**Leads:** Abbe (documents), Tsobeng (payroll data)

| Ref | Item | P |
|---|---|---|
| BN-113 | Legally complete individual payslip | M |
| BN-114 | Batch printing (organisation / department / selection) in one file | M |
| BN-115 | Identical reprint marked "duplicate" | M |
| BN-117 | Payroll book and summary with totals | M |
| BN-118 | Statement of contributions and taxes withheld | M |
| BN-119 | Statutory declarations (DIPE / CNPS) in required format | M |
| BN-120 | Annual individual salary statement + annual tax summary | M |
| BN-110 / BN-121 | Payment by transfer/cheque/cash; payment order + bank file per bank | M |
| BN-111 | Amounts due to CNPS and tax administration with due dates | M |
| BN-123 | Certificates: work, employment, salary, presence, leave, end of contract, final settlement | M |
| BN-124 | Contract, amendment, promotion, transfer, disciplinary letter from templates | M |
| BN-126 | Export every list/report to spreadsheet and PDF | M |
| BN-165 | Alert payroll officer of cycle and declaration due dates | M |
| BN-116 | E-mail payslip / publish to portal, protected | S |
| BN-122 | Pay register, cash-paid list and receipt | S |
| BN-125 | Template editing (header, logo, signatures) without development | S |
| BN-127 | Archive a copy of every issued document | S |

#### Sprint 10 — OHADA accounting — end of Release 3 · 18/01 → 29/01/2027
**Goal:** Validated payroll becomes a balanced OHADA entry automatically, with nothing typed twice.
**Leads:** Tsobeng (accounting), Abbe (export); whole team

| Ref | Item | P |
|---|---|---|
| BN-128 | Configurable OHADA chart of accounts (classes, sub-accounts) | M |
| BN-129 | Versioned mapping element → expense / counterpart / third-party account | M |
| BN-130 | Default class 6 / 4 / 5 accounts, adaptable by the accountant | M |
| BN-131 | Auto-generate payroll entry on validation | M |
| BN-132 | Reject any unbalanced entry | M |
| BN-133 | Consolidated or broken down by department / site / cost centre | M |
| BN-134 | Salary payment entry | M |
| BN-135 | Contribution and tax settlement entry | M |
| BN-137 | Accounting periods and financial year, closed-period protection | M |
| BN-138 | Continuous numbering per journal, no edit/delete, reversal only | M |
| BN-139 | Payroll journal + miscellaneous operations journal | M |
| BN-140 | Entry → payroll period → payslips traceability | M |
| BN-141 | Journal book, general ledger, trial balance, balances per employee/body | M |
| BN-142 | Payroll ↔ entry reconciliation | M |
| BN-143 / BN-181 | Export entries to accounting software; import chart of accounts; bank export | M |
| BN-146 | Single currency and rounding rule, no payroll/accounting gap | M |
| BN-147 | Trace every accounting operation; legal retention | M |
| BN-136 | Provisions for paid leave and their reversal | S |
| BN-144 | Personnel expense analysis vs budget | S |
| BN-145 | Elements for OHADA annual financial statements | S |

**Demo (R3, main goal):** calculate → compare → validate → print payslips → declarations → accounting entry → export.

---

### Release 4 — Career and steering

#### Sprint 11 — Careers · 01/02 → 12/02/2027
**Goal:** Promotions, transfers and departures are recorded with an effective date and reach payroll automatically.
**Leads:** Dihou

| Ref | Item | P |
|---|---|---|
| BN-68 | Promotion with effective date, auto effect on base salary | M |
| BN-69 | Transfer / affectation with effect on org chart and cost centre | M |
| BN-71 | Salary revisions independent of promotion | M |
| BN-73 | Departure for any reason → triggers final settlement | M |
| BN-74 | Career timeline per employee | M |
| BN-75 | Print decision documents | M |
| BN-06 | Structure history with effective dates, "as at date" view (from M-01) | S |
| BN-70 | Temporary assignment / acting / secondment with auto-return | S |
| BN-72 | Disciplinary measures with payroll effect | S |
| BN-76 | Approval circuit before payroll-impacting acts become final | S |

#### Sprint 12 — Reports & dashboards — end of Release 4 · 15/02 → 26/02/2027
**Goal:** Management sees reliable figures without extra work.
**Leads:** Abbe (reports), Dihou (career figures)

| Ref | Item | P |
|---|---|---|
| BN-155 | Dashboard per profile (figures and charts), replacing the template's e-commerce dashboard | M |
| BN-156 | Headcount indicators | M |
| BN-157 | Movement indicators: hires, departures, turnover, promotions, transfers | M |
| BN-158 | Time indicators: absenteeism, lateness, overtime, leave | M |
| BN-159 | Payroll indicators | M |
| BN-160 | Filters, export and print on every report | M |
| BN-07 | Organisation chart display and print (from M-01) | S |
| BN-161 | Custom report builder | C |
| BN-162 | Scheduled report e-mails | C |
| BN-168 | Escalation of unanswered requests | C |

---

### Release 5 — Extension

#### Sprint 13 — Self-service portal · 01/03 → 12/03/2027
**Leads:** Noumsi (portal), Abbe (security)

| Ref | Item | P |
|---|---|---|
| BN-153 | Manager: approve team requests, team attendance & leave calendar, propose promotions, **never see salaries** | M |
| BN-154 | Re-test: an employee can never access another employee's data | M |
| BN-177 | Personal data protection: purpose, minimisation, retention (OP-05), right to consult/rectify | M |
| BN-148 | Employee consults own record, requests correction | S |
| BN-150 | Download own payslips and attestations | S |
| BN-151 | Own attendance, timetable and shifts | S |
| BN-182 | English / French interface and documents | S |
| NF-08 | Mobile-friendly portal | S |
| BN-152 | Request a document and get notified | C |
| BN-176 | Second factor for payroll profiles | C |

#### Sprint 14 — Evaluation & recruitment · 15/03 → 26/03/2027
**Leads:** Dihou (evaluation), Noumsi (recruitment)

| Ref | Item | P |
|---|---|---|
| BN-82 → BN-86 | Campaigns, objectives, self/manager evaluation, final score, link to promotion/bonus, printed review | S |
| BN-22 → BN-25 | Recruitment need, job offer, application pipeline, convert hire → employee record | S |
| BN-26, BN-27 | Onboarding checklist, candidate pool | C |

#### Sprint 15 — Training + go-live · 29/03 → 09/04/2027
**Leads:** Whole team

| Ref | Item | P |
|---|---|---|
| BN-77 → BN-81 | Skills repository, training plan & budget, sessions, results, cost follow-up | C |
| BN-179 | Import initial data from spreadsheets with rejection report | M |
| BN-183 / NF-05 | Automatic daily backup and controlled restore | M |
| DL-06 | Data recovery report | — |
| DL-07 / NF-11 | User guide per profile, admin guide, calculation rules | — |
| DL-08 | User training and first real payroll cycle | — |

---

## 4. Applies to every sprint

- **BN-178 (M):** every new reference list (leave types, salary elements, templates, circuits, mapping) is configurable without code.
- **Non-negotiable rules:** no rates in code · keep history, never delete · enter data once · least privilege, salary access logged · everything printable.
- **NF-01 / NF-07 / NF-09:** check response time (< 3 s), the rounding and currency format, and data protection at each sprint review.

## 5. If time runs short

As the Scrum Master's note says, **Sprint 10 (working payroll + OHADA entry) is the real target**.
If the calendar only allows Sprints 3–10, drop the **S** and **C** items inside those sprints first.
Then deliver Releases 4 and 5 after the PO agrees.
