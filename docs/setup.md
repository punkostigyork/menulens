# Setup and troubleshooting

## Quick start

### 1. Get the project

Install **Git** and **Docker Desktop** (or Docker Engine with Compose v2). Start Docker before continuing. Docker installs the application dependencies inside containers; you do not need Python, Node.js or PostgreSQL installed on your computer to run the app this way.

Clone this repository using its **Code → SSH** address on GitHub, then open the cloned folder. Replace `OWNER` with the repository owner's GitHub username or organization:

```sh
git clone git@github.com:OWNER/menulens.git
cd menulens
```

You can also use **Code → Download ZIP**, extract it, and open a terminal in the extracted folder. All Docker commands below run in the directory containing `docker-compose.yml`, `frontend/`, and `backend/`.

### 2. Create your local configuration

Copy the included template **once**, only if you do not already have `.env`:

```sh
# macOS / Linux
test -f .env || cp .env.example .env
```

```powershell
# Windows PowerShell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Open `.env` in your editor. On macOS you can use `open -e .env`; on Windows, `notepad .env`. Make sure the filename is exactly `.env`, not `.env.txt`.

```text
menulens/
├── .env              ← put your actual API keys here (private, ignored by Git)
├── .env.example      ← shareable template with empty key fields
├── docker-compose.yml
├── frontend/
└── backend/
```

**For a no-key demo, leave the API fields empty and go to step 3.** Demo browsing, uploading files, document preparation and explicit search filters work without paid providers. Menu extraction, explanations, natural-language search, illustrations and live discovery require the relevant configuration below.

#### OpenAI: menu understanding and food illustrations

Create an API key in your [OpenAI API account](https://platform.openai.com/api-keys), and configure API billing/credits there. A ChatGPT subscription does not provide API credits for this application. Set these existing lines in `.env` (do not add duplicate entries):

```dotenv
OPENAI_API_KEY=REPLACE_WITH_YOUR_OPENAI_KEY
MENU_AI_PROVIDER=openai
MENU_AI_MODEL=gpt-4.1-mini
IMAGE_PROVIDER=openai
IMAGE_MODEL=gpt-image-1-mini
ANTHROPIC_API_KEY=
```

The model names above are economical testing examples. Your account must have access to the selected models; requests may incur charges. Image generation uses the same OpenAI key and only runs when you request an illustration. Model capabilities and account requirements can change: see [OpenAI model documentation](https://developers.openai.com/api/docs/models).

Anthropic is optional: use `MENU_AI_PROVIDER=anthropic`, set `ANTHROPIC_API_KEY`, and choose a compatible `MENU_AI_MODEL`. Food illustration generation still uses OpenAI independently.

#### Google: maps and nearby places

In [Google Cloud Console](https://console.cloud.google.com/), select your project, enable billing, and enable **Maps JavaScript API** and **Places API (New)**. MenuLens does not need the other Google Maps APIs.

In **APIs & Services → Credentials**, create/configure two keys in the same project:

| Key | Used for | API restriction | Application restriction |
|---|---|---|---|
| MenuLens Browser | Showing the map | Maps JavaScript API | Websites: `http://localhost:3000/*` |
| MenuLens Server | Finding nearby places | Places API (New) | Your server's public outbound IP when practical |

If you open the app at `http://127.0.0.1:3000`, also allow `http://127.0.0.1:3000/*` on the browser key. A website-restricted key does not work for the backend Places requests. For server IP restrictions, use the public outbound IP, not `localhost`, a Docker address or `127.0.0.1`; a changing home IP requires updating that restriction.

```dotenv
MAPS_API_KEY=REPLACE_WITH_YOUR_GOOGLE_BROWSER_KEY
PLACES_API_KEY=REPLACE_WITH_YOUR_GOOGLE_SERVER_KEY
MAPS_MAP_ID=DEMO_MAP_ID
```

A browser key is a normal API key configured for website use. It is intentionally visible to the browser, which is why restrictions matter. One key can technically serve both roles if its restrictions allow both, but separate keys are recommended so the browser cannot expose the private server credential.

`DEMO_MAP_ID` is Google's shared map configuration for development, not an API key. Leave it exactly as shown for local testing. It enables the advanced markers used here; it does not remove API-key or billing requirements. Use your own map ID before production. See [Google setup](https://developers.google.com/maps/documentation/javascript/get-api-key) and [map ID guidance](https://developers.google.com/maps/documentation/javascript/advanced-markers/start).

Keep the template's local database settings unless you deliberately change them. `DATABASE_URL` must match `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB`; the hostname is `postgres` inside Docker. Do not change credentials on an existing volume just to match an example.

**Never commit `.env`, paste real keys into `.env.example`, or put private keys in frontend source.** The included `.gitignore` excludes local environment files. If a key has already been committed or shared, revoke/rotate it; adding an ignore rule does not remove Git history.

### 3. Build and start

```sh
docker compose up --build -d
```

The first build downloads dependencies and may take several minutes. Check startup with:

```sh
docker compose ps
```

Wait for frontend, backend and PostgreSQL to become healthy. A healthy container confirms the service is running; it does not validate external API credentials.

| Page | Address |
|---|---|
| Homepage | http://localhost:3000 |
| Hungarian demo | http://localhost:3000/demo |
| Upload | http://localhost:3000/upload |
| Search | http://localhost:3000/search |
| Explore nearby | http://localhost:3000/explore |
| Interactive API docs | http://localhost:8000/docs |
| Database-aware health | http://localhost:8000/health |

The health response should be `{"status":"ok","database":"connected"}`. The backend root `/` is not a page; use `/health` or `/docs`.

### 4. Test the app yourself

1. **Try the demo:** open `/demo`. You should see four Hungarian dishes in three sections, with HUF prices. No key is needed.
2. **Try free filter search:** open `/search`, choose **Choose filters**, enter ingredient `chicken` and a maximum price of `6000 HUF`. The seeded Csirkepaprikas should match. This does not call AI.
3. **Test extraction:** download the sample PDF from the demo page, or choose your own small PDF/JPG/PNG. Upload it on `/upload`, then start menu understanding. With OpenAI configured, it should become a readable menu with sections and prices. Uploading alone does not extract dishes.
4. **Test explanations/images:** request one dish explanation and one food illustration. Illustrations are labeled as AI-generated and cached; they are not restaurant photos.
5. **Test natural-language search:** on `/search`, describe a dish in a processed menu, for example `chicken under 6000 HUF`. Results depend on the dishes you have saved.
6. **Test Google:** on `/explore`, choose **Explore central Budapest**, then **Find nearby places**. The map and venue list should appear. Test **Use my location** separately and allow your browser's location permission.

Start with one small menu and a few images to check usage and account access. The demo is fictional, hand-authored data, not a quality benchmark or a live AI result.

### 5. Stop, restart or apply changed keys

```sh
# Stop the app; keep all saved data
docker compose stop

# Restart previously created containers with their existing configuration
docker compose start

# Apply changes to .env (restart alone does not reload environment values)
docker compose up -d

# Rebuild after pulling source-code changes
docker compose up --build -d
```

PostgreSQL records and uploaded/generated files live in named Docker volumes. `docker compose down` removes containers but preserves these volumes. **Do not run `docker compose down -v` unless you intend to delete the stored data.** Cloning the repository does not copy another person's local database or uploads.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Docker cannot connect to the daemon | Start Docker Desktop / Docker Engine, then retry. |
| `no configuration file provided` | Run commands in the folder containing `docker-compose.yml`. |
| Port already allocated | Another process uses 3000 or 8000; stop it or deliberately change the Compose port mapping and matching URLs/restrictions. |
| App says provider is not configured | Check root `.env`, exact variable names and model fields; run `docker compose up -d`. |
| OpenAI request fails | Check the key, API credit/billing, model access and whether that model supports the required input/output. |
| Map is blank or displays an authorization error | Check Maps JavaScript API, billing, browser key and the exact website referrer. Browser developer-console messages often identify the cause. |
| Map loads but nearby places fail | Check Places API (New), the server key and its application restrictions; do not use website restrictions on the server key. |
| Location is unavailable | Allow location in browser settings or use central Budapest. Non-local deployments require HTTPS for geolocation. |
| Uploaded menu is not searchable | Start processing and wait until its status is processed. |
| Database fails after changing a password | Editing `.env` does not rotate the password already stored in PostgreSQL. Restore the matching configuration or perform a deliberate database credential change. |

For service diagnostics, run `docker compose logs --tail=100 backend frontend`. Review logs before sharing them. Do not share `.env` or the output of `docker compose config`, which can contain expanded credentials. Detailed backup and deployment guidance is in [docs/deployment.md](deployment.md).

