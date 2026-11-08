# Owner preferences

`craft:setup` follows these preferences in its recommended answers. Where a part cannot use one, it says why in one line and recommends the next best choice. Change a preference here, in a PR to craft.

## Hosting: Vercel where it fits

The owner prefers [Vercel](https://vercel.com) for hosting, and is on the Hobby plan.

- **Where it fits:** web frontends, server-rendered web apps, and APIs that run as functions. Use Vercel's storage where a part needs it: Vercel Blob for files, and the Postgres and Redis providers on the Vercel Marketplace, so that one account and one bill cover the project.
- **Where it does not:** long-running servers and workers, persistent WebSocket servers, heavy or long jobs, and building mobile apps. Say so, and recommend a host for that part only. Keep the rest on Vercel. A mobile app can still use a backend on Vercel.
- **In `dev`:** connect the repo to Vercel early when a part runs there. Every PR then gets a preview deployment that the app driver skill can drive, which shows the deploy works long before `deploy` mode. For that, the brief settles three things, each with an item on the **Owner checklist**:
  - **Commit author.** On Hobby, Vercel can refuse to deploy a commit to a private repo when the commit author is not the account owner, which blocks agent-authored commits. Settle whether commits use the owner's Git identity, the repo is public, or the project needs Pro.
  - **Preview protection.** Vercel Authentication protects preview deployments by default, so an agent meets a login page. Settle whether protection is off for previews, or the agent gets a protection bypass secret.
  - **Network access.** The cloud environment's network access must allow the preview domains, such as `*.vercel.app`.
- **In `deploy`:** craft merges to one base branch, and Vercel deploys each push to the production branch to production. Settle in **Promotion** whether the base branch is the production branch, or production is promoted from a staging deployment by hand. Hobby has no custom environments such as "staging": staging is a preview deployment, for example of a branch with a fixed URL. A real staging environment is a reason to move to Pro, under **Later**.
- **The Hobby plan:** Hobby is for personal, non-commercial use, and cannot connect private repos owned by a GitHub organization. Its limits and features change, so read the current ones at <https://vercel.com/docs/plans/hobby> and <https://vercel.com/docs/limits> when you run, and re-check every claim in this section there. Do not rely on memory. In the brief, put the limits that the project comes near under **Constraints**, word for word with their source. Put under **Later** what would make the project move to the Pro plan: commercial use, more team members, a staging environment, or a limit it will pass. Tell the owner when a choice only works on Pro.
