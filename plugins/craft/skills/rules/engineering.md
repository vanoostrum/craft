# Shared rules

The engineering rules for every project. A stack profile wins over these rules, and the project rules win over both (`docs/adr/0011`). The main reader of the code is the next agent: the code must stay easy for it to understand and change.

Each rule is a habit that agents get wrong although they know better, or a choice between valid options. A finding names a rule by its bold name.

## Rules

- **Reuse before you write.** Before you add a function, type, or constant, search the repo for code that already does the job, and use or extend it. A new copy of existing logic breaks this rule. Sources: GitClear 2026; arXiv 2601.20109.
- **Clean up what you touch.** If your change makes the code you touch harder to read, such as a second copy, a longer function, or one more branch, clean it up in the same PR. Stay inside the files that the ticket touches. Sources: Beck, *Tidy First?*; arXiv 2511.04824.
- **Catch narrowly.** Catch only the errors that you expect and can handle, at the place where you can handle them. Do not swallow an error, and do not catch everything to make a failure go away. Sources: arXiv 2603.28592; GitClear 2026.
- **Keep a file to one read.** Do not grow a file past the file length threshold. Split it along a concept, not into fragments of helpers.
- **Leave no dead code.** Delete the code, parameters, imports, flags, and files that your change leaves unused. Do not keep commented-out code, or a path "for compatibility" that has no caller. Sources: arXiv 2603.28592; arXiv 2601.20109.
- **Few layers.** Do not add a wrapper, interface, or base class with one caller or one implementation. Each concept has one obvious place, with a name that you can find with grep. Source: Ousterhout.
- **Make the code pass, not the test.** Do not delete, skip, loosen, or rewrite a test to get green. Do not branch on test inputs, or return a value only because a test expects it. If a test contradicts the spec, stop and report it. Sources: arXiv 2511.21654; arXiv 2510.20270.
- **Mock only at the boundary.** Mock only what a test cannot run for real: the network, the clock, an external service, or a paid API. Do not mock your own code. Source: arXiv 2602.00409.
- **Tests show intent.** Each test checks one behavior, with a name that says the behavior. Each test asserts something, and its expected value has a name or a reason, not a bare magic number. Sources: arXiv 2506.14297; arXiv 2410.10628.
- **Finish the job.** Do not leave a placeholder, a `TODO` in place of the work, or a function that returns a fixed value to look done. Build and test the error and edge cases that the spec names, not only the main path. Source: arXiv 2511.04064.
- **No secrets in the code.** No secret, token, or personal data in code, tests, fixtures, or logs. Source: arXiv 2607.12428.
- **Add dependencies on purpose.** Use the standard library or a dependency that the project already has, when it does the job. Add a new package only after you have checked that it exists, that it is the well-known one for the job, and that it is maintained. Pin it to a version, and pin CI actions and images too. Sources: arXiv 2406.10279; arXiv 2607.12428.

## Named, not restated

The model knows these works. Use them as the vocabulary of a finding, and as a tie-breaker.

- Fowler, *Refactoring*: the smell catalogue.
- Ousterhout, *A Philosophy of Software Design*: deep modules and small interfaces.
- Google's code review guide, and Beck, *Tidy First?*: small cleanups next to a change.
- Martin, *Clean Code*: naming and single responsibility only. Its very small functions and many classes add layers, so these rules do not follow them.
