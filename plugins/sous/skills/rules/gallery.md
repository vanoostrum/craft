# Gallery rules

The gallery is the visual spec of a kitchen. It lives in the kitchen's `design/` and shows how each screen looks before anyone builds it. Sous follows it literally: `sous:build` builds screens to match it, and `sous:review` compares the app with it.

The gallery is not a sign-off document. It is a living file in the repo, next to the code. When the look changes, the gallery changes in the same PR as the code.

The kitchen's `design/README.md` holds the gallery's state in two lines, which sous reads and updates:

```markdown
Current stage: 1

Platforms: desktop, mobile
```

A kitchen without a gallery has no `design/README.md` yet. `sous:design` creates it on its first run, with `Current stage: 0` and `Platforms: not set`, and links this file from it.

## Platforms

`Platforms` lists the screens that the kitchen targets, primary platform first. `sous:design` sets it on its first run, and changes it only when chef asks or the steering argument `platforms` says so.

| Platform | What | Window |
|---|---|---|
| `desktop` | Web app in a desktop browser. | 1280×800 |
| `mobile` | Web app in a phone browser. | 390×844 |
| `ios` | Native iOS app. Follows Apple's Human Interface Guidelines. | 393×852 |
| `android` | Native Android app. Follows Material Design. | 412×915 |

`sous:design` derives the platforms from the project information: the plan or ticket, the notes under `## Steering`, `CLAUDE.md`, and the code. A web app gets `desktop, mobile`, unless the project says it is desktop-only or mobile-first. A native app gets `ios`, `android`, or both, and no web platform unless the project also has a web app. Chef confirms the platforms in the first prototype round.

## Layout

| Path | What |
|---|---|
| `design/gallery.css` | The gallery's stylesheet. It holds the visual identity: colours, fonts, spacing, and the primary action. It is separate from the app's stylesheet. |
| `design/pages/<screen>/<state>.html` | Demo pages. One static HTML file per screen state, such as `design/pages/search/empty.html`. |
| `design/components/` | From stage 2. Every component in every state that matters: hover, focus, disabled, error, light and dark. |
| `design/patterns/` | From stage 2. The rules for combining components, such as where the primary action sits and the space between items. |

## Rules for pages

- Static HTML with realistic data, not lorem ipsum. Real copy where the ticket settled it.
- Styles come only from `design/gallery.css`, linked with a relative path. No other CSS, no external fonts or scripts, so a page renders from a file without a server.
- One file per state that the app can reach. The file name is the state: `default`, `empty`, `error`, `loading`, and so on.
- A page covers every platform in `Platforms`. Web platforms share one page: it adapts to the window with media queries in `design/gallery.css`. Native platforms share one page while the iOS and Android screens are the same. Where they differ, the page splits into `<state>.ios.html` and `<state>.android.html`.
- Each page has exactly one primary action.
- Acceptance criteria cite pages by path, for example "GET /search with no results matches `design/pages/search/empty.html`".
- Take screenshots with `<rules>/scripts/gallery-shot <page> <platform> <evidence dir>`, once for each platform.

## Who changes the gallery

- `sous:design` adds and changes pages, with chef, before the spec gate.
- `sous:build` does not change the gallery, except for polish fixes asked at the merge gate. A polish fix changes the code and the gallery in the same PR.
- Feedback that changes the design, not only polishes it, goes back to `sous:design`.
- The replan check in `sous:next` marks the pages of later tickets stale when a decision changes their screen. `sous:design` redraws a stale page when its ticket is grilled.

## Rollout stages

The gallery grows in stages. At the start of each run, `sous:design` checks the trigger of the next stage. When the trigger is met, it creates a Linear ticket `Gallery stage <n>` with the work below. That ticket goes through sous and sets `Current stage` in `design/README.md`.

| Stage | Trigger | Work |
|---|---|---|
| 1. Pages | The first ticket with the `ui` label, or a plan with screens. `sous:design` does this work inside that ticket, without a stage ticket. | Set `Platforms`. Add `design/gallery.css` with the visual identity, and the first pages in `design/pages/`. Set `Current stage: 1`. |
| 2. Components, patterns, and checks | Stage 1 is done and `design/pages/` holds 5 or more screens, or one element appears on 3 or more screens. | Extract `design/components/` and `design/patterns/` from the pages. Add `tests/design/`: Playwright tests over the gallery pages and the app's HTML routes that check WCAG AA contrast, that elements are visible, and that each page has one primary action that stands out. Add Playwright with the kitchen's own package manager, and a CI step that installs Chromium. Add `tests/design/` to the engineering rules in `CLAUDE.md`, and to the verify skill. Set `Current stage: 2`. |
| 3. Coverage and sync | Stage 2 is done. | Add a test that every HTML route of the app has a gallery page. Add a recurring task that compares the gallery with the live app and opens a ticket for each difference. Set `Current stage: 3`. |

Stage 3 is the last stage. Usability in production, such as task completion rates, is out of scope until the kitchen's app has users.
