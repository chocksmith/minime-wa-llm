# Working in this repo

This is a personal fork (`origin` = `chocksmith/minime-wa-llm`) of
`ilanbenb/wa_llm` (`upstream`). Push to `origin`, not `upstream`.

This repo is vendored as a git submodule at `vendor/wa_llm` inside the
`minime` repo, whose root `docker-compose.yml` runs the **live personal
stack** (`postgres`, `whatsapp`/GOWA, `web-server` = this app,
`realestate-bot`). The `docker-compose*.yml` files here are for standalone
development only — never run them on the live host alongside minime's
stack (same `whatsapp` container_name and volumes). Deployment notes live
in minime's README ("Running it").

## The WhatsApp session volume is precious

`wa_llm_whatsapp` (mounted at `/app/storages` in the `whatsapp` container)
*is* the paired WhatsApp session. Never `docker compose down -v` or
otherwise remove/recreate it casually — that forces re-scanning the QR
code, which affects every bot sharing the session (currently `web-server`
and `realestate-bot` both do, via `WHATSAPP_WEBHOOK` fan-out — see
"Companion services" in the README). When migrating hosts, copy this
volume (and `wa_llm_postgres`, which also holds GOWA's own device-pairing
state) byte-for-byte rather than starting fresh.

## `docker-compose.override.yml`

Tracked in this repo, auto-loaded by `docker compose` (standalone use only;
minime's compose file sets the 5433 mapping itself). Currently remaps
postgres's *published* port to `5433` because the current deployment host
has an unrelated local postgres already bound to `127.0.0.1:5432`.
Internal container-to-container traffic is unaffected either way (still
`postgres:5432` on the compose network) — if you ever see a port-bind
conflict on a fresh host, this file is the first place to check, and
`ports:` needs the `!override` YAML tag to actually replace (not
concatenate with) the base file's port list.
