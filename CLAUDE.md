# Working in this repo

This is a personal fork (`origin` = `chocksmith/minime-wa-llm`) of
`ilanbenb/wa_llm` (`upstream`). Push to `origin`, not `upstream`.

`docker-compose.yml` here orchestrates the **whole personal stack**, not
just this app: `postgres`, `whatsapp` (GOWA), `web-server` (this app), and
`realestate-bot` (built from the sibling `minime` repo — see its
`CLAUDE.md` for that side of the relationship). Current live deployment
host and layout: see the note at the top of README.md's "Operations"
section (§7) — keep it updated if the deployment ever moves.

## The WhatsApp session volume is precious

`wa_llm_whatsapp` (mounted at `/app/storages` in the `whatsapp` container)
*is* the paired WhatsApp session. Never `docker compose down -v` or
otherwise remove/recreate it casually — that forces re-scanning the QR
code, which affects every bot sharing the session (currently `web-server`
and `realestate-bot` both do, via `WHATSAPP_WEBHOOK` fan-out — see
"Companion services" in the README). When migrating hosts, copy this
volume (and `wa_llm_postgres`, which also holds GOWA's own device-pairing
state) byte-for-byte rather than starting fresh.

## Never mount anything at `/app/whatsapp-bot`

That's the `realestate-bot` service's source-code path inside the
container. A named volume mounted there once silently froze the running
code to whatever was in the image the first time the volume was
populated — Docker only auto-populates a named volume from the image on
first use, so every later rebuild appeared to succeed while the container
kept running stale code. State for that service belongs under
`/app/data` instead (see `realestate_bot_state` volume in
`docker-compose.yml`).

## `docker-compose.override.yml`

Tracked in this repo, auto-loaded by `docker compose`. Currently remaps
postgres's *published* port to `5433` because the current deployment host
has an unrelated local postgres already bound to `127.0.0.1:5432`.
Internal container-to-container traffic is unaffected either way (still
`postgres:5432` on the compose network) — if you ever see a port-bind
conflict on a fresh host, this file is the first place to check, and
`ports:` needs the `!override` YAML tag to actually replace (not
concatenate with) the base file's port list.
