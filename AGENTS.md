# Repository rules

This public portfolio presents one current n8n workflow set and its companion Python implementation.

- Keep n8n the primary reader path; preserve the shared catch / optional summary / optional metrics architecture.
- Never add real credentials, environment identifiers, production exports, pinned data, private paths or raw operational logs.
- Use synthetic examples and inactive workflows. Do not connect to production services for checks.
- Preserve upstream attribution; distinguish third-party services from this project.
- Record static checks, fixture execution and live integration separately. Never upgrade historical results into current evidence.
- Run `python3 scripts/check_public.py`, `node --test checks/*.test.mjs`, and the Python test suite before publishing.
- New behavior needs a regression test. Do not modify source development projects.
