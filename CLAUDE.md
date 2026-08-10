# CLAUDE.md

Guidance for Claude working on this repository.

**Doc map**: this file is *how to operate* day to day. `DECISIONS.md` is
*why* things are the way they are (ADR log — read it before
reconsidering something that looks arbitrary). `HANDOVER.md` is *what
happened*, session by session, and what to do first if resuming cold.

## Language policy

Converse with Hidenori (chat, CLI turns, questions) in **Japanese**.
Everything that lands in the repository — code, comments, `.md` prose,
commit messages — stays in **English**, matching the `optgeo` family of
sibling repos (`cogenerate`, `kitavolca`, etc.). Don't mix.

## Mission

Convert GSI (国土地理院) 基盤地図情報 DEM data — available at 10m, 5m, and
1m resolution — from its native JPGIS/GML distribution format into
GeoTIFF, and republish it durably on Source Cooperative
(`smartmaps/japan-geotiff-dem`). The 1m/5m per-mesh GeoTIFFs in `dst/`
are the primary published product; `quadrans/` additionally produces a
LERC-compressed, quadrant-merged mosaic intended for Mapterhorn-style
terrain-tile pipelines (see "Open question" below — this mosaic is not
currently wired into the upload path).

This is one instance of the `optgeo` "Adopt Geodata" pattern: adopt an
open geospatial dataset, convert it cloud-native, publish it durably on
Source Cooperative. Sibling repos: `optgeo/cogenerate`,
`optgeo/fabdem-contour-fiji`, `optgeo/c2`, `optgeo/oam-starc`.

**Why this is worth doing, not just mechanical conversion**: GSI's
download portal is built around an individual, interactive use case —
a person signing in and fetching a limited geographic area at a time
(session-bound download URLs, one prefecture part per request, e.g.
Hokkaido's 46 parts). That's a different use case from this project's
(bulk, automated, national-scale reprocessing), so there's no
inventory/diff API to script against (D4) — the per-part fetching has
to happen by hand, once, per refresh. This project's value is doing
that once and republishing the result as a clean, uniform,
directly-fetchable GeoTIFF dataset, so nobody downstream needs to
repeat the same region-by-region retrieval themselves.

## Current machine and scope (updated 2026-08-11 — read this before assuming anything below)

**Runs on `slate`** (M4 Mac mini, headless/SSH-only,
`/Volumes/Migrate-2025-04/github/japan-geotiff-dem-repo`), not
`aalto`. `aalto`'s external HDD — this repo's original working-copy
location (D5) — failed outright on 2026-08-11 (bad enough that even
`fsck_hfs`, a full system restart, and a full drive power cycle didn't
restore real read throughput; see `HANDOVER.md` and `DECISIONS.md`
D11/D12 for the full incident). `slate` is now the only machine with a
live copy of this project — treat any older reference to `aalto` in
this file or in git history before 2026-08-11 as stale.

Docker on `slate` runs via **colima**, not Docker Desktop (headless,
no GUI login flow available) — `colima start -f --mount
/Volumes/Migrate-2025-04:w` before `convert` will work; a plain
`colima start -f` only mounts colima's own default scope and silently
produces empty bind-mounts for anything outside it.

**Scope, as of 2026-08-11: Kyushu/Okinawa only, best-effort, no
deadline.** Hokkaido is deliberately frozen (not abandoned) after the
drive failure took all 46 of its region-pack zips with it — resuming
it means re-downloading all 46 parts from GSI from zero, and should
only happen after an explicit fresh decision, not by default. Of
Kyushu/Okinawa's 25 region-pack zips, only 10 (`Z010`-`Z019`) survive;
the other 15 would also need re-downloading if ever wanted. See
`DECISIONS.md` D12 for the full reasoning.

## Pipeline

```
just extract <res>   # src/{res}z/*.zip  -> src/{res}/*.zip   (unzip -n, skip existing)
just convert <res>   # src/{res}/*.zip   -> dst/{res}/*.tif   (docker: gmldem2tif)
just quadrans <res>  # dst/{res}/*.tif   -> quadrans/{res}/{n,e,s,w}.tif  (LERC mosaic)
just sync <res>      # dst/{res}         -> s3://smartmaps/japan-geotiff-dem/{res}
just docs            # source-coop/README.md, INCOMPLETE marker -> same bucket
```

`res` is `1`, `5`, or `10`.

### Directory naming

- `src/{res}z/` — raw files as downloaded from GSI's kiban download
  service. **Inspect before placing a new download here**: if the zip
  contains further `.zip` entries (a region/prefecture bulk pack), it
  belongs in `src/{res}z` and needs `extract` first. If it already
  contains `.xml` GML files directly (an individual mesh-code zip), it
  can go straight into `src/{res}` and `extract` can be skipped for it.
- `src/{res}/` — mesh-level zips, each containing GML `.xml` file(s).
  This is exactly what `gmldem2tif.rb` consumes (it does not recurse
  into nested zips itself — that's `extract`'s job).
- `dst/{res}/` — one GeoTIFF per mesh, EPSG:6668, ZSTD-max compressed.
- `quadrans/{res}/` — four merged mosaics (north/east/south/west
  quadrant, split by mesh code per `scripts/quadrans_script.rb`),
  LERC-compressed via `gdal_translate` for Mapterhorn compatibility.

### Idempotency

Both `extract` (`unzip -n`) and `convert` (`gmldem2tif.rb`'s
`tif_valid?` check, skips any mesh whose output `.tif` already opens
cleanly) are safe to re-run repeatedly as new source archives arrive.
`quadrans` is **not** incremental — it rebuilds each quadrant's mosaic
from every matching `dst/{res}/*.tif` on every run, so it's only worth
running once a batch (e.g. a whole prefecture) is complete, not after
every individual mesh pack.

### Data provenance caveats (DECISIONS.md D4)

- GSI's "更新情報" (data update info) page date is when an update was
  *announced*, not necessarily when the underlying files were
  generated — the mesh zip's embedded date (e.g.
  `FG-GML-624000-DEM1A-20250507.zip`) can be considerably earlier.
  Don't treat a mismatch as a sign the download is stale by itself;
  compare it against the *previous* local baseline instead.
- Large prefectures are split into multiple region-pack files (e.g.
  Hokkaido: `Z001` through `Z046`). Different parts can carry
  different-vintage mesh data — check each part's extracted filenames,
  don't assume uniform vintage across a whole prefecture.
- GSI's download site has no query/inventory API: it's a POST-with-
  selection that returns a ZIP. There is no way to ask "what changed"
  ahead of downloading. The only viable update-detection strategy is
  full periodic re-download plus content diffing.

## Source Cooperative publishing (DECISIONS.md D2)

Matches the role split already established in `cogenerate`: Hidenori
runs `source-coop login` once, locally (human-only step — creating or
authenticating a Source Cooperative account is not something Claude
does). That populates the `source-coop` profile in `~/.aws/config`
(`credential_process = source-coop creds`, plus `endpoint_url`).

Claude only ever invokes `aws ... --profile source-coop`. **Never run
`source-coop creds` directly** — it prints the actual temporary AWS
access key/secret/session token to stdout, which is exactly the kind
of thing that shouldn't land in a transcript (this happened once in
`cogenerate` — low-impact since the session token expired quickly, but
avoid repeating it). If you need to confirm the login session is live,
use `aws s3 ls s3://smartmaps/japan-geotiff-dem/ --profile source-coop`
instead — it authenticates via the same `credential_process` without
ever printing secret material, and doubles as a sanity check that the
bucket/endpoint routing is actually correct. **Don't use `aws sts
get-caller-identity`** for this — confirmed 2026-08-08 that it fails
with an opaque `Unknown` error under this profile, because its
`endpoint_url` (`https://data.source.coop`) is S3-only and doesn't
serve the STS API at all; the failure is about the wrong AWS service
being hit, not about the credentials.

Target: `s3://smartmaps/japan-geotiff-dem` (Source Cooperative product
page: https://source.coop/smartmaps/japan-geotiff-dem).

**Never add `--delete` to the `sync` recipe (DECISIONS.md D9)**. Local
`dst/{res}` normally holds only whatever prefecture was just
(re)processed, not the full national dataset for that resolution — a
`--delete` mirror sync would erase every other prefecture's
already-published files still missing locally. The dangerous
full-mirror version is deliberately kept in a separate `sync-mirror`
recipe, `--dryrun`-checked and confirmed with Hidenori before ever
running for real, only for the (rare) case where local genuinely holds
the complete current national set.

`sync` also passes `--size-only` (DECISIONS.md D10) — `aws s3 sync`'s
default mtime-based comparison is useless here since a freshly-run
`convert` gives every local file today's mtime regardless of whether
its content changed, which would otherwise force a full re-transfer of
the whole batch on every run. Safe because mesh filenames already
encode the survey date, so same-name + same-size reliably means
unchanged content.

**Open question, not yet decided (DECISIONS.md D6)**: `quadrans/{res}`
output has no `just sync-quadrans`-equivalent recipe — it's generated
locally but never uploaded anywhere. Ask Hidenori before inventing one;
it affects what path/product the Mapterhorn-ready mosaic would be
served from.

## Two READMEs (DECISIONS.md D8)

`source-coop/README.md` — not the repo-root `README.md` — is what
`just docs` uploads to the product root on Source Cooperative. Repo-root
`README.md` is engineering-facing (for people running `just` commands);
`source-coop/README.md` is data-facing (for people who only ever touch
the S3 bucket, never GitHub). Don't let content drift back together —
in particular, `source-coop/README.md` must never link back to the
Source Cooperative page itself (it would be self-referential to a
reader already there), and shouldn't use GitHub-ism language like
"this repository."

`source-coop/README.md`'s `## Changelog` section is a public record of
what's actually live, not a work log (DECISIONS.md D7, now relocated
here). Only append an entry there right after a `just sync`/`just docs`
run has completed against the public bucket — format: `- YYYY-MM-DD:
<what changed> (resolution(s), and region if partial-coverage).`
In-progress work (downloads in flight, local pipeline runs, bugs found
and fixed) belongs in `HANDOVER.md` instead, which is never synced
anywhere. Also avoid hardcoding current coverage extent in
`source-coop/README.md` outside the Changelog — it goes stale; point at
the bucket's own file listing instead.

## Local tooling

`just`, `docker` (the `gmldem2tif:latest` image should already be built
locally — check `docker images` before trying to rebuild it), `ruby`,
GDAL CLI (`gdalbuildvrt` runs on the host, not in Docker, inside
`quadrans_script.rb`), `unzip`, `aws` CLI, `gh` (for git operations —
see "Current machine and scope" above). On `slate`, the Docker daemon
is **colima**, not Docker Desktop: `colima start -f --mount
/Volumes/Migrate-2025-04:w` before `convert` or `quadrans` will work
(no GUI `open -a Docker` equivalent on a headless machine).
