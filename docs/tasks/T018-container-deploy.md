# T018 — Package the app as a container for Aiven Runtime

**Owner:** Jasumar **Status:** review
**Branch:** `task/t018-container-deploy`

## Goal

The coach (API + UI, full dataset) runs as one Docker container that Aiven Runtime can
build from this repo. The AI stays on the existing Modal or OpenRouter API.

## Allowed files

```text
Dockerfile
.dockerignore
apps/bank-backend/server.py   (bind address only)
.env.example, README.md, docs/tasks/Decisions.md, this file
```

**Shared surfaces touched:** `.env.example` (new optional key `HOST`), root `README.md`,
`docs/tasks/Decisions.md` (#65). Requested by the user.

## Depends on

- Needs merged first: none
- Blocks: none

## Acceptance criteria

- [ ] `docker build --build-arg DATA=fixture .` builds; the container answers
      `GET /api/health` on port 8080.
- [ ] `docker build .` builds the full database into the image.
- [ ] Without `HOST` the local server still binds to 127.0.0.1.
- [ ] Deployed on Aiven Runtime with AI keys as secrets (manual step).

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh
docker build -t spankki-coach --build-arg DATA=fixture .
docker run --rm -p 8080:8080 spankki-coach
```

## Notes

Data is baked into the image instead of a managed database: it is read-only, and Aiven
Runtime is for stateless apps. Plan memory/disk limits were not checked; the full image
holds a ~0.5 GB database.
