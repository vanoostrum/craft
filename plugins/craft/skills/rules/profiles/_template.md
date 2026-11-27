# <stack> profile

The engineering rules for one stack, such as `python-fastapi`. This profile wins over the shared rules in `engineering.md`, and the project rules in `docs/engineering.md` win over it (`docs/adr/0011`).

This file is a template. A file in `profiles/` whose name starts with `_` is a template, and `Stacks` never names it. To write a profile, copy this file to `profiles/<stack>.md` and fill in each section.

Each rule is one bullet that starts with a bold name, such as `**Catch narrowly.**`. A rule that overrides a shared rule ends with `Replaces: engineering.md **<name>**`. A rule earns its place only as a choice between valid options, or as a habit that agents get wrong although they know better.

## Structure

Where each kind of code lives: the folders, the modules, and what each one owns.

## Naming

The names of files, types, functions, and tests, where the stack has more than one valid convention.

## Libraries

The library for each job, and the libraries not to use.

## Error handling

Which errors the code catches, where, and how it reports them.

## Metrics

The metric tools for complexity, CRAP, duplication, and file length, the command that runs each one, and its threshold.

## Sources

The sources behind the rules of this profile, by short name.
