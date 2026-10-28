---
name: react-bits-search
description: Search the local React Bits retrieval index and return the best matching components with technical and visual descriptions plus modifiable params
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: retrieval
---

## Purpose

Use this skill to search the local React Bits corpus after the Gemma enrichment and Qdrant index have been built.

This skill is for concrete implementation retrieval, not broad visual ideation.

If the main uncertainty is page direction, layout, or visual language, use `frontend-design-vault` first and turn that result into a narrower React Bits search.

## Expected Result Shape

Return the best candidates with:

- component title and category
- technical description
- visual description
- modifiable params and key parameter details
- preferred variant and available languages/styling
- short reason why the hit fits the query

## Workflow

1. If needed, remind the user that the React Bits index must already be built.
2. Prefer the registered `react-bits-local_search_components` MCP tool instead of shelling out.
3. Use targeted queries, not vague design prompts.
4. Fetch the full component doc only for shortlisted candidates via `react-bits-local_get_component`.
5. Summarize the best hits in chat with:

- title and category
- technical description
- visual description
- modifiable params
- preferred variant
- why the component fits the requested surface

6. Keep the answer focused on selection help and implementation suitability.

## Routing Rule

- `frontend-design-vault` answers: what should this interface feel like and how should it be structured?
- `react-bits-local` answers: what exact component should implement it?
