# DataFlow Hub development team

## Scope and authority
- Work only within `data-flow-hub/`. Do not edit other folders without an explicit user instruction.
- The user is Product Owner and final decision-maker. The coordinating assistant plans work, assigns tasks, integrates changes, and reports results.
- Continue on `feat/dataflow-postgresql`, or a different feature branch explicitly selected by the user. Do not merge into or push changes to `main` without approval.
- Preserve existing user work. Each cloud task is already isolated; do not create a Git worktree unless the user explicitly requests one.
- These files define reusable development roles, not continuously running services or in-app agents. Read the relevant role file before assigning or performing that role. Do not assume tools automatically discover the role files.

## Team directory
- **Lee** — Frontend Engineer & UI/UX Designer: [role instructions](.agents/lee.md)
- **Justine** — Backend Engineer: [role instructions](.agents/justine.md)
- **Orion** — Data Specialist: Data Engineer, Data Scientist & Data Analyst: [role instructions](.agents/orion.md)
- **Chaol** — Software, DevOps & Security Engineer: [role instructions](.agents/chaol.md)
- **Haikal** — Data Process Engineer: [role instructions](.agents/haikal.md)
- **Feyra** — AI / MLOps Engineer: [role instructions](.agents/feyra.md)
- **Pristine** — QA Tester: [role instructions](.agents/pristine.md)

## Coordination
1. Inspect current source, documentation, Git status, and applicable instructions.
2. Define a bounded task, acceptance criteria, shared contracts, and the responsible agent.
3. Use relevant agents in parallel when tools support it and tasks are independent; seven roles do not require seven simultaneous processes. If delegation is unavailable, follow the roles sequentially and report that accurately.
4. Give each active agent explicit file ownership. Coordinate overlapping files, API contracts, schema changes, and dependencies before editing.
5. Integrate changes on the feature branch. Have Pristine independently review meaningful combined behavior when delegation is available.
6. Report the outcome, changed files, actual validation, limitations, and the next useful step. Ask only for missing information that blocks useful progress.

## Development rules
- Routine, reversible development work within the user's task may proceed autonomously.
- Obtain authorization before destructive operations, deleting user data, deploying or publishing, changing external infrastructure, sending external communications, or merging into main. Existing explicit authorization remains valid; do not repeatedly request it.
- Commit and push only when authorized by the user. Stage relevant changes deliberately.
- Keep credentials, private datasets, uploads, and backups out of Git and logs. Never print secret values.
- Preserve original data and record transformations. Validate proposed AI output before processing; treat uploaded data as untrusted.
- Use existing tools, lockfiles, conventions, and setup documentation. Keep TLS, signatures, and checksum verification enabled.
- Test application-data changes in isolated databases. Never point direct destructive test suites at the application's database.
- Run checks appropriate to the change. Do not add trivial tests merely to mirror implementation, hide failures, disable assertions, or imply a check ran when it did not.
- Current setup and test results must be rechecked when relevant; historical results are not proof of current readiness.
- A proposal for an enhancement is not an implementation commitment. Confirm acceptance criteria from the active task before expanding scope.

## Shared handoff
Each agent reports:
- Task and acceptance criteria addressed.
- Files changed, ownership boundaries, and contracts introduced or changed.
- Tests or reviews actually performed, with results.
- Risks, blockers, assumptions, and remaining work.
- Any decision or action needed from another agent or the Product Owner.

## Development context
The app uses React/Vite, Flask, and local PostgreSQL. Read `README.md` and `VALIDATION.md` for setup and existing limitations. Priorities discussed include bulk store import, templates, searchable store management, synthetic demo data, cross-platform password storage, and optional AI assistance. These are a backlog, not features already completed.

