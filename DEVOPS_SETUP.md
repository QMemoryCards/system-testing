# DevOps setup for QMemoryCards

Commands marked "from the workspace root" assume the directory that contains
the `backend`, `frontend` and `system-testing` repositories.

This file lists what is automated in the three repositories and what must be
configured once in the GitHub UI. Everything that can live in code is already
in the repositories.

## Pipeline

```
backend  PR/push ──► lint ─► unit + integration tests ─► build ─► docker build ─► smoke test ─┐
                                                                                             ├─► ghcr.io/qmemorycards/backend:{sha-<commit>,latest}
                                                                                             │
frontend PR/push ──► lint ─► format ─► type-check ─► Vitest ─► docker build ──────┤
                                                                                             ├─► ghcr.io/qmemorycards/frontend:{sha-<commit>,latest}
                                                                                             │
                                                                                             └─► repository_dispatch
                                                                                                       │
system-testing ──► resolve image digests ──► docker compose up ──► pytest (Playwright) ───────────────┤
                                                                                                       │
                                                                                                       ├─► deploy dev  (self-hosted runner, label `dev`)
                                                                                                       └─► deploy prod (self-hosted runner, label `prod`, manual approval)
```

- `repository_dispatch` is used to start system tests after an image push.
  `workflow_run` cannot cross repositories, and polling GHCR is slower and
  races with the next push. A nightly schedule stays as a fallback.
- System tests run against the exact image digests they resolved. The deploy
  jobs receive those digests from the `e2e` job, so production gets the tested
  bytes, not whatever `latest` points to later.
- Prod deployment has a GitHub Environment with required reviewers. Dev has no
  reviewer gate.

## What changed in the repositories

### backend

- `.github/workflows/main.yaml`
  - Runs ktlint, unit tests, Testcontainers integration tests, build, coverage.
  - Builds the image once, starts the database and backend containers, waits
    for health, then pushes `sha-<commit>` and `latest` tags on `main`.
  - Pushes a `vX.Y.Z` image tag and creates a GitHub Release on tag pushes.
  - Sends `repository_dispatch` to `QMemoryCards/system-testing` after a push
    to `main`.
- `Dockerfile`: runtime image is `eclipse-temurin:21-jre-jammy`, non-root user,
  `curl`, and a Docker `HEALTHCHECK`.
- `.dockerignore`: keeps `.env`, `.git`, build outputs and IDE files out of the
  image.
- `docker-compose.yaml`: image names come from `BACKEND_IMAGE` / `FRONTEND_IMAGE`,
  healthchecks on all services, `depends_on: service_healthy`, configurable
  host ports.
- `.env` is no longer tracked. Use `.env.example` as the template.

### frontend

- `.github/workflows/ci.yml` (renamed from `main.yaml` to get a fresh workflow
  ID after GitHub disabled the old scheduled workflow for inactivity)
  - Adds lint, Prettier check and app type-check, and runs the full Vitest
    suite (not only the integration subset).
  - Builds the image, starts the container and checks the static page, pushes
    `sha-<commit>` and `latest` on `main`, creates a release on `vX.Y.Z` tags,
    and dispatches system tests.
- `Dockerfile`: Docker `HEALTHCHECK`.
- `docker-compose.yaml`: same healthcheck and image-variable changes as backend.
- `.env` is no longer tracked. Use `.env.example` as the template.
- Test files are linted with relaxed `no-explicit-any` and react-refresh rules;
  application code keeps the strict rules.

### system-testing

- `.github/workflows/main.yaml` is now the only workflow:
  - `push` / `pull_request` to `main`: run E2E against the current `latest`
    images.
  - `repository_dispatch: images-published`: run E2E after backend/frontend
    publish a new image, then deploy.
  - `schedule`: nightly E2E smoke test without deployment.
  - `workflow_dispatch`: manual run, with an optional `deploy` checkbox.
  - Resolves image digests, runs the stack with `docker compose up --wait`,
    runs Playwright, prints logs on failure, and always tears the stack down.
  - Deploys the tested digests to `dev` (self-hosted runner label `dev`) and
    then `prod` (self-hosted runner label `prod`, environment approval).
- `.github/workflows/periodic.yaml` was removed; the schedule is now in the main
  workflow so tests are not duplicated.
- `.github/actionlint.yaml` declares the custom runner labels for local linting.
- `docker-compose.yaml`: image variables, healthchecks, service-name networking,
  configurable project name and host ports.
- `.env` is no longer tracked. Use `.env.example` as the template.

## One-time GitHub UI setup

Do these steps after pushing the branches and merging them into `main`.

### 1. Environments and per-environment secrets

Repository: `QMemoryCards/system-testing` → **Settings → Environments**.

Create `dev` and `prod`. For `prod`, enable **Required reviewers** and add your
account (do not enable "Prevent self-review" if you are the only reviewer).

Add these **environment secrets** to both environments. Use different values in
`dev` and `prod`:

| Secret | Example | Notes |
| --- | --- | --- |
| `POSTGRES_DB` | `memory_cards` | Database name |
| `POSTGRES_USER` | `memory_cards` | Database user |
| `POSTGRES_PASSWORD` | long random string | Never reuse; avoid spaces, `$` and `#` (Compose `.env` syntax) |
| `CORS_ORIGIN_PATTERNS` | `http://localhost:*,http://localhost,http://127.0.0.1:*` / real origin | Comma-separated patterns |
| `GHCR_TOKEN` | PAT with `read:packages` | Optional; see package access below |

Add these **environment variables** to both environments (not secrets):

| Variable | Dev example | Prod example |
| --- | --- | --- |
| `FRONTEND_PUBLISHED_PORT` | `8081` | `80` |
| `BACKEND_PUBLISHED_PORT` | `8082` | not used |

Prod runs with `docker-compose.prod.yaml`, which removes the backend host port.
The frontend reaches backend as `backend:8080` inside the Compose network.

If dev and prod run on different hosts, dev can use `8080` for the backend; prod
does not publish it at all.

The deploy jobs write these values to a temporary `.env` on the runner with
`umask 077`, start the stack, and delete the file afterwards. No secret is
stored in a repository.

### 2. Token that triggers system tests

Create a fine-grained personal access token:

- Resource owner: `QMemoryCards`
- Repository access: only `QMemoryCards/system-testing`
- Permissions: **Contents: Read and write** (required for `repository_dispatch`)

Add it as an **Actions secret** named `SYSTEM_TESTS_TOKEN` in:

- `QMemoryCards/backend`
- `QMemoryCards/frontend`

Without this secret the dispatch step is skipped (the workflow still succeeds)
and system tests run only from the nightly schedule or manually. Add the secret
to get the push-triggered flow.

### 3. GHCR package access

The system-testing repository pulls the images published by the other two
repositories. The backend and frontend smoke tests are self-contained, so they
do not need cross-package access. For each package:

`QMemoryCards/backend` and `QMemoryCards/frontend` → **Packages** →
`backend` / `frontend` → **Package settings → Manage Actions access**

- `backend` package: **Write** for `QMemoryCards/backend`, **Read** for
  `QMemoryCards/system-testing`.
- `frontend` package: **Write** for `QMemoryCards/frontend`, **Read** for
  `QMemoryCards/system-testing`.

If the packages are public, this step is not required. If organization policy
blocks `GITHUB_TOKEN` access, create a classic PAT with `read:packages`, save it
as the `GHCR_TOKEN` environment secret in both environments, and the deploy jobs
will use it instead of `GITHUB_TOKEN`.

Bootstrap order on a fresh organization: publish both images once (for example,
merge a trivial change in each repository) before the first system-testing run.

### 4. Self-hosted runners

Repository: `QMemoryCards/system-testing` → **Settings → Actions → Runners**.

The jobs use `runs-on: [self-hosted, dev]` and
`runs-on: [self-hosted, prod]`.

Install one runner on the dev host with the custom label `dev`, and one on the
prod host with the custom label `prod`:

```bash
# Follow the token/URL shown by GitHub, then:
./config.sh --url https://github.com/QMemoryCards/system-testing \
  --token <RUNNER_TOKEN> \
  --name qmemorycards-dev \
  --labels dev
sudo ./svc.sh install
sudo ./svc.sh start
```

GitHub allows several runners on one machine, but each needs its own directory,
its own `--name`, and its own service name. Running `config.sh` twice in the
same directory does not create a second runner. If you want two runners on one
host:

```bash
mkdir -p ~/actions-runner-dev ~/actions-runner-prod
# unpack the runner into each directory, then:
(cd ~/actions-runner-dev && ./config.sh --url ... --token <TOKEN> \
  --name qmemorycards-dev --labels dev)
(cd ~/actions-runner-prod && ./config.sh --url ... --token <TOKEN> \
  --name qmemorycards-prod --labels prod)
```

The registration token is short-lived; create a fresh one in
**Settings → Actions → Runners → New self-hosted runner** if GitHub says it is
invalid.

#### One runner for both environments

The `prod` gate is the GitHub Environment approval, not the runner label. If
GitHub refuses a second runner on the same host, register one runner with both
labels:

```bash
./config.sh --url https://github.com/QMemoryCards/system-testing \
  --token <RUNNER_TOKEN> \
  --name qmemorycards-host \
  --labels dev,prod
```

If a runner is already registered with only `dev`, add `prod` in
**Settings → Actions → Runners → <runner> → Labels**. Both deploy jobs will then
match it; they run one at a time, and `prod` still waits for environment
approval.

Common registration errors:

- `A runner with the name ... already exists` — choose a unique `--name`.
- `Runner already configured. To reconfigure, use --replace` — you are in an
  existing runner directory; use a new directory for the second runner.
- `Registration token is invalid/expired` — generate a new token.
- Service install fails — the service name is derived from the runner name;
  unique runner names give unique service names.

The runner user must be able to run Docker:

```bash
sudo usermod -aG docker <runner-user>
```

The host also needs the Docker Compose plugin:

```bash
docker --version
docker compose version
```

If both environments run on the same host, use one runner with both labels (see
above) or two runner instances with different names. Set a different
`FRONTEND_PUBLISHED_PORT` for the two environments. Prod does not publish the
backend port; dev keeps `BACKEND_PUBLISHED_PORT` for the E2E-style checks. The
compose project name is already different (`qmemorycards-dev` and
`qmemorycards-prod`), so the containers do not collide.

Pull requests never run on the self-hosted runners: E2E uses `ubuntu-latest`,
and the deploy jobs only run for `repository_dispatch` or a manual run. This
keeps untrusted PR code away from the hosts.

Alternatives considered: a GitHub-hosted runner that connects to the host over
SSH (needs an exposed SSH endpoint and a private key secret), or a cloud
container runtime (not local, and outside the thesis scope). The self-hosted
runner avoids inbound SSH and is the method required by the thesis.

### 5. Branch protection

For `main` in all three repositories: **Settings → Branches → Add branch
protection rule**.

- Require a pull request before merging (1 approval).
- Require status checks to pass:
  - backend: `Static Analysis`, `Run Tests`, `Build Project`, `Docker Image`
  - frontend: `Frontend Quality`, `Docker Image`
  - system-testing: `E2E`
- Require branches to be up to date before merging.
- Require conversation resolution.
- Block force pushes and deletions.
- Do not allow bypassing the rule.

### 6. Issues and Projects

- Enable **Issues** in each repository (Settings → General → Features).
- Create an organization Project board and add issues from all three
  repositories. The thesis requires Issues/Projects; GitHub does not expose a
  stable API for board setup without a project token, so this stays a UI step.

### 7. Releases

The backend and frontend workflows run on tags matching `v*`:

```bash
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

That builds `ghcr.io/qmemorycards/<repo>:v1.0.0` and creates a GitHub Release
with generated notes. `latest` is not moved by a tag push; it moves on `main`.

## Local verification

These checks were run locally after the changes:

```bash
# Workflow syntax and expressions
actionlint backend/.github/workflows/main.yaml \
           frontend/.github/workflows/ci.yml \
           system-testing/.github/workflows/main.yaml

# Compose interpolation and schema
(cd backend && docker compose config)
(cd frontend && docker compose config)
(cd system-testing && docker compose config)
(cd backend/docker && docker compose -f docker-compose.prod.yaml config)

# Frontend gates used by CI
cd frontend
npm ci
npm run lint
npm run format:check
npm run type-check:app
npm run test:ci

# Image builds and health-checked stack
docker build -t qmemorycards/backend:local backend
docker build -t qmemorycards/frontend:local frontend
cd system-testing
BACKEND_IMAGE=qmemorycards/backend:local \
FRONTEND_IMAGE=qmemorycards/frontend:local \
docker compose --env-file .env.example up -d --wait
curl -fsS http://localhost/                     # frontend
curl -fsS http://localhost:8080/actuator/health # backend
python3 -m pytest test_e2e.py -q
docker compose --env-file .env.example down -v
```

Results on the development machine:

- `actionlint` passed on all three workflows.
- `docker compose config` passed for backend, frontend, prod and
  system-testing compose files.
- Frontend `npm ci`, lint, Prettier check, app type-check and the full Vitest
  suite (604 tests) passed.
- Both images built successfully.
- The stack reached `healthy` for db, backend and frontend.
- All 10 Playwright E2E scenarios passed against the locally built images.

The `CORS_ORIGIN_PATTERNS` in `.env.example` includes `http://localhost`
without a port. The frontend calls the backend directly during the E2E run, and
`http://localhost:*` alone does not match the default port 80 origin.

The backend health endpoint is `http://localhost:8080/actuator/health`; the
frontend is `http://localhost/`.

GitHub-side behavior (dispatch, environments, approval, self-hosted runners,
GHCR push) cannot be executed from this machine. The first run after the UI
setup is the real end-to-end check.

## Troubleshooting

- **502 Bad Gateway after a deploy.** Nginx caches the resolved IP of the
  `backend` hostname. The frontend image now uses Docker DNS with
  `resolver 127.0.0.11 valid=10s`, and the deploy job reloads nginx after
  `docker compose up`. If an old image is still running, reload it once:
  `docker compose exec -T frontend nginx -s reload`.
- **A pull request has no checks.** Open the repository's **Actions** tab and
  look for `disabled_inactivity`. GitHub disables workflows that contain a
  `schedule` trigger after 60 days without repository activity. Re-enable the
  workflow in the UI, then push a commit or close/reopen the pull request. The
  frontend workflow was renamed to `.github/workflows/ci.yml` so it gets a fresh
  workflow ID and is not tied to the old disabled `CI Pipeline` workflow.
- **`Docker Image` fails while pulling the other service.** Grant the package
  read access described above, or make the packages public.
- **`Deploy Dev`/`Deploy Prod` stays queued.** No self-hosted runner with the
  `dev`/`prod` label is online. Check **Settings → Actions → Runners**.
- **`Deploy Prod` waits forever.** The `prod` Environment has required reviewers;
  approve the deployment in the Actions run or in the Environments page.

## Operational notes

- **Same tested artifact**: deploy jobs use the digest refs produced by the
  `e2e` job. Re-running a deployment does not silently pick a newer `latest`.
- **Failed system tests**: deployment jobs do not run because they `need: e2e`.
- **Rollback**: the `e2e` job writes the tested digest refs to the run summary.
  On the affected host, put those old refs into `.env` as `BACKEND_IMAGE` and
  `FRONTEND_IMAGE`, then run `docker compose up -d --remove-orphans --wait`.
  A workflow input for digest-based rollback is the natural next improvement if
  rollbacks become frequent.
- **Secret hygiene**: `.env` files are ignored and were removed from the git
  index. If any password was ever real, rotate it in the database and in the
  environment secrets.
- **Allowed image tags**: `latest`, `sha-<40-char-commit>`, `vX.Y.Z`.
- **Action versions**: checkout/setup/cache actions are on current major versions,
  Docker login is on v3, and TruffleHog is pinned to `v3.99.3`. Review these
  pins periodically.
