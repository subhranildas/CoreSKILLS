# Workflow insertion schema

The plan contains `entrypoint`, flat `nodes`, and ordered `children` references. `parent_id` must agree with the parent's child list. Workflow nodes contain children; work nodes are leaves. Every entry has `id`, `kind`, and explicit Boolean `skippable`. Added workflows also define aggregate `criterion`; added work defines both `criterion` and `verification_procedure`.

Example insertion, not an automatically installed stage:

```yaml
- id: resource-analysis
  parent_id: verification
  kind: workflow
  skippable: true
  criterion: Selected images meet the agreed memory budget
  children: [inspect-memory]
  depends_on: [build-matrix]
- id: inspect-memory
  parent_id: resource-analysis
  kind: work
  skippable: false
  criterion: Each selected image fits its recorded RAM and flash limits
  work_config: leaves/inspect-memory.yaml
  verification_procedure: Inspect the linker map and compare usage with the platform budget; record observations and evidence
  procedure: procedures/resource-analysis.md
```

Insert `resource-analysis` into `verification.children` after `build-matrix`, then create the referenced procedure relative to the plan directory. Keep that procedure explicit about inputs, checks, failure intervention, and outputs. An existing `skill` name can be used instead; verify that it is installed. A supplied procedure must resolve to an existing file.

Create `leaves/inspect-memory.yaml` with the matching `work_id` and editable steps/checks using the bringup leaf template. In plan schema version 2+, every work entry requires a valid `work_config` file; a procedure or skill alone does not replace it.

`depends_on` is a list of node IDs whose completed, valid results are required before this node starts. It is not the parent/child relationship. Dependencies must finish earlier in the depth-first sequential order, cannot point to self/ancestors/descendants, and cannot form a cycle. Repeated/expanded template IDs are resolved to concrete session IDs before execution; record per-instance prerequisites. A skip never satisfies a required dependency merely by occupying an earlier position.

Keep the existing global commit/report templates, including `skippable` on each. The editor generates no duplicate static commit/report child for every future work; those are instantiated by the parent at execution. If alternative behavior is requested, explicitly show the policy change and its completion impact rather than silently changing templates.
