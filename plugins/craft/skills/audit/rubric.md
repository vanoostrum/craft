# Core rubric

Rubric version: 1

The blind auditor judges each PR against these five items, and only these. A change to this file gets a new rubric version, and the audit compares scores only within one rubric version (`docs/adr/0008`).

## Severity

Mark each audit finding major or minor.

- **major**: a careful reviewer would ask for a change before merge.
- **minor**: worth a comment, but the reviewer would still approve.

Do not report style that the project's linter or formatter already checks.

## Items

### Design

Look for: code in the wrong layer or module for the project's structure; a function or class that does more than one job; hidden state, or state shared where it need not be; a wrapper, option, or abstraction with one caller and no reason; types that let illegal states through; validation inside business logic instead of at the boundary.

### Complexity

Look for: deep nesting, long functions, and long condition chains that a simpler shape would remove; special cases that a better data structure would make unnecessary; control flow that a reader must trace across many places to follow; clever code where plain code works.

### Duplication

Look for: logic, constants, or knowledge copied in two or more places, in the change or between the change and existing code, where one change would have to be made twice; a new helper that repeats one the project already has.

### Naming

Look for: names that do not say what a thing is or does; names that say something false; one concept with two names, or two concepts with one name, against the project's own terms and glossary.

### Tests

Look for: changed behavior with no test; tests that check internals instead of behavior that a user or client sees; tests below the project's test seam that repeat a test at the seam; assertions so weak that the test would still pass if the behavior broke; missing edge or error cases that the change makes reachable.

## Finding format

One line per audit finding:

`<item> | <major or minor> | <file>:<line> | <one sentence>`

`<item>` is one of the five item names above, as written there.
