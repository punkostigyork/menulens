# MenuLens

MenuLens is a planned menu understanding and local restaurant discovery product. It will help diners understand unfamiliar dishes and find places to eat.

**Phases 1–8 are implemented: foundation, uploads, document preparation, AI extraction, menu browsing, dish search, lazy food illustrations, and nearby discovery.** New AI work requires the corresponding provider key/model. Search filters and cached results work without credentials. Nearby discovery requires Google Places and Maps configuration.

## Included

- Next.js App Router, React, TypeScript, and Tailwind CSS homepage and upload page.
- File picker, drag and drop, progress, retry, and saved-file confirmation.
- Validated menu upload and metadata retrieval with PostgreSQL records and persistent file storage.
- PyMuPDF text extraction and scanned-page rendering, plus validated/oriented/resized PNG and JPEG input.
- Replaceable OpenAI/Anthropic adapters, validated structured extraction, one validation retry, and transactional section/item persistence.
- Background extraction status, retry after failure, and saved-menu status links that survive refresh.
- Responsive menu pages with sections, dish cards, source descriptions, ingredients, and prices.
- Optional English/Hungarian explanations and clearly labeled inferred tags, cached per dish/language in PostgreSQL.
- Natural-language dish search, explicit filters, applied-filter summaries, and paginated results with menu links.
- On-demand, clearly labeled food illustrations with persistent caching and retryable failures.
- FastAPI backend with Pydantic settings, explicit CORS, and safe event logging.
- SQLAlchemy engine and session dependency using the psycopg PostgreSQL driver.
- Database-aware `GET /health`, interactive API docs, and focused pytest tests.
- Dockerfiles and Docker Compose with health-based startup ordering and persistent PostgreSQL storage.

```mermaid
flowchart LR
    Browser --> Frontend[Next.js :3000]
    Frontend -->|REST API proxy| Backend[FastAPI :8000]
    Backend -->|SQLAlchemy / psycopg| Postgres[(PostgreSQL)]
```

The frontend sends same-origin requests through Next.js to FastAPI. Upload business logic lives in `menu_service.py`, outside API routes. No private keys are exposed to the frontend. AI providers are called only when the user starts menu understanding, requests a dish explanation or illustration, or submits a natural-language search. Filter-based search and result pagination do not call AI.

The `menus`, `menu_sections`, `menu_items`, `menu_extractions`, `item_explanations`, and `generated_images` tables are created on startup using SQLAlchemy `create_all` (non-destructive for existing tables). Phases 4, 5, and 7 only add new tables, without altering the existing menu columns. This initial schema has no migration framework; `create_all` does not alter existing columns. Add migrations before subsequent schema changes. `restaurant_id` is nullable and has no foreign key until restaurant persistence is introduced.

## Run with Docker

Prerequisite: Docker Engine / Docker Desktop running, with Docker Compose v2. Ports 3000 and 8000 must be available.

From this directory:

```sh
cp .env.example .env
docker compose up --build
```

The copy is optional for the default local setup: Compose includes development defaults. The checked-in database password is only a local development default, not a production secret. If changing PostgreSQL credentials, update `DATABASE_URL` to match. Inside Compose, the database hostname is `postgres`.

- Frontend: http://localhost:3000
- Upload: http://localhost:3000/upload
- Health: http://localhost:8000/health
- API documentation: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json

`/` on the backend is not an API route. Use `/health` or `/docs`.

Successful health response:

```json
{"status":"ok","database":"connected"}
```

Health executes `SELECT 1` against PostgreSQL. An unavailable database produces HTTP 503 with `{"status":"unavailable","database":"disconnected"}` and does not expose database details.

```sh
docker compose ps
docker compose exec postgres psql -U menulens -d menulens -c 'SELECT 1;'
docker compose logs backend
docker compose down
```

`docker compose down` preserves metadata in `postgres_data` and uploaded files in `uploads_data` (mounted at `/app/uploads`). `docker compose down -v` permanently deletes that data. PostgreSQL is not exposed to the host; only the frontend and backend are bound to localhost. These are production-build containers; rebuild after source changes.

## Local development and tests

Frontend requires Node.js 22+ and npm:

```sh
cd frontend
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
# In another terminal:
npm run typecheck
BACKEND_URL=http://localhost:8000 npm run build
```

Backend requires Python 3.12+:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use an isolated in-memory SQLite database and temporary file storage; they do not require PostgreSQL. Docker integration verification separately exercises real PostgreSQL. For a host-run API, provide a reachable PostgreSQL URL and start:

```sh
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/menulens'
uvicorn app.main:app --reload --port 8000
```

The Compose database is intentionally private to its network. Use your own host-accessible development database, or keep the backend in Compose. `.env` is automatically read by Compose at repository root; a host-run backend reads `.env` from its current working directory or uses exported variables.

## Environment

| Variable | Purpose |
| --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Local database initialization |
| `DATABASE_URL` | Backend SQLAlchemy URL, using `postgresql+psycopg://` |
| `MAX_UPLOAD_BYTES` | Maximum file size; default 10485760 (10 MiB), up to 100 MiB. Rebuild Compose after changing it to align the frontend proxy. |
| `UPLOAD_DIR` | Host-run backend upload directory; Compose fixes this to `/app/uploads`. |
| `BACKEND_URL` | Frontend development/build environment only; default `http://backend:8000` for Docker. |
| `CORS_ORIGINS` | JSON array of permitted browser origins; defaults to localhost:3000 |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Backend-only provider keys; configure the selected provider |
| `MENU_AI_PROVIDER`, `MENU_AI_MODEL` | Select `openai` or `anthropic` and a compatible vision/structured-output model |
| `MENU_AI_TIMEOUT_SECONDS` | Total deadline per provider attempt; default 60 seconds |
| `MENU_AI_MAX_OUTPUT_TOKENS` | Response token budget; default 12000 |
| `IMAGE_PROVIDER`, `IMAGE_MODEL` | Image provider (`openai`) and a compatible GPT Image model; independent of the menu provider |
| `IMAGE_TIMEOUT_SECONDS` | Image generation deadline; default 180 seconds, maximum 300 |
| `IMAGE_MAX_BYTES` | Decoded/stored image limit; default 10 MiB, maximum 20 MiB |
| `PLACES_API_KEY` | Private backend Google Places API (New) key |
| `MAPS_API_KEY` | Public browser Maps JavaScript key, restricted by website referrer |
| `MAPS_MAP_ID` | Google map ID; defaults to `DEMO_MAP_ID` for development |
| `PLACES_TIMEOUT_SECONDS` | Places request deadline; default 15 seconds |

Never commit `.env` files or credentials. Database, CORS, upload, processing limits, and AI settings are passed to the backend. There are no frontend private environment variables. CORS allows GET and POST from explicit configured origins.

## Important files

```text
frontend/src/app/page.tsx       Homepage with active upload link
frontend/src/app/upload/page.tsx Upload page
frontend/src/components/MenuUpload.tsx File selection, validation, progress, results
frontend/src/services/api.ts    Same-origin API client
frontend/next.config.ts         Backend proxy and multipart size allowance
backend/app/api/menus.py        Upload, configuration, and metadata endpoints
backend/app/services/menu_service.py File validation, persistence, preparation orchestration
backend/app/services/document_service.py Text extraction and normalized image preparation
backend/app/schemas/document.py Provider-neutral ordered document input
backend/tests/test_documents.py Real generated PDF/image fixtures and API tests
backend/app/models/menu.py      Initial Menu schema
backend/app/schemas/menu.py     Typed metadata responses
backend/app/core/upload_limit.py Bounded multipart requests
backend/app/services/ai/base.py Replaceable provider interface
backend/app/services/ai/openai_provider.py OpenAI Responses API adapter
backend/app/services/ai/anthropic_provider.py Anthropic Messages API adapter
backend/app/services/ai/menu_extractor.py Prompt, validation, retry, usage
backend/app/services/extraction_service.py Job lifecycle and transactional persistence
backend/app/schemas/extraction.py Validated AI menu output
backend/app/models/menu_section.py Section persistence
backend/app/models/menu_item.py Dish persistence
backend/app/models/menu_extraction.py Provenance and extraction errors
frontend/src/components/MenuProcessing.tsx Processing status and explicit retry
backend/tests/test_extraction.py Extraction/provider/lifecycle regression tests
backend/tests/test_menus.py     Upload and persistence regression coverage
frontend/src/app/globals.css    Tailwind entry and base styling
frontend/Dockerfile             Multi-stage standalone Next.js image
frontend/package-lock.json      Locked frontend dependencies
backend/app/main.py             App lifecycle and CORS
backend/app/api/health.py       Health endpoint and safe failure response
backend/app/core/config.py      Typed environment configuration
backend/app/core/logging.py     Logging configuration
backend/app/database/connection.py  Engine and connectivity check
backend/app/database/session.py Request-scoped SQLAlchemy session dependency
backend/tests/test_health.py    Health, failure, docs, and CORS tests
backend/Dockerfile              Non-root Python API image
docker-compose.yml             Three services and persistence
.env.example                   Local configuration template
```

## Scope and next phases

Phase 8 implementation is complete, with live provider verification pending credentials. Phase 9 adds final polish. Provider comparison and an evaluation dataset remain future work. No authentication, migrations, production deployment hardening, OCR, are included. Uploads begin at `uploaded`; preparation alone does not change status. Explicit extraction transitions through `processing` to `processed` or `failed`.

Framework setup follows the official [Next.js installation guide](https://nextjs.org/docs/app/getting-started/installation) and [FastAPI Docker guide](https://fastapi.tiangolo.com/deployment/docker/).

## Phase 1 verification (historical)

Verified on 2026-09-29:

- Docker Compose built and started all three services; all reported healthy.
- Next.js production build completed with TypeScript checking.
- Homepage returned HTTP 200 and was visually inspected in a browser; upload CTA is disabled and labeled as coming soon.
- `/health` returned HTTP 200 with `status=ok` and `database=connected`.
- A separate SQLAlchemy `SELECT 1` from the backend container succeeded.
- `/docs` and `/openapi.json` returned HTTP 200.
- Backend pytest suite: 3 passed (one upstream Starlette/httpx deprecation warning).

The sandbox required a workspace-local Docker Buildx cache and npm cache during verification. These are environment-specific adjustments, not prerequisites for the normal Docker command above. No Phase 2 features were implemented.


## Upload API and behavior

- `POST /api/menus`: multipart form field `file`; returns HTTP 201 with persisted metadata.
- `GET /api/menus/{menu_id}`: returns metadata; 404 for an unknown UUID.
- `GET /api/menus/upload-config`: supplies the upload limit to the UI.

```sh
curl -F 'file=@/absolute/path/to/menu.pdf' http://localhost:8000/api/menus
curl http://localhost:8000/api/menus/MENU_UUID
```

PDF, JPG/JPEG, and PNG are supported. Validation checks extension (case-insensitive), declared MIME type when supplied, file signature, nonempty content, filename metadata length, and the byte limit. Missing/generic MIME types are accepted only when the signature matches the extension. Upload signatures are preliminary format checks. The Phase 3 preparation endpoint additionally decodes the document and rejects unreadable inputs.

Original basenames are retained for display; path components are stripped. Stored filenames use random UUIDs, and exclusive creation prevents overwrites. Files are not publicly served. Invalid requests leave no rows or stored files. Storage/database failures roll back the transaction and remove the newly written file. A process crash between file creation and commit can leave an orphan file; there is no orphan reconciliation job in this phase.

The backend bounds multipart request bodies to the configured file limit plus 1 MiB of multipart overhead, even without Content-Length. The service separately enforces the exact file limit. The Next.js proxy uses the same total request allowance. Logs record upload IDs, not contents or connection secrets.

Use the upload page to save a file and see confirmation. The app has no menu library or full result page yet; records and structured items can be retrieved using the API. This remains a local prototype without authentication or a delete API. Do not expose it publicly.

## Phase 2 verification

Verified on 2026-09-29:

- 21 pytest tests passed: health, CORS, supported formats, invalid extension/MIME/signature, empty/oversized files, exact size boundary, safe unique storage, metadata retrieval, missing records, database/disk failure cleanup, and request-size enforcement without Content-Length.
- Next.js production build and TypeScript checks passed.
- Browser file picker → PDF upload → “Menu saved” completed successfully; unsupported extension displayed an error.
- Actual PDF and PNG uploads through the frontend proxy returned HTTP 201 and persisted in PostgreSQL.
- A 10 MiB file succeeded through the proxy; an over-limit file returned 413, and a spoofed PDF returned 415.
- Restarted PostgreSQL and the backend, retrieved the same records, and matched SHA-256 checksums of the stored files.
- All three Docker services reported healthy after restart.

A Next.js default 10 MiB proxy buffer initially truncated a boundary-sized multipart upload. The proxy allowance now matches the configured file size plus 1 MiB overhead. See the official [Next.js proxy body-size documentation](https://nextjs.org/docs/pages/api-reference/config/next-config-js/proxyClientMaxBodySize). Multipart uploads follow the [FastAPI file upload API](https://fastapi.tiangolo.com/tutorial/request-files/).


## Phase 3: prepare an uploaded document

Upload a menu, then call:

```sh
curl -X POST http://localhost:8000/api/menus/MENU_UUID/prepare
```

This endpoint is also available through the frontend proxy at port 3000 and in `/docs`. It synchronously returns a validated `PreparedDocument`:

- `page_count`: number of original pages.
- `mode`: `text`, `images`, or `mixed`.
- `pages`: ordered text/image inputs with original, one-based page numbers.
- `skipped_blank_pages`: page numbers of completely uniform rendered pages.

Text pages contain `kind: "text"` and `text`. Image pages contain `kind: "image"`, `media_type: "image/png"`, `data_base64`, `width`, `height`, and any supplemental `extracted_text`. Provider adapters in Phase 4 can consume this same schema regardless of the original file format. Image data is returned only by this explicitly requested API, not exposed on normal product pages or logged.

Digital PDF pages with useful text use direct extraction with layout sorting and whitespace cleanup. Pages with sparse/garbled text are rendered to RGB PNG, up to 150 DPI and a 1600-pixel longest edge. A large embedded image (at least 25% of page area) also triggers visual input, preserving supplemental text so an embedded scan is not lost under a digital header. Mixed documents retain both kinds of input. Completely uniform pages are skipped; an entirely blank document is rejected.

PNG/JPEG uploads are decoded with Pillow, checked for format consistency and animation, oriented using EXIF, resized without upscaling, flattened onto white, and re-encoded as RGB PNG without original metadata. Sources are never modified. Corrupt/unreadable documents and password-protected PDFs receive friendly 422 errors; processing-limit violations receive 413, missing stored files 503, and unknown menu IDs 404.

Preparation is on demand and has no database side effects: `status` remains `uploaded` and `processed_at` remains null on success or failure. These fields are reserved for the complete menu extraction workflow. Prepared output is returned to the caller and is not yet cached/persisted. There is no preparation UI in this phase; the existing upload experience remains unchanged. This preparation endpoint itself does not parse dishes, prices, ingredients, or descriptions; the extraction endpoint below consumes its output.

### Preparation limits

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCUMENT_MAX_PAGES` | 20 | Maximum PDF pages |
| `DOCUMENT_IMAGE_EDGE` | 1600 | Maximum normalized image edge in pixels |
| `DOCUMENT_MAX_IMAGE_PIXELS` | 40000000 | Maximum source image pixel count before decoding |
| `DOCUMENT_MAX_TEXT_CHARS` | 200000 | Maximum extracted PDF text length |
| `DOCUMENT_MAX_OUTPUT_BYTES` | 16777216 | Maximum total base64 image characters (ASCII bytes) |

These variables are included in `.env.example` and forwarded to the backend by Compose. PyMuPDF calls are serialized with a process-local lock because its native API does not support concurrent threads. This simple synchronous implementation has no worker queue or hard processing deadline; limits bound ordinary workloads, but this is not a sandbox for hostile documents.

Text usefulness and blankness are deterministic heuristics, not semantic menu detection. Poor OCR layers, complex columns, rotated layouts, or scans split into many small embedded images may need improved heuristics during later evaluation. The preparation endpoint does not claim a file actually contains a menu. Some damaged PDFs may be recoverable by PyMuPDF; unreadable ones fail cleanly.

Implementation uses the official [PyMuPDF page API](https://pymupdf.readthedocs.io/en/latest/page.html) and [rendering recipes](https://pymupdf.readthedocs.io/en/latest/recipes-images.html).

## Phase 3 verification

Verified on 2026-09-29:

- 42 backend tests passed, including the earlier upload/health regression tests.
- Generated real digital, scanned, mixed, sparse, blank, and encrypted PDF fixtures; checked PNG/JPEG decoding, EXIF rotation, image dimensions, animation/type rejection, output limits, missing files, and path confinement.
- Through the running Next.js proxy and PostgreSQL-backed API, uploaded and prepared digital/scanned/mixed PDFs and a JPEG. The returned modes were respectively `text`, `images`, `mixed`, and `images`.
- Corrupted, blank, and password-protected PDFs returned HTTP 422 with readable errors.
- Verified menu records remain `uploaded`, health remains connected, the preparation endpoint appears in OpenAPI, and `/upload` still responds successfully.
- Rebuilt the Docker application; all three services reported healthy.

The test run emits upstream PyMuPDF SWIG and Starlette/httpx deprecation warnings; no tests fail. No AI integration or Phase 4 work is included.


## Phase 4: AI menu extraction

### Configure a provider

No key or model is supplied by default. Create the ignored root `.env` from `.env.example`, then configure one provider:

```dotenv
MENU_AI_PROVIDER=openai
MENU_AI_MODEL=YOUR_COMPATIBLE_MODEL_ID
OPENAI_API_KEY=YOUR_PRIVATE_KEY
```

Or use `MENU_AI_PROVIDER=anthropic` and set `ANTHROPIC_API_KEY` plus a compatible model ID. Choose a model supporting images and native structured JSON output in your provider account. There is no automatic fallback to another provider, no fake provider mode in the running application, and no silent model substitution. Never put API keys in chat, frontend variables, or committed files.

After editing `.env`, apply it with `docker compose up -d` (or `docker compose up --build -d` after code changes). A plain restart does not refresh container environment. Keys are runtime backend environment variables, never frontend build arguments. Existing uploads and the health endpoint work without keys; extraction returns a friendly 503 without changing the menu status when configuration is missing.

On `/upload`, save a menu, then select **Understand this menu**. The menu is sent to your chosen AI service and that provider's usage charges apply. The page shows “Understanding your menu…” and then “Your menu is ready.” with section/item counts. The saved menu ID is retained in the page URL, so refreshing resumes status checks. A failed extraction can be retried explicitly. Select **View your menu** to browse the saved dishes and request explanations.

### Endpoints

- `POST /api/menus/{menu_id}/process`: starts extraction and returns HTTP 202 with current menu status.
- `GET /api/menus/{menu_id}`: metadata plus ordered sections/items, source restaurant name, and a safe processing error if present.
- `GET /api/menus/{menu_id}/items`: ordered flat list of persisted items.

The frontend polls metadata until processing finishes. Repeated start requests while processing or after success do not start another model call or duplicate records. New extraction attempts are allowed for `uploaded` or `failed` menus. The response to an accepted start may be `processing` even when an in-process test client waits for the job to finish before returning.

```sh
curl -X POST http://localhost:8000/api/menus/MENU_UUID/process
curl http://localhost:8000/api/menus/MENU_UUID
curl http://localhost:8000/api/menus/MENU_UUID/items
```

### Architecture and validation

```mermaid
flowchart LR
    Start[Explicit process request] --> Claim[Atomic database status claim]
    Claim --> Prepare[Document service]
    Prepare --> Extractor[Menu extractor]
    Extractor --> Provider[AIProvider interface]
    Provider --> OpenAI[OpenAI Responses API]
    Provider --> Anthropic[Anthropic Messages API]
    Provider --> Validate[Pydantic validation]
    Validate -->|Invalid once| Extractor
    Validate -->|Valid| Save[One transaction: sections, items, metadata]
    Validate -->|Invalid twice| Fail[Failed status and safe error]
```

Provider-specific request construction and response parsing live under `services/ai`. They use the providers' HTTP APIs through an injected/testable HTTPX transport. `AIProvider.extract_menu` returns untrusted JSON plus token usage; only the shared extractor validates it. Adding a future Gemini adapter requires implementing this interface and registering it in the factory, without changing routes or persistence. The interface also supports dish explanations and search intent interpretation.

The provider receives a compatible subset of the JSON schema; local Pydantic validation enforces the full constraints. Invalid JSON, wrong field types, blank names, negative/nonfinite/overprecision prices, malformed currency codes, unexpected fields, and oversized collections fail validation. Invalid output is retried exactly once using the original source and a correction instruction. Both invalid attempts lead to `failed`, a logged internal event, and a safe user-facing message. Provider refusal, incomplete output, transport errors, and timeouts fail without automatic transport retries. The per-attempt deadline covers the entire HTTP operation, rather than only a read timeout.

The prompt preserves source-language names, source descriptions, exact prices, order, and explicitly listed ingredients. It treats source documents as untrusted data and prohibits invented items and inferred allergy claims. Local validation guarantees schema/data constraints, not factual accuracy; hallucination and extraction accuracy still require evaluation with real menus.

Section and item IDs, ordering, foreign keys, numeric storage, currency fallback, and database writes are deterministic. Prices use PostgreSQL `NUMERIC(12,2)` and serialize as decimal strings. Ingredients, tags, and dietary information use JSONB in PostgreSQL (JSON in SQLite tests). Generated descriptions/cuisine remain null; tags and dietary information remain empty, keeping unimplemented inferences separate from extracted source information. Restaurant names are preserved in extraction metadata, not used to create restaurant/place records yet.

`menu_extractions` stores the chosen provider/model, prompt version, latest attempt count, accumulated provider-reported token usage, extraction latency, restaurant name, and a safe failure message. This supports later provider comparison without implementing an evaluation dataset now. It keeps the latest run, not an audit history; monetary costs are not estimated. Timeout usage may be unavailable. Source contents, full responses, and keys are never logged.

### Persistence and job limitations

All sections/items and final menu metadata are committed in one transaction. Failure rolls that transaction back, leaves no partial dishes, and sets `failed` in a separate transaction. If the database is unavailable even for the failure update, the status can remain `processing` until restart recovery.

This MVP uses FastAPI in-process background tasks and **one backend worker/replica**. Startup marks interrupted `processing` records as failed so the user can retry. Do not add workers/replicas with this recovery policy; a shared durable job queue and ownership/lease mechanism would be needed first. There is no automatic retry of a job lost during a process crash. These choices keep Phase 4 infrastructure small while making interruption visible.

Provider format references: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

## Phase 4 verification

Verified on 2026-09-29:

- 76 pytest tests passed, including all Phase 1–3 tests and new provider contracts, strict extraction validation, one-retry behavior, timeout handling, safe errors, job idempotency, restart recovery, and full rollback on failed persistence.
- Both real HTTP adapters were exercised with HTTPX mocked transports inside the backend container against the actual PostgreSQL database. A first invalid response was retried once; the valid second response persisted one section/item, source ingredients, exact price, source restaurant name, and accumulated usage. Repeated process requests did not duplicate data or calls.
- Two clearly named `phase4-openai-test.pdf` / `phase4-anthropic-test.pdf` integration records remain in the local database, with `mock-integration-model` provenance. They are test fixtures, not live model results.
- Frontend production build and TypeScript validation passed. The browser displayed a processed fixture after loading its saved-menu URL, completed a fresh upload, and showed the friendly missing-configuration message when extraction was requested.
- Existing data survived container recreation. The backend configuration was checked by presence only: neither provider key, provider selection, nor model is configured. No paid external AI requests were made.

**Live-provider verification remains pending:** set the selected key/model in `.env`, recreate the backend, and process a real menu to assess actual model accuracy. Mocked tests validate integration and persistence, not model quality or account access. This historical verification predates Phase 5.


## Phase 5: Menu browsing and explanations

Open `/menu/{menu_id}` from **View your menu** after upload. The page shows the restaurant or filename title, ordered sections, dish cards, exact saved prices/currencies, source descriptions, and listed ingredients. Section navigation, responsive cards, loading skeletons, empty states, missing-menu handling, and retryable connection errors are included. An unfinished menu retains the existing processing controls.

Choose English or Magyar for explanations. **Explain this dish** requests an optional, concise explanation and up to five suggested tags. Original names and menu text stay in their source language. The language control changes explanations and price formatting, not the entire interface. Explanations and tags are visibly labeled as AI-generated information, separate from source ingredients and descriptions. Food illustrations are available separately through the Phase 7 controls below.

### Explanation API and persistence

- `POST /api/menu-items/{item_id}/explanation`, body `{"language":"en"}` or `{"language":"hu"}`: returns HTTP 202; starts work only if no ready/active result exists.
- `GET /api/menu-items/{item_id}/explanation?language=en`: reads the cached status/result.
- `GET /api/menus/{menu_id}` includes cached explanations on each item.

The new `item_explanations` table has a composite item/language key, status, description, inferred tags, provider/model/prompt provenance, timestamp, and safe failure message. English and Hungarian are cached independently. Repeated requests reuse results; ready results are readable without provider credentials. Failed requests are retried explicitly. Existing menu items and their source fields are never overwritten by explanation generation. Legacy `generated_description`, `tags`, and `dietary_info` item columns remain untouched.

The shared `AIProvider.generate_description` interface uses the same replaceable OpenAI/Anthropic adapters and configured provider/model as extraction. Pydantic validates language, length, sentence count, allowed tags, and common English/Hungarian allergy-safety claims. Invalid output is retried once. The prompt forbids invented ingredients and allergy assurances. These checks do not guarantee factual accuracy or catch every possible unsafe paraphrase; real-model evaluation remains necessary. Users are directed to ask the restaurant about allergens.

Generation runs lazily in the existing single-worker background-task setup. Failures affect only the explanation, not the processed menu. Startup marks interrupted explanations as failed for explicit retry. Caching has no automatic model/prompt-version invalidation in this phase.

### Key Phase 5 files

- `frontend/src/app/menu/[id]/page.tsx`: result route.
- `frontend/src/components/MenuView.tsx`: menu states and language choice.
- `frontend/src/components/MenuSection.tsx`, `DishCard.tsx`, `MenuSkeleton.tsx`: consumer-facing presentation.
- `backend/app/api/menu_items.py`: thin explanation endpoints.
- `backend/app/services/explanation_service.py`: caching, jobs, persistence, recovery.
- `backend/app/services/ai/dish_explainer.py`: prompt, validation, retry.
- `backend/app/schemas/explanation.py`, `models/item_explanation.py`: contracts and persistence.
- `backend/tests/test_explanations.py`: provider, schema, cache, language, and failure tests.

### Phase 5 verification (2026-09-30)

- 95 pytest tests passed, including bilingual caching, restricted tags, validation retries, provider contracts, job deduplication, interrupted-job recovery, and persistence failures.
- Next.js production compilation and TypeScript checks passed on the host and in Linux containers.
- The actual PostgreSQL-backed API persisted four Hungarian sample dishes and eight EN/HU explanations. Nine mocked provider calls covered extraction plus explanations; repeated requests made no additional calls.
- Browser checks covered desktop and 390-pixel mobile layouts, language switching, source/inferred labels, section navigation, upload-to-menu navigation, empty results, missing menus, and missing provider configuration. The mobile page had no horizontal overflow.
- Containers were recreated with stored data retained; `/health` returned `{"status":"ok","database":"connected"}`.
- Docker Desktop initially failed to reach its registry. Official base images were loaded through the host connection and local dependencies were used for an intermediate verification build. The standard Compose build subsequently completed successfully; project Dockerfiles remain unchanged.

The local sample is available at `/menu/a3e0799c-7973-4174-8042-99b886108fda` in this workspace's database. It is a QA fixture named **Magyar asztal · sample menu**, with `phase5-mocked-fixture` provenance, not a real restaurant or live model result. An empty-menu QA record is also present. A fresh database does not seed these automatically.

No live provider credentials were configured and no paid AI requests were made. Live accuracy and provider account compatibility remain unverified. This historical verification predates Phase 6.


## Phase 6: Dish search

Open [Find a dish](http://localhost:3000/search), also linked from the homepage and menu pages. **Describe a craving** interprets requests such as `I want spicy chicken under 5000 HUF.` through the configured provider. **Choose filters** supports dish name, one listed ingredient, tag, and maximum price with HUF/EUR/USD. The API supports multiple ingredients/tags, minimum prices, explicit boundary inclusivity, any three-letter currency code, and optional exact menu scope.

Filter search works without API credentials. **Browse all saved dishes** is available before searching and after an empty result. The UI shows applied filters, result count, source menu/section links, loading and error states, and pagination. A result matched through a saved AI tag explicitly says so. Results reuse Phase 5 dish cards and may offer optional explanations, but searching does not generate descriptions or tags.

### Search API

`POST /api/search` accepts exactly one of `query` or `filters`:

```json
{"query":"I want spicy chicken under 5000 HUF.","limit":20,"offset":0}
```

Equivalent deterministic request (no AI call):

```json
{
  "filters": {
    "ingredients": ["chicken"],
    "tags": ["spicy"],
    "max_price": "5000",
    "max_price_inclusive": false,
    "currency": "HUF"
  },
  "limit": 20,
  "offset": 0
}
```

An empty `filters` object browses all processed dishes. `menu_id`, when supplied separately, is a validated UUID applied exactly by SQL; the model never receives or chooses menu/item IDs. `limit` is 1–50, default 20. Responses contain the validated `intent`, `results`, exact `total`, `offset`, `limit`, `has_more`, and optional `clarification`. Prices serialize as decimal strings. Send the returned intent back as `filters` to paginate without repeating the AI call. Results are ordered by newest menu, then stored section/item order and stable ID tie-breakers; there is no AI ranking.

```mermaid
flowchart LR
    Query[Natural-language request] --> Interpreter[AIProvider.interpret_search]
    Interpreter --> Validation[Pydantic validation and one retry]
    Filters[Explicit filters or pagination] --> Validation
    Validation --> SQL[SQL: status, menu ID, currency, price]
    SQL --> Matching[Deterministic ingredient, name, tag matching]
    Matching --> Results[Paginated saved dishes and applied filters]
```

### Matching rules and boundaries

- Every requested ingredient and tag must match (AND semantics). Dish names use case/accent-insensitive substring matching. Ingredient matching uses whole words/phrases in **listed ingredients only**, with a small documented English/Hungarian alias vocabulary in `search_matching.py`. It is not general translation, stemming, fuzzy search, or embedding similarity.
- Tag matching is exact after case/accent normalization, against saved item tags and tags from `ready` explanations in either language. Failed/processing explanation tags and incidental description wording do not count. No tags are generated during search; untagged dishes may therefore be absent from tag-filtered results.
- Price bounds use PostgreSQL `NUMERIC`/Python `Decimal`. `under` means strictly less than; `up to` means inclusive. Manual maximum-price filters are inclusive. Currency matching is exact with no exchange-rate conversion. A budget without currency returns a clarification, and missing-price items are excluded from price-bounded searches.
- Unsupported constraints (allergy/dietary safety, exclusions, location/restaurant filters, nutrition, or OR groups) return clarification with no partial results. Detection in natural-language requests depends on the model; schema validation does not guarantee semantic interpretation accuracy. Applied filters make the interpretation reviewable. Allergy safety is never inferred from ingredient absence.
- Query length is 1–500 characters. Unknown fields, invalid amounts/ranges, invalid tags, and model-supplied SQL/IDs are rejected. Both adapters send only the query and interpretation instructions/schema; they never receive the candidate records. An invalid model response is retried once, then returns a friendly 422. Provider failures/timeouts and database failures return clean errors. Search queries, raw model outputs, and secrets are not logged.
- SQL first filters price/currency/menu/status. The service streams candidates in batches of 200 and applies deterministic normalized ingredient/name/tag matching in Python, retaining only the requested page while counting all matches. There is no silent candidate cutoff. This is suitable for the local MVP; large catalogs need indexed normalized search fields and database-side matching before scaling. Concurrent catalog changes can shift offset pagination; it is not a saved search snapshot.

No new tables or migrations are needed. Search uses the existing `MENU_AI_PROVIDER`, `MENU_AI_MODEL`, keys, and per-attempt timeout. Search output is capped at 2000 tokens per attempt. No search history, query cache, vector database, or background queue was added. Prompt version, provider, attempts, token usage, and latency events support later evaluation; no monetary cost estimate or evaluation dataset is implemented.

### Key Phase 6 files

- `backend/app/api/search.py`: thin REST endpoint.
- `backend/app/schemas/search.py`: request, intent, result schemas and provider-compatible JSON schema.
- `backend/app/services/ai/search_interpreter.py`: provider-neutral prompt, deadline, and validation retry.
- `backend/app/services/search_service.py`: deterministic filtering, pagination, and safe errors.
- `backend/app/services/search_matching.py`: normalization, ingredient aliases, and exact tag matching.
- `backend/tests/test_search.py`: schemas, provider contracts, filter correctness, pagination, and failures.
- `frontend/src/app/search/page.tsx`, `components/DishSearch.tsx`, `components/SearchBar.tsx`: search experience.
- `frontend/src/types/search.ts`, `services/api.ts`: typed API contracts/client.

The OpenAI adapter continues using the existing Responses API structured-output contract documented in the [official OpenAI guide](https://developers.openai.com/api/docs/guides/structured-outputs); the shared service still validates every response locally.

### Phase 6 verification (2026-09-30)

- 135 pytest tests passed, including 40 search tests and all earlier regressions (upstream SWIG/Starlette warnings only).
- Standard Docker Compose production build and TypeScript validation passed; frontend, backend, and PostgreSQL report healthy. The initial host build was blocked by a sandbox port-binding restriction; the container build completed after Docker access was granted.
- Both actual provider adapters were exercised with mocked HTTP transports against PostgreSQL. `spicy chicken under 5000 HUF` returned the 4590 HUF fixture and excluded the 5000 HUF boundary fixture. Exact menu scope, missing-currency clarification, pagination, and read-only search behavior passed.
- Browser checks covered the missing-provider error and filter fallback, correct matching dish, no-results state, link to the selected dish, and a 390-pixel mobile form without horizontal overflow.
- Local QA menu `cc43f8d0-8c24-410a-b245-19197302d2ac` is named `phase6-search-fixture.pdf`. It contains two constructed dishes with mocked explanation provenance `phase6-mocked-fixture`; there is no uploaded source PDF for this QA record. It is not a real restaurant or a live model result and is not automatically seeded in a fresh database.

Live provider credentials are still absent. Natural-language interpretation accuracy/account access remain unverified; no paid requests were made. Try the working filter UI with ingredient **chicken**, tag **spicy**, and maximum **4999 HUF** to see the matching fixture. This historical verification predates Phase 7.


## Phase 7: Food illustrations

Dish cards on menu and search pages now offer **Create food illustration**. Generation is explicit and lazy: viewing a menu, searching, or switching explanation language does not start it. A successful image is reused across views and requests, with lazy browser loading. Every image has the visible label **AI-generated illustration** and the explanation **Representative only. Not a photo from the restaurant.** Loading, provider failures, interrupted jobs, unavailable cached files, and retry states are handled per dish.

### Configure and run

Set these variables in the ignored root `.env`:

```dotenv
IMAGE_PROVIDER=openai
IMAGE_MODEL=YOUR_COMPATIBLE_GPT_IMAGE_MODEL_ID
OPENAI_API_KEY=YOUR_PRIVATE_KEY
```

Then run `docker compose up --build -d`. The image provider uses `OPENAI_API_KEY` independently of `MENU_AI_PROVIDER`, so menu extraction can still use Anthropic. No model is chosen silently. The initial adapter uses the [OpenAI Images API](https://developers.openai.com/api/docs/guides/image-generation), requesting one 1024×1024 PNG at low quality. Select a model supporting those options in your account. No legacy image-model URL flow is implemented. Private keys remain backend-only.

Clicking the illustration button sends dish name, listed ingredients, original source description, and cuisine (if available). The prompt requests a representative food illustration without extra toppings, branding, or allergy claims. It treats dish contents as untrusted data. Generated explanations are deliberately not included, to avoid compounding earlier inferences. Image fidelity and factual ingredient depiction cannot be guaranteed by code.

### API and cache

- `POST /api/menu-items/{item_id}/image`: HTTP 202; returns the existing ready/processing record or claims one new job. A failed record can be retried explicitly.
- `GET /api/menu-items/{item_id}/image`: status/metadata, or 404 if no illustration was requested.
- `GET /api/menu-items/{item_id}/image/content`: validated PNG bytes for a ready image, with a one-hour private browser cache and `nosniff`.
- Menu/item/search responses include nullable `generated_image` metadata, so opening cards needs no extra per-item status calls. Polling happens only while an image is processing.

The new `generated_images` table records ID, unique menu-item ID, provider, model, prompt/version, status, UUID storage filename, creation time, latency, and a safe failure message. The unique item constraint and atomic retry claim prevent concurrent requests from scheduling duplicate jobs. Ready caches can be read without credentials. There is one current image per item; changing model/prompt settings does not invalidate it. No automatic regeneration or paid retry occurs.

Files live in `uploads/generated-images/` (inside the existing `uploads_data` Docker volume). Responses contain only a same-origin content URL, never a filesystem path or expiring provider URL. The adapter accepts bounded base64 image output and does not download URLs from provider responses. The service validates PNG/JPEG raster data, rejects oversized, animated, corrupt, or excessive-pixel output, and re-encodes PNG pixels without embedded metadata. Paths are UUID-based and confined to the image directory; exclusive file creation protects existing files.

Files are written before the ready database transaction is committed, so incomplete files are not exposed. On ordinary failure, the new file is removed and the image becomes failed without modifying the menu. Like earlier phases, jobs run in-process with one backend worker/replica. Startup changes interrupted image jobs to failed for an explicit retry. A provider may charge for a timed-out/interrupted request; retrying can create another charge. A hard process crash can leave an orphan file; automatic cleanup and durable queues remain future work. Missing ready-cache files return a readable error and are never automatically regenerated; restore the volume from backup or repair/invalidate the record operationally.

No existing table columns changed; startup `create_all` adds the new table. No image costs are estimated, no images are generated in bulk, and no external storage service was introduced.

### Key Phase 7 files

- `backend/app/api/images.py`: thin generation/status/content routes.
- `backend/app/models/generated_image.py`, `schemas/image.py`: persistence and public metadata.
- `backend/app/services/image_service.py`: prompt, validation, cache, file storage, jobs, and recovery.
- `backend/app/services/images/base.py`, `factory.py`, `openai_provider.py`: replaceable image-provider interface and initial adapter.
- `frontend/src/components/DishIllustration.tsx`: on-demand generation, polling, cached image rendering, labels, retry/reload states.
- `backend/tests/test_images.py`: provider, cache, raster, storage, rollback, and lifecycle tests.
- `.env.example`, `docker-compose.yml`: image configuration and existing-volume storage.

### Phase 7 verification (2026-10-01)

- 158 pytest tests passed, including all previous regressions and 23 image tests. Tests cover provider envelopes/errors, byte/pixel limits, raster validation, source preservation, cache reuse without credentials, one active job per item, timeout, failure/retry, restart recovery, storage/database failures, path traversal, missing cached files, and filename-collision preservation.
- Docker Compose production compilation and TypeScript validation passed; all three services are healthy.
- The real OpenAI HTTP adapter was exercised with a mocked transport against PostgreSQL. A generated test PNG was validated, stored, served, and cached after one provider request. Two simultaneous database sessions competing for another item scheduled exactly one job. Interrupted work became failed, and the ready file/record survived backend restart.
- Browser checks confirmed loaded cached pixels, visible illustration labels, missing-configuration feedback on retry, and responsive rendering at 390 pixels without horizontal overflow. Menu cards keep their natural height when only some dishes have images.
- The QA menu `/menu/32f6f776-46f9-452a-9562-fcebccd72188` is named **Phase 7 - image service test**. Its cached raster explicitly says **MOCK PROVIDER IMAGE — Cache and rendering test only**, with model provenance `phase7-mocked-image`. It is a diagnostic fixture, not AI-generated food or a restaurant photo. This manually constructed QA menu has no uploaded source PDF and is not seeded in fresh databases.

Image credentials/model selection are absent in this environment. No paid image requests were made; real model output quality, latency, and account compatibility remain unverified. This historical verification predates Phase 8.


## Phase 8: Nearby discovery

Open **http://localhost:3000/explore**. Choose **Use my location** (browser permission required) or **Explore central Budapest** (a fixed search center, not demo restaurant data). Select restaurants, cafes, or bars, choose a distance, then click **Find nearby places**. A search returns at most 20 results ranked by distance; it is not an exhaustive directory. Changing filters clears old results and requires another explicit search. Panning the map does not trigger additional paid searches.

The map has numbered selectable markers, a search-center marker, and a place detail panel. The list shows names, addresses, categories, ratings and price levels when supplied. A list-only view works if the map is unavailable. Google/provider attribution remains visible. Choosing a card reuses its returned data instead of issuing another paid details request. Missing keys, unavailable location, empty searches, network failures and timeouts have readable states.

### Configure Google services

In the root `.env`, set:

```dotenv
PLACES_API_KEY=your_private_server_key
MAPS_API_KEY=your_public_browser_key
MAPS_MAP_ID=DEMO_MAP_ID
PLACES_TIMEOUT_SECONDS=15
```

Enable **Places API (New)** and **Maps JavaScript API** in your Google Cloud project with billing configured. Use separate keys: restrict `PLACES_API_KEY` to Places API (New) and your server IPs where applicable; restrict `MAPS_API_KEY` to Maps JavaScript API and website referrers such as `http://localhost:3000/*` and your eventual production domain. The browser key is intentionally public and returned by `/api/places/config`; never reuse the private Places or AI key there. Replace the demo map ID with your own for production. Run `docker compose up -d` after editing these variables (no frontend rebuild needed for keys).

Places queries use an explicit field mask. Rating/price fields can affect billing; configure quotas and budgets in Google Cloud. The official references are [Nearby Search](https://developers.google.com/maps/documentation/places/web-service/nearby-search), [Place Details](https://developers.google.com/maps/documentation/places/web-service/place-details), [Advanced Markers](https://developers.google.com/maps/documentation/javascript/advanced-markers/add-marker), and [Places policies/attribution](https://developers.google.com/maps/documentation/places/web-service/policies). Review the account's applicable EEA terms if its billing address is in the EEA. Before public deployment, supply the application's own public terms and privacy policy; the local prototype links Google's documents but does not yet provide operator-specific legal pages.

### API and architecture

- `GET /api/places/nearby?latitude=47.4979&longitude=19.0402&place_type=restaurant&radius=1500`
- `GET /api/places/{place_id}` — normalized details for a restaurant, cafe or bar.
- `GET /api/places/config` — only public browser map configuration.

Coordinates must be finite and in range. Radius is an integer from 100 to 50,000 meters (the UI offers 500 m–10 km). Place IDs are constrained before building the fixed Google URL. Private key headers and raw error bodies never reach the frontend. Requests have a timeout and a bounded response size, without automatic retries. Provider errors are translated to readable 404/502/503/504 errors. Business logic and the replaceable `PlacesProvider` interface live in `places_service.py`; route functions remain thin.

Normalized records contain `id`, `name`, `address`, `latitude`, `longitude`, `category`, optional `rating`/`price_level`, `provider`, and third-party `attributions`. Price levels are 0 (free) through 4 (very expensive). A multi-category place uses its supported primary category, then a deterministic supported-type fallback. Categories can overlap in Google's results.

Discovery results and coordinates are transient: no PostgreSQL table, localStorage cache, or menu-to-restaurant linkage is added in Phase 8. Responses use `Cache-Control: no-store`; backend access logs strip query strings, and service event logs omit coordinates and provider payloads. Any future reverse proxy must also avoid retaining location query strings. Google receives the selected area when the map is loaded or a search runs. No location prompt, Places request or map SDK load occurs on initial page entry.

The local app still has no authentication or public-deployment rate limiting. Add appropriate request controls before exposing paid endpoints publicly. DeepSeek remains a separate follow-up; this phase does not alter AI adapters.

### Important Phase 8 files

- `backend/app/api/places.py`
- `backend/app/schemas/places.py`
- `backend/app/services/places_service.py`
- `backend/app/core/logging.py`
- `backend/tests/test_places.py`
- `frontend/src/app/explore/page.tsx`
- `frontend/src/components/ExplorePlaces.tsx`, `Map.tsx`, `RestaurantCard.tsx`
- `frontend/src/services/googleMaps.ts`, `api.ts`
- `frontend/src/types/places.ts`
- `frontend/public/google-maps-logo.svg` — unchanged official Google attribution asset.

### Phase 8 verification (2026-10-02)

- 187 backend tests passed, including 29 Places/configuration/log-redaction cases with mocked Google HTTP responses.
- TypeScript checks and the Docker production build passed. All three Compose services are healthy; `/health` reports PostgreSQL connected and `/explore` returns HTTP 200.
- Browser checks covered initial disabled search, location selection, missing-key feedback, loading, normalized result cards, selected-place details, category changes, empty results and list-only mode. A temporary local fixture proxy supplied clearly labeled test data, without changing the production API or database.
- The mobile list layout was checked at 390px with no horizontal overflow. Desktop and mobile screenshots are saved beside the project as `menulens-phase8-desktop.png` and `menulens-phase8-mobile.png`.
- Live Google requests, actual map tiles/markers, and the real geolocation permission flow remain unverified until credentials/browser permission are supplied. No paid provider calls were made. Phase 9 and DeepSeek integration have not been implemented.
