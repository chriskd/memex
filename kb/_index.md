---
title: Voidlabs Knowledge Base
tags:
  - index
  - overview
created: 2024-12-19
---

# Voidlabs Knowledge Base

This knowledge base contains operational guidance, patterns, and documentation for voidlabs projects. It serves as a reference for both human developers and AI agents working in this environment.

## Categories

### [[devops/]]
Deployment, CI/CD, and operational concerns.
- [[devops/deployment]] - Dokploy deployment workflow
- [[devops/docker-patterns]] - Dockerfile patterns with uv

### [[development/]]
Development tooling and practices.
- [[development/python-tooling]] - Python development with uv
- [[development/project-structure]] - Standard project layout

### [[infrastructure/]]
Environment and infrastructure setup.
- [[infrastructure/devcontainers]] - Devcontainer configuration

### [[architecture/]]
System design and architectural decisions.

### [[patterns/]]
Coding patterns and philosophy.
- [[patterns/clean-changes]] - Clean changes over backwards compatibility

### [[troubleshooting/]]
Common issues and solutions.

## Contributing

To add new entries:

1. Create a new `.md` file in the appropriate category directory
2. Include proper frontmatter:
   ```yaml
   ---
   title: Entry Title
   tags:
     - relevant
     - tags
   created: YYYY-MM-DD
   contributors:
     - your-name
   ---
   ```
3. Use `[[bidirectional links]]` to connect related entries
4. Keep entries focused on one topic
5. Include actionable content and code examples

## Usage

This KB is available as a Claude Code plugin. AI agents can query entries for operational guidance. Entries are designed to be:

- **Focused** - One topic per file
- **Actionable** - Include commands and examples
- **Connected** - Link to related entries
- **Current** - Update when practices change
