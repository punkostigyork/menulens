# Verification — 2026-10-02

## Automated

- **193 backend tests passed.** Coverage includes uploads, document preparation, extraction schemas/adapters, explanations, deterministic search, image caching/failure recovery, Places normalization/errors, configuration and log redaction.
- Phase 9 adds demo tests for first creation, repeated startup/CLI seeding, source PDF parity, exact deterministic searches, preserving unrelated records, conflicting files, transaction rollback and sanitized database errors.
- TypeScript checks and the standard Docker Compose production build passed.
- `python3 scripts/smoke.py` passed against the running stack: frontend pages, REST proxy, API docs, PostgreSQL-aware health, seeded demo, chicken/price filtering and downloadable PDF.
- Rerunning the seed against PostgreSQL reported no changes, confirming the existing demo survives container recreation without duplicate rows.

## Visual checks

- Demo page renders four dishes in three ordered sections, with HUF prices, ingredients, source tags and a prominent fictional/hand-authored disclosure.
- Desktop and 390px mobile screenshots are in `screenshots/`; mobile had no horizontal overflow.
- The sample PDF was rendered with Poppler and visually reviewed for clipping, text overlap and readability. Automated extraction checks names, prices, ingredients and tags against the saved records.
- Phase 8 browser checks cover location selection, missing-key errors, mocked result cards and details, category changes, empty results and list mode. The Explore screenshot shows the real unconfigured page, not fabricated live map data.

## Environment notes

Docker's image resolver initially stalled; reloading previously cached official Python/Node base images resolved it. No custom base images or workaround Dockerfiles are shipped. A host-only Next.js build hit a sandbox port-binding restriction; the final standard Docker production build completed successfully. Existing upstream PyMuPDF/Starlette deprecation warnings remain; they did not fail tests.

## Still requires live/manual validation

No paid API calls were made. Mock tests validate request/response handling, not model quality, account entitlement, billing or real service performance. Credentialed OpenAI/Anthropic/image/Google testing, real geolocation permission behavior and real Google map rendering remain unverified. Backup/restore commands are documented but have not been exercised against user data. The planned 20-document model evaluation dataset has not been built.

All nine planned implementation phases are complete at prototype scope. DeepSeek is still a separate extension. Public deployment hardening, authentication, migrations and durable jobs are explicitly outside the implemented scope.
