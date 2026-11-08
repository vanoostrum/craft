# Parts of a project

`craft:setup` goes through the checklist of each part the project has. Each item is a question to settle, by the agent or with the owner, as **The conversation** in `craft:setup` describes. Skip what the project already settles.

For every part, in every mode, also settle:

- how you know the part works there: a health check, a test, or a screenshot;
- which secrets and settings it needs there, and where they live;
- what an agent in a fresh cloud session must do to get it running, without the owner.

## Web frontend

- **Local:** the framework and package manager, the dev server command and port, and how it reaches the backend.
- **Cloud agent:** the setup script that installs the dependencies, and a browser for the app driver skill.
- **CI:** lint, type check, unit and route tests, the build, and end-to-end tests in a headless browser.
- **Deploy:** the host, preview deployments per PR, the domains, and caching.

## Mobile app

- **Local:** the framework (native, React Native, Flutter), the simulators or emulators, and which platforms come first.
- **Cloud agent:** what can run without a simulator: lint, type check, unit tests, and a web or headless build. Say plainly what an agent cannot do, such as running the iOS simulator, and how the app driver skill proves a change instead.
- **CI:** the build service for iOS and Android builds, and the signing credentials it needs.
- **Deploy:** internal test builds (TestFlight, Play internal testing), store accounts, release channels, and over-the-air updates.

## Backend API

- **Local:** the language and framework, the run command and port, and how it gets its settings.
- **Cloud agent:** the same run command, in the cloud session, with the backing services it needs.
- **CI:** lint, type check, and tests through the API's routes, with the backing services as CI services or test doubles.
- **Deploy:** functions or a long-running server, the host, the region, scaling, and health checks.

## Storage

Databases, file storage, caches, and search.

- **Local:** the engine and version, and how it runs: a container, an embedded file such as SQLite, or a hosted dev instance.
- **Cloud agent:** the same engine, started by the setup script or reached over the network. Check that the cloud session's network access allows it.
- **CI:** a fresh instance per run, migrations, and seed data.
- **Deploy:** the hosted service and its plan, migrations on release, backups and restore, and how staging data is kept apart from production data.

## Background jobs

Queues, scheduled jobs, and workers.

- **Local:** how jobs run during development: inline, or a worker process.
- **Cloud agent and CI:** how tests run a job and check its result without waiting for a schedule.
- **Deploy:** the queue or scheduler, retries, and how a failed job shows up.

## External services

Payments, email, auth providers, AI models, maps, and other third-party APIs.

- **Local, cloud agent, and CI:** a sandbox account or a test double, and which one each place uses. Tests do not call a live paid service.
- **Deploy:** the production account, its keys, its limits and costs, and what happens when it is down.
