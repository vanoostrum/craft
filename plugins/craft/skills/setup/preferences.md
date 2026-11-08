# Owner preferences

`craft:setup` follows these preferences in its recommended answers. Where a part cannot use one, it says why in one line and recommends the next best choice. Change a preference here, in a PR to craft.

## Hosting: Vercel where it fits

The owner prefers [Vercel](https://vercel.com) for hosting, and is on the Hobby plan.

- **Where it fits:** web frontends, server-rendered web apps, and APIs that run as functions. Use Vercel's storage where a part needs it: Vercel Blob for files, and the Postgres and Redis providers on the Vercel Marketplace, so that one account and one bill cover the project.
- **Where it does not:** long-running servers and workers, persistent WebSocket servers, heavy or long jobs, and building mobile apps. Say so, and recommend a host for that part only. Keep the rest on Vercel. A mobile app can still use a backend on Vercel.
- **In `dev`:** connect the repo to Vercel early when a part runs there. Every PR then gets a preview deployment, which the app driver skill can drive, and which shows the deploy works long before `deploy` mode.
- **The Hobby plan:** Hobby is for personal, non-commercial use. Its limits change, so read the current ones at <https://vercel.com/docs/plans/hobby> and <https://vercel.com/docs/limits> when you run, and do not rely on memory. In the brief, put the limits that the project comes near under **Constraints**, word for word with their source. Put under **Later** what would make the project move to the Pro plan: commercial use, more team members, or a limit it will pass. Tell the owner when a choice only works on Pro.
