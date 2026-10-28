---
name: react-bits-copy
description: Copy a selected React Bits component variant into a target directory
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: copy
---

## Purpose

Use this skill after a React Bits component and variant have already been chosen.

Do not use it during exploration. Copy only after the design direction and component selection are already clear.

## Required Inputs

Pass enough information to determine:

- category
- slug
- variant id
- target directory

## Workflow

Prefer the registered `react-bits-local_copy_component_variant` MCP tool.

Then report:

- which variant was copied
- where it was copied
- which files were written

## Integration Rule

After copying, adapt the code to the project’s tokens, spacing, typography, and existing visual language. React Bits is a source of implementation primitives, not a reason to replace the project’s design system.
