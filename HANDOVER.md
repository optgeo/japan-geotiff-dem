# HANDOVER

Session log for `japan-geotiff-dem`. Read `CLAUDE.md` first for the
standing rules; this file is what actually happened, session by
session, and what to pick up next if resuming cold.

## 2026-08-08: First session, 1m DEM update kickoff

Claude's first time working in this repo. Starting point: repo already
had one complete upload cycle behind it (10m/5m/1m, README changelog
says "2026-05-28: First complete upload done"), all local `src/`/`dst/`
contents cleaned out afterward (only `.gitkeep` placeholders remained).
Goal this round: refresh the 1m DEM now that GSI's coverage has grown,
starting with Hokkaido.

- Read `Justfile`/`README.md`/`scripts/quadrans_script.rb` and the
  `gmldem2tif.rb` source (inside the `gmldem2tif:latest` image) to
  reconstruct the actual pipeline contract — see `CLAUDE.md` for the
  writeup. Key finding: `gmldem2tif.rb` expects `zip_dir` to directly
  contain mesh-level zips (`.zip` with `.xml` entries) — nested
  region-pack zips must go through `extract` first.
- Moved the working copy from `/Users/hfu/japan-geotiff-dem` to
  `/Volumes/github/japan-geotiff-dem` (external volume) for storage
  headroom — 1m coverage for all of Japan will not fit comfortably on
  the internal disk. Confirmed via `git remote -v` this is the same
  clone of `optgeo/japan-geotiff-dem`, not a fork/copy drift.
- Cross-checked GSI's update-info page
  (https://service.gsi.go.jp/kiban/app/data_update_info/): the 2026-07
  DEM1A update is real (announced 2026-07-31). Confirmed the general
  pattern that the announcement date and the mesh file's embedded
  compilation date don't have to match — see the provenance caveat in
  `CLAUDE.md`.
- Hidenori downloaded and placed the first Hokkaido region pack,
  `FG-GML-hokkaido-DEM1-20260616-Z001.zip` (~1.9 GiB), into `src/1z/`.
  Hokkaido ships as **46 parts total (Z001–Z046)** — this is 1 of 46.
- Ran the pipeline end to end on that one part as a smoke test:
  - `just extract 1` → 16 mesh-level zips landed in `src/1/`.
  - **Bug found and fixed**: `just convert 1` failed immediately
    (`realpath: dst/1: No such file or directory`) because `dst/1`
    didn't exist yet — only `src/1`/`src/1z` had `.gitkeep`
    placeholders carried over from a previous resolution's setup.
    Fixed by adding `mkdir -p dst/{{res}}` to the `convert` recipe in
    `Justfile`, plus `.gitkeep` in `dst/1`, `dst/5`, `dst/10` for
    parity with `src/`.
  - Re-ran `just convert 1` (docker daemon needed a manual start via
    `open -a Docker` first, image `gmldem2tif:latest` was already
    built locally, no rebuild needed) — succeeded, 949 mesh GeoTIFFs,
    ~1.4 GiB in `dst/1/`, zstd-max, ~4 minutes.
  - **Notable**: the extracted mesh filenames all read
    `-DEM1A-20250507` (2025-05-07), not the July 2026 update. Hokkaido
    Z001 alone doesn't confirm the new survey data landed — the
    updated meshes may be in a different Z-part. Worth checking as
    more parts come in.
- Updated `Justfile`'s Source Cooperative recipes (`docs`, `sync`) to
  match the role split already working in the sibling repo
  `cogenerate`: Hidenori does `source-coop login` once, locally;
  Claude only ever runs `aws ... --profile source-coop`. Corrected the
  bucket target from the old `s3://us-west-2.opendata.source.coop/...`
  form to `s3://smartmaps/japan-geotiff-dem` (matches the product's
  actual Source Cooperative URL already in `README.md`), added
  `--acl bucket-owner-full-control` per the `cogenerate` precedent.
  **Not yet exercised for real** — no upload has been attempted this
  session, and Hidenori's `source-coop login` status for this specific
  machine/session hasn't been confirmed.
- Confirmed (per Hidenori) that GSI's download site has no
  inventory/diff API — it's POST-with-selection returning a ZIP, full
  stop. Full periodic re-download + content diffing is the only
  update-detection strategy available; documented in `CLAUDE.md`.
- Added `DECISIONS.md` (ADR log, D1–D7) at Hidenori's suggestion,
  following the same `DECISIONS.md`/`HANDOVER.md`/`CLAUDE.md` split
  already used in `cogenerate`/`layers-martin`. Everything above that
  was a real decision (directory placement rule, Source Cooperative
  role split, idempotency scope, provenance handling, storage move,
  the open `quadrans/` upload question) now has a corresponding D-entry
  there; this file stays the session narrative only.
- Made the `README.md` Changelog's scope explicit (DECISIONS.md D7): it
  only gets a new entry once a `just sync`/`just docs` run has actually
  landed on the public bucket, since the README itself is uploaded
  there and doubles as the product's public description. No entry was
  added this session — nothing has been published yet.

- Reported progress publicly: posted a comment on
  [mapterhorn/mapterhorn#142](https://github.com/mapterhorn/mapterhorn/issues/142)
  (Hidenori's own earlier issue describing this pipeline), noting the
  2026-07-31 DEM1A update, that downloaded packs contain a mix of
  vintages rather than a wholesale re-release, and that Hokkaido is
  being reprocessed first.
- **Z002–Z007 processed** (of 46 Hokkaido parts), incrementally,
  confirming `extract`/`convert`'s skip-existing behavior works exactly
  as expected in practice (re-running against all parts placed so far
  each time, no duplicate work, no errors). New-vintage meshes kept
  turning up as more parts arrived — `20260603` (Z003, Z005, Z006) and
  `20260522` (Z007) — alongside plenty of `20250507`/`20251107`/
  `20250513`/`20250616`/`20250728` mesh dates. So the July 2026 DEM1A
  update is real and present, just spread thin across parts rather than
  concentrated in one.
- **README split** (Hidenori noticed `README.md` looked out of place on
  the actual Source Cooperative product page — self-referential links,
  "this repository" language, tool-marketing "Features" section — see
  DECISIONS.md D8 for the full diagnosis). Added `source-coop/README.md`
  as the data-facing file `just docs` now uploads; trimmed repo-root
  `README.md` down to pipeline/engineering content only, dropped the
  self-referential GitHub link and the Changelog (moved to
  `source-coop/README.md`, superseding D7's file target — same rule,
  new location).

### Current state (updated: 18 of 46 parts downloaded)

- `src/1z/`: 18 of 46 Hokkaido parts (`Z001`–`Z018`). Hidenori is
  downloading serially at night (bandwidth is narrower after dark, so
  parallel downloads stopped helping — see the "download pace" note
  below) — expect `Z019`+ to keep arriving one at a time.
- `src/1/`, `dst/1/`: fully processed through `Z017` as of the last
  check — 18,519 mesh GeoTIFFs. `Z018` extract+convert was kicked off
  right before this handover was written; **check
  `/tmp/convert_z18.log` and `dst/1` count on resume** to see whether
  it finished cleanly (same integrity check pattern as every batch so
  far: sum `.xml` entries in the newly-extracted mesh zips, compare to
  the increase in `dst/1/*.tif` count — see D-entries below, every
  batch through Z017 matched exactly, no corruption found).
- `quadrans/1/` still not run — still incomplete, still not worth it
  per D3.
- **`just sync 1` last run for real at Z001–Z012** (12,736 files,
  confirmed present remotely, 0 missing). **Z013 onward (through
  whatever Z018 converts to) has NOT been synced to Source Cooperative
  yet** — local `dst/1` is ahead of what's published. Run `just sync 1`
  again before trusting `smartmaps/japan-geotiff-dem`'s published `1/`
  prefix to reflect current local state (this matters for
  `hfu/mapterhorn-japan-bridge`'s `file_list.txt`-based sourcing — see
  "Related work" below).

### Related work: `hfu/mapterhorn-japan-bridge` (new, 2026-08-08)

This repo's output now also feeds a downstream tiling effort that
lives entirely in **other** repos/machines — don't duplicate that
narrative here, read it there instead:

- **What**: turns this repo's published 1m/5m/10m GeoTIFFs into
  Mapterhorn-format terrain tiles (PMTiles), as a bridge until upstream
  `mapterhorn/mapterhorn`'s own Japan source picks up this update.
- **Where the pipeline runs**: `hfu/mapterhorn` (a fork of
  `mapterhorn/mapterhorn`) on a different machine (`slate`, an M4
  Mac mini, SSH-accessible) — chosen over doing it on this machine
  (`aalto`, M1/8GB) because Mapterhorn's aggregation stage needs more
  RAM and genuine SSD random access than aalto's external HDD offers.
- **Where the narrative/decisions live**: `hfu/mapterhorn-japan-bridge`
  (a new, separate repo — deliberately NOT inside the `hfu/mapterhorn`
  fork, to keep that fork close to upstream). Its `CLAUDE.md`,
  `DECISIONS.md`, `HANDOVER.md` are the source of truth for that whole
  effort, including a currently-open viewer bug — check there first
  before assuming this file has the full picture.
- **Published product**: `smartmaps/mapterhorn-japan-bridge` on Source
  Cooperative (a second, separate product from
  `smartmaps/japan-geotiff-dem`).

### Next steps

- [ ] Confirm `Z018`'s convert finished cleanly (see above), then keep
      processing `Z019`–`Z046` as they arrive: `just extract 1 && just
      convert 1` per batch, same as every batch so far.
- [ ] Run `just sync 1` to publish everything through the latest
      converted batch — it's been several batches (Z013–Z018+) since
      the last real sync. Confirm `source-coop login` is current first
      (`aws s3 ls s3://smartmaps/japan-geotiff-dem/ --profile
      source-coop`, never `source-coop creds` directly — see
      `CLAUDE.md`). If `hfu/mapterhorn-japan-bridge` work is also
      resuming, it will want this synced first (its `file_list.txt` is
      built from what's actually published, not from this repo's local
      state).
- [ ] **TODO, blocking before this round counts as "the 1m update"**:
      once all 46 Hokkaido parts are downloaded and extracted, tally up
      which meshes carry a 2026 survey date (`20260522`, `20260603`,
      etc. — already confirmed present) versus older ones, so there's a
      clear answer to "did the July 2026 update actually land" beyond
      "some 2026-dated meshes exist somewhere" (see DECISIONS.md D4).
      If whole sub-regions of Hokkaido never show a 2026 date, that's
      worth surfacing to Hidenori rather than silently proceeding.
- [ ] Run `just quadrans 1` for Hokkaido once it's complete.
- [ ] Open question, still undecided (DECISIONS.md D6): does
      `quadrans/{res}` get its own Source Cooperative sync path? Now
      somewhat superseded in spirit by the `mapterhorn-japan-bridge`
      effort (which also produces a Mapterhorn-ready terrain artifact,
      via a different route) — worth deciding whether `quadrans/` is
      still needed at all, next time this comes up.

### `just docs` exercised for real (2026-08-08)

Hidenori ran `source-coop login`; confirmed live with a read-only
`aws s3 ls s3://smartmaps/japan-geotiff-dem/ --profile source-coop`
first (credentials good, bucket reachable, old `README.md` — 1529
bytes, 2026-05-29 — and no `INCOMPLETE` object visible). Ran
`just docs`: uploaded the new `source-coop/README.md` (2439 bytes) and
issued the `INCOMPLETE` removal (a no-op delete, since it wasn't
actually there — `aws s3 rm` doesn't error either way). Re-fetched
`https://source.coop/smartmaps/japan-geotiff-dem` afterward and
confirmed the new title, dataset-facing description, and Changelog are
live, with only an outward one-directional link to
`optgeo/japan-geotiff-dem` (no self-referential link back to the
Source Cooperative page itself).

**Correction to earlier advice**: `aws sts get-caller-identity
--profile source-coop` does **not** work as a login-check — it fails
with an opaque `Unknown` error, because this profile's `endpoint_url`
(`https://data.source.coop`) is S3-only and doesn't serve the STS API.
Use `aws s3 ls s3://smartmaps/japan-geotiff-dem/ --profile
source-coop` instead. Fixed in `CLAUDE.md` and `DECISIONS.md` D2.

### `just sync 1` exercised for real, first time (2026-08-08)

Before running any real data sync, Hidenori asked directly whether
repeated `sync` is safe or risks disaster — this is what led to finding
and fixing the `--delete` bug (D9) and the mtime-vs-content-hash waste
(D10) earlier today, both fixed in `Justfile` before this run.

Sequence: re-confirmed a fresh `source-coop login` live
(`aws s3 ls ... --profile source-coop`), uploaded one real mesh file by
hand first (`FG-GML-6239-27-29-DEM1A-20250507.tif`) as a minimal test,
verified it back with `gdalinfo /vsicurl/https://data.source.coop/
smartmaps/japan-geotiff-dem/1/...` — read correctly, right CRS
(EPSG:6668), right dimensions. Then ran `just sync 1` for real against
the full Z001–Z012 batch (12,736 local files).

Result: ~1.5 GiB transferred (matches the ~1,198-file genuinely-new
estimate from D10's analysis, not a full 17 GiB re-transfer), exit code
0, no errors. Verified afterward with a targeted remote listing scoped
to the 9 mesh-code prefixes involved (`622x`/`633x`/`634x` range, not a
full-bucket listing — learned that lesson from the credential-expiry
incident above): all 12,736 local files confirmed present remotely,
0 missing. This is genuinely live now — Hokkaido's Z001–Z012 1m data is
published at https://source.coop/smartmaps/japan-geotiff-dem/1/.

### Note on download pace (2026-08-08)

`Z003` is still slow to download as of this session. Hidenori's
observation, worth keeping in mind for later sessions: as GSI's 1m
coverage keeps getting richer, the download+verify wait at the front of
this pipeline will likely keep growing — and absorbing that wait (plus
the per-part bookkeeping of what's actually landed and what vintage it
is) may be a real part of this project's value, not just overhead to
optimize away.

**Tried and ruled out, don't re-suggest**: Claude proposed a few ways
to speed up the download side — more parallel browser tabs, a
segmented multi-connection downloader (`aria2c`), or Claude fetching
files directly via `curl`. The `curl` idea wasn't viable: GSI's
download URLs (e.g.
`https://service.gsi.go.jp/kiban/app/api/download/file/728977`, the
address for `Z015`) are session-bound behind an `isLogin` gate, and
handling that session's cookies would mean touching credential-like
material — not something to do. The parallel-tabs idea got an actual
empirical test: Hidenori ran 3 downloads concurrently and watched
`btop` — aggregate bandwidth didn't increase at all versus one file at
a time, indicating GSI throttles per session/account rather than per
connection. So neither more browser tabs nor a segmented downloader
would help; both hit the same limit. Download speed is a fixed
characteristic of a portal designed around individual/regional
downloads (see `CLAUDE.md`'s Mission section), not something to
route around — plan around the pace rather than trying to beat it.

### Data integrity check, Z008–Z010 (2026-08-08)

Hidenori asked directly whether anything on his end (manual downloads,
placing files) has caused skipped or corrupted output so far. Checked
rigorously for the Z008–Z010 batch rather than just trusting exit
codes: summed `.xml` entries across all 56 newly-extracted mesh zips
(3,461) and compared against the actual increase in `dst/1/*.tif`
count (6,957 → 10,418, i.e. +3,461). **Exact match** — every single
source XML produced a valid output GeoTIFF, nothing silently skipped or
failed. Same reasoning applies retroactively to Z001–Z007 (each
`convert` run completed with exit code 0, and `gmldem2tif.rb` raises on
GDAL failures rather than silently continuing).

Also found and fixed a real bug in `Justfile`'s `sync` recipe before
any real data upload was attempted — see D9 in `DECISIONS.md`: the
original `--delete` flag would have wiped out ~177k already-published
non-Hokkaido 1m files on the first real `sync`, since local `dst/1`
only ever holds whatever's been processed so far, not the full
national set. Fixed to be additive-only; the dangerous mirror behavior
now lives in a separately-named `sync-mirror` recipe.

### Long-term notes

- Hidenori wants full-Japan 1m coverage eventually, but is fine
  treating Hokkaido as its own complete-then-publish cycle rather than
  waiting for every prefecture before the next upload.
- Open design question for Hidenori (DECISIONS.md D6): should
  `quadrans/{res}` (the Mapterhorn-ready LERC mosaic) get its own sync
  path to Source Cooperative? Currently it's local-only.
- Open gap, accepted for now (DECISIONS.md D9 consequences): updated
  meshes upload under a new dated filename rather than replacing the
  old one in place, so superseded-date duplicates will accumulate
  under the additive-only `sync`. Revisit with a cleanup pass once this
  becomes a bigger practical problem.

### Blocked on Hidenori

- Downloading the remaining 45 Hokkaido `Z`-parts, one at a time
  through GSI's site (built for individual/regional downloads, not
  bulk retrieval — see `CLAUDE.md`'s Mission section).
- Confirming `source-coop login` has been run on this machine before
  any upload step is attempted.
