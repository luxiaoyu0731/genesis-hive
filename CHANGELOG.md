# Changelog

## Unreleased

- Invalidate executor reuse when goal, strategy, task graph, budget or upstream inputs change.
- Reject cyclic/unassigned dependencies before execution; isolate task exceptions and retry failed results.

