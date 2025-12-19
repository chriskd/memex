---
title: Deployment with Dokploy
tags:
  - deployment
  - dokploy
  - ci-cd
created: 2024-12-19
contributors:
  - agent
---

# Deployment with Dokploy

Apps are deployed to **Dokploy**, a self-hosted PaaS similar to Heroku or Railway.

## Deployment Workflow

Push to main branch triggers auto-deploy:

```bash
git push origin main  # Triggers Dokploy build and deploy
```

No additional CI/CD configuration needed - Dokploy watches the repository.

## Environment Configuration

- Environment variables are configured in the Dokploy UI
- Secrets come from **Phase** (never hardcoded)
- Database URLs, API keys, etc. are injected at runtime

## Production Patterns

### FastAPI/Starlette Apps

Most projects use uvicorn:

```bash
# Production startup (via Dockerfile CMD)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

See [[devops/docker-patterns]] for the standard Dockerfile.

### Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Server | `uvicorn --reload` | `uvicorn` (no reload) |
| Secrets | `.env` file | Phase via Dokploy |
| Database | Local/dev instance | Production instance |

## Security Rules

**Never commit secrets.** All sensitive configuration must come from:
- Phase for secrets management
- Dokploy environment variables for non-secret config

## Related

- [[devops/docker-patterns]] - Dockerfile patterns for deployment
- [[development/python-tooling]] - Local development setup
