# Explicit schema migration

The validator accepts plan schema 3 and root/leaf config schema 1 only. Missing, Boolean, older, or future versions fail with a migration message. Lowering a version never disables mandatory config checks.

For an older project plan, save complete file-state snapshots/backups first. Preserve IDs, order, criteria, flags and history. Materialize missing leaf configs using the actual procedures and matching work_id. Add a root config matching the project's existing root child order. Review command resolution/checks and migrate referenced config structure where needed. Set plan schema 3 only after required files exist.

Show the full candidate diff and resume impact, obtain approval, validate the candidate, then apply using multi-file manifest checks. Session additions preserve existing data; missing historical snapshots mark affected results stale rather than inventing old content. Future unknown schemas require a compatible tool or documented user-assisted migration.

A declared older plan is the exception to validating the original with the current validator: perform this explicit migration while requiring the candidate to pass before applying it. Invalid current-schema plans still require intervention.
