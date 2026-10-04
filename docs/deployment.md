# Deployment and recovery

## Supported setup

The shipped Compose stack is a local/private, single-instance prototype. It binds frontend/backend ports to loopback and keeps PostgreSQL private. Use one backend worker; jobs run inside that process. No Kubernetes, accounts, payment service or external queue is required.

Before upgrades, back up both PostgreSQL and uploaded/generated files. Record the application version and environment configuration separately, without committing secrets. `create_all` does not perform schema migrations; future schema changes require a migration/rollback plan.

## Start and update

1. Install Docker/Compose, ensure ports 3000 and 8000 are free.
2. Copy `.env.example` to `.env` only on first setup. Set unique database credentials for any nonlocal deployment, and keep `DATABASE_URL` consistent.
3. Run `docker compose up --build -d`.
4. Check `docker compose ps`, `/health`, `/docs`, `/demo`, and `python3 scripts/smoke.py`.
5. Configure external providers independently. Blank keys leave uploads, document preparation, demo browsing and filter search usable.

Changing `POSTGRES_PASSWORD` in `.env` does not rotate credentials in an existing database volume. Coordinate database-side changes with the connection URL. `docker compose down` preserves named volumes; **`docker compose down -v` deletes data** and is not an upgrade or recovery command.

## Public deployment prerequisites

Place a TLS reverse proxy in front of port 3000. Keep port 8000 and PostgreSQL off the public network; Next.js proxies `/api`. Configure the actual frontend origin in `CORS_ORIGINS`; browser geolocation requires HTTPS except for local development. Ensure proxy upload limits/timeouts support the configured file size, and do not retain location query strings in proxy access logs.

Before exposing this prototype publicly, add authentication/authorization and request/usage limits for uploads and paid endpoints, configure Google/provider quotas, and provide operator-specific privacy/terms pages and retention/deletion procedures. These controls are intentionally not claimed as implemented. The Google links in Explore do not replace your own policy pages. Do not publish the bundled database development credentials.

Use a secrets manager or restricted environment file appropriate to the hosting platform. Never bake private secrets into images or `NEXT_PUBLIC_*` variables. `MAPS_API_KEY` is the sole intentional browser-visible key; use a different key from `PLACES_API_KEY`.

## Google setup

Enable Places API (New) and Maps JavaScript API in a billing-enabled project. Restrict the Places key by API and backend IP as appropriate. Restrict the Maps JavaScript key by API and website referrers. Set your own `MAPS_MAP_ID` for production. Ratings/price-level fields can change request billing. Review the applicable account terms, including EEA-specific requirements where applicable.

Official references: [Nearby Search](https://developers.google.com/maps/documentation/places/web-service/nearby-search), [Advanced Markers](https://developers.google.com/maps/documentation/javascript/advanced-markers/add-marker), [Places attribution/policies](https://developers.google.com/maps/documentation/places/web-service/policies). The unchanged Google logo in `frontend/public` comes from the attribution assets linked in those policies.

## Backup

Run from the project root. The following pauses writes briefly so the database and file archive correspond. Use a new backup directory for each snapshot; store backups securely off the host too.

```sh
mkdir -p backups/your-snapshot
docker compose stop frontend backend
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/your-snapshot/database.dump
docker compose run --rm --no-deps -T backend tar -C /app/uploads -czf - . > backups/your-snapshot/uploads.tar.gz
docker compose start backend frontend
```

Check command exit statuses and verify both archives are nonempty. If a backup step fails, restart the stopped services and investigate before treating it as a usable backup. The backend one-off container runs `tar`, not the application, so it does not process jobs or seed data.

## Restore rehearsal

Restore into a **separate, empty installation**, never over a running database. Copy the same application version and protected configuration; give the rehearsal a distinct Compose project name, volume set and host ports. The shipped top-level project name can be overridden with `docker compose -p menulens-restore`; change published ports in the rehearsal copy to avoid conflicts. Disable demo seeding until verification completes if exact snapshot counts matter.

With only the fresh rehearsal PostgreSQL service started, run these commands **from the rehearsal project**:

```sh
docker compose -p menulens-restore exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges' < /secure/path/database.dump
docker compose -p menulens-restore run --rm --no-deps -T backend tar -C /app/uploads -xzf - < /secure/path/uploads.tar.gz
docker compose -p menulens-restore up -d
```

Only restore trusted archives. Verify `/health`, stored menu/item counts, cached image content and source-file availability. A restore rehearsal against independent volumes is necessary before trusting a backup strategy. These commands are documented; no backup/restore of user data has been executed as part of Phase 9.

## Operational limits

Monitor disk use (uploads + generated images + PostgreSQL), provider spending, failure rates and timeouts. Internal errors must not include credentials or raw provider output. Query strings are omitted from backend access logs. Provider calls can incur charges even when a job times out; users retry explicitly. Gracefully drain active jobs before planned restarts where practical. Interrupted jobs become failed on startup.

Ready images whose stored files are missing do not regenerate automatically. Restore the matching file volume or repair the affected cache operationally. Automatic orphan cleanup, queue durability, migrations and horizontal scaling are future work.
