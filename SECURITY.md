# Security

## Reporting a vulnerability

Report security problems privately through GitHub:
[Security → Report a vulnerability](https://github.com/jasondouglascox-coder/claude-cad/security/advisories/new).
Don't open a public issue for them.

Examples: a crafted 3MF or STEP file that runs code when cadkit reads it, a path traversal when writing `out/`, or
a dependency with a known exploit that cadkit actually uses.

Expect a first reply within a week. Fixes go to `main`; there are no release branches.

## Physical safety

A part that could fail under load (a shelf bracket, a ceiling anchor) isn't a secret. Open a normal issue with the
`safety` label so everyone printing it sees the warning.
