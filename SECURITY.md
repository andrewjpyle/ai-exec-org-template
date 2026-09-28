# Security

This project's safety model is simple: **seats read, humans act.**

- Readers only issue GET requests or a single SQL `SELECT`. Give them read-only credentials anyway.
- Stripe: use a **restricted** key (`rk_...`) with read access to Balance. Secret keys are refused.
- GitHub: a fine-grained token with read-only Deployments and Actions access is enough. The brief
  workflow needs `issues: write` only to file the brief itself.
- Tokens come from environment variables. Never commit them to `exec_roles.py` or `metrics.json`.
- The optional Claude layer sends each armed seat's snapshot (the numbers in your brief) to the
  Anthropic API. Leave `EXEC_CLAUDE_NARRATE` off if those numbers must not leave your environment.

## Reporting a vulnerability
Please open a private security advisory on this repository (Security > Advisories > Report a
vulnerability) rather than a public issue.
