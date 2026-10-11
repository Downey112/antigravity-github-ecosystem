---
name: research
description: >-
  Navigates the repository, locates symbol definitions (classes, functions), and creates architecture summaries without polluting the main turn context.
---

# Codebase Research Skill (`research`)

Use this skill when exploring unfamiliar code, indexing files, or locating symbols.

## Capabilities
- AST symbol search across Python, JavaScript, and TypeScript files.
- Repository structural hierarchy tree generation.
- Targeted documentation extraction.

## Guidelines
- Do not read entire directories when a symbol search suffices.
- Provide file path and line number references for discovered symbols.
