# CLIProxyAPI suspend patch

`suspend-aware.patch` is applied to CLIProxyAPI 7.2.149 from the pinned
`llm-agents` input. It makes authentication refresh deadlines tolerate long
system suspends and expands the relevant tests.

The package runs `go test ./sdk/cliproxy/auth` after applying the patch. Update
the pinned input and this patch together.
