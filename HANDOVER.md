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
- `src/1/`, `dst/1/`: fully processed through `Z018` — 20,396 mesh
  GeoTIFFs, no errors in extract or convert logs (same clean pattern
  as every batch through Z017).
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

## 2026-08-09: Hokkaido download completed; Kyushu/Okinawa downloads started in parallel

**Reconstructed summary, not the original session log** — the source
working copy (`aalto`'s external HDD) failed before this entry could be
committed and pushed; see the 2026-08-11 entry below for the full
incident. What follows is assembled from cross-references in
`hfu/mapterhorn-japan-bridge`'s own `HANDOVER.md` (which was read in
full during the 2026-08-11 recovery session and survives), not from
this repo's own original prose.

- Hidenori continued downloading Hokkaido's remaining `Z`-parts
  through GSI's portal by hand over the course of the day, reaching
  **46/46 parts downloaded** by session end.
- `extract`/`convert` kept pace incrementally as parts arrived; `just
  sync 1` was run for real at least once more, publishing through
  `Z018` (6.0 GiB transferred) with a dated changelog entry via `just
  docs`.
- Kyushu/Okinawa 1m downloads were **also started in parallel** this
  session, per Hidenori's own "北日本・南日本を先行させる" plan —
  islands/coastline-heavy regions first, to stress-test sea handling
  in the downstream `mapterhorn-japan-bridge` pipeline, ahead of the
  larger-landmass regions.
- Exact per-part timing, any bugs found, and the full narrative this
  session actually had are not recoverable — this summary exists only
  to keep the chronology from having a silent gap. Treat any detail
  not also stated in the 2026-08-10/2026-08-11 entries below as
  unverified.

## 2026-08-10: `aalto`'s HDD hit a wall; conversion work migrated to `slate`'s SSD; Kyushu/Okinawa fast-tracked via an internal-disk shortcut

Picking up where 2026-08-09 left off: Hokkaido 46/46 downloaded,
Kyushu/Okinawa downloads continuing in parallel (Hidenori manually
working through GSI's per-part portal, eventually reaching all 25
parts today). Extract/convert kept grinding through the backlog on
`aalto` for most of the day — then got dramatically worse.

### The HDD problem, diagnosed properly this time

2026-08-09's entry already flagged `aalto`'s external USB HDD as slow
(~0.3-2MB/s). Today it got bad enough to actively block work: a single
`ls dst/1/*.tif | wc -l` timing out at 120s, a `docker run` for
`convert` sitting at 0% CPU / zero block-I/O growth for minutes at a
time. Root-caused through a sequence of tests, documented here because
the diagnostic *method* is reusable even if this exact drive gets
replaced:

- **Single-file stat vs. directory/glob enumeration**: `ls -la
  /path/to/one/known/file.tif` returned instantly even when `ls
  dir/*.zip` or `ls dir | wc -l` on the same directory hung. This
  matters diagnostically — it rules out "the whole disk is dead" (a
  truly failed drive fails single-file reads too) and points at
  directory-enumeration-heavy operations specifically.
- **Multi-process contention made it categorically worse, not just
  additively worse**: `unzip` (still draining the Kyushu/Okinawa
  extract queue), a `docker run` convert container, `rm -rf` on a
  ~156-file holding directory, and a 3-second-interval background
  sweeper script (see 2026-08-09 mapterhorn-japan-bridge entries —
  `/tmp/kyushu_sweep.sh`, running continuously for ~20+ hours by this
  point) were all touching the same disk at once. Killing the extract
  chain and the sweeper, then deleting the sweeper's now-empty holding
  directory, was necessary before `convert` could make any progress at
  all — but even fully alone, a single `docker run convert` still only
  processed ~1.3 files/second (see below), confirming the underlying
  drive itself, not just contention, was the ceiling.
- **A controlled single-process re-test** (everything else stopped, one
  fresh `convert` container, block-I/O and log-line growth sampled at
  fixed intervals) showed real forward progress but at ~1.3
  already-converted-mesh skip-checks/second — extrapolated, clearing
  just the "skip already-done files" pass for Hokkaido's ~900 zips
  (each ~10-25 sub-tiles) would have taken 2-4.5 hours *before* any new
  conversion work even started.
- **A file-count-reduction hypothesis, tested and disproven**: reasoned
  that transferring 46 large region-pack zips (`src/1z/`) instead of
  901 already-extracted individual mesh zips (`src/1/`) might be faster
  by reducing per-file seek overhead, even at similar total bytes.
  Measured: **no meaningful difference** (still 80KB/s-1.9MB/s,
  fluctuating). The bottleneck is the drive's raw sustained read
  bandwidth, not seek count — don't assume a plausible-sounding I/O
  optimization helps without measuring it.
- No SMART data available (USB-attached), no logged I/O errors, disk
  otherwise mounts and reports free space normally — this reads as a
  drive that has degraded under sustained load rather than one that has
  outright failed, but the practical effect (workload-blocking) is the
  same either way. **Recommendation, not yet acted on**: this drive is
  no longer fit for this workload; replace it (see the same-day
  Mac-hardware/SSD discussion in `mapterhorn-japan-bridge`'s own
  session — this incident is the live case study for that discussion).

### The fix: move `convert` (and eventually `extract`) to `slate`

`slate` (the M4 Mac mini already used for `hfu/mapterhorn`'s
aggregation pipeline, see `mapterhorn-japan-bridge/CLAUDE.md`) has
~1.4TB free on its own real internal-adjacent SSD
(`/Volumes/Migrate-2025-04`) as of today (freed up during the same
session — see that repo's HANDOVER.md). Set up this repo's
conversion pipeline there from scratch:

- **Docker on `slate`, headless**: `slate` has no display attached
  (SSH-only). Docker Desktop needs a GUI first-launch permission flow,
  which doesn't work headless. Used **colima** instead
  (`brew install colima docker`) — a CLI-only, Docker-API-compatible
  VM manager built for exactly this (headless CI/server macOS use),
  using Apple's own Virtualization.framework as its backend on Apple
  Silicon. No GUI interaction needed anywhere in colima's own setup.
  - **Gotcha #1**: `colima start -f` alone only mounts colima's default
    scope (roughly the home directory) into its VM. A bind-mount of
    `/Volumes/Migrate-2025-04/...` (a *different* volume) into a
    container silently produced an **empty directory inside the
    container** — no error, just nothing there, which looked exactly
    like an application bug (`gmldem2tif.rb`'s `Dir.glob` finding
    nothing) rather than an infrastructure misconfiguration. Fixed by
    restarting with `colima start -f --mount
    /Volumes/Migrate-2025-04:w`. Verified with a plain `docker run
    --rm -v <path>:/x alpine ls /x` sanity check before trusting the
    real pipeline's output (or lack of it) again.
  - **Gotcha #2**: `docker run` initially failed with `docker:
    error getting credentials - err: exec: "docker-credential-desktop":
    executable file not found` — a stale `"credsStore": "desktop"` key
    in `~/.docker/config.json`, left over from an incomplete/empty
    prior `Docker.app` installation attempt on `slate` (found at
    `/Applications/Docker.app`, essentially empty — 3 directory entries
    total, never a real install). Fixed by removing that key from the
    JSON. Worth checking on any machine that once had Docker Desktop
    even briefly, before assuming a fresh colima/docker setup is broken.
  - Built the `gmldem2tif:latest` image from this repo's existing
    Dockerfile (`docker build -t gmldem2tif .` inside a copy of
    `github/gmldem2tif`, ~18s, no issues — building *inside* Docker
    doesn't hit the host's Command Line Tools at all, unlike a native
    Homebrew source build, see the `source-coop` CLI note below).
  - **Result**: once both gotchas were fixed, a `just convert 1` smoke
    test against 5 already-transferred mesh zips finished in **26
    seconds**, producing real, correctly-georeferenced GeoTIFF output
    (verified: coordinates, raster dimensions, pixel counts all
    sane) — vs. hours-to-indefinite on `aalto`.

### Getting Hokkaido's data onto `slate`

Transferring `aalto`'s already-extracted `src/1/` (901 mesh zips) via
`rsync` was itself bottlenecked by the same degraded `aalto` HDD read
speed (~0.5-2MB/s per file, matching everything above) — moving the
*processing* to fast storage doesn't help if the *source data* still
has to be read off the slow drive first. This transfer was still in
progress (partial) as of this writing; the region-pack-count
optimization attempt (above) didn't meaningfully speed it up either.

**A genuinely fast path, found by inspection rather than
optimization**: Hidenori noticed 10 Kyushu/Okinawa region-pack zips
(`Z010`-`Z019`, ~20.7GB total) sitting unmoved in `/Users/hfu/Downloads`
— manually downloaded there by the browser (on `aalto`'s **internal**
boot SSD, not the external HDD) and never relocated to `src/1z/` on the
slow volume. Transferring these directly to `slate` averaged
**6.57MB/s** (peaks past 10MB/s) — 3-10x the external-HDD rate, and,
unlike the region-pack-count experiment, this actually delivered the
expected speedup because it changed the *actual bottleneck* (source
disk) rather than a secondary factor (file count). **Lesson: check
for a fast-storage copy of the same data before assuming everything
must flow through whatever slow path it originally arrived by.**
Verified byte-identical (`ls -la` size comparison, all 10 files) before
deleting the `Downloads` copies.

Set up a separate `japan-geotiff-dem-kyushu` working copy on `slate`
(Justfile only — `extract`/`convert`/`sync` recipes copied over, no
full `git clone` needed for a scratch/test area; HTTPS clone failed
non-interactively with `could not read Username`, not worth fighting
for this use case) with an incremental loop (re-run `just extract 1
&& just convert 1` on a ~3 min cadence, idempotent either way) so
processing keeps pace automatically as more region packs land.

### `source-coop` CLI on a headless machine, and an OAuth loopback flow without a local browser

`slate` needed its own `aws`/`source-coop` setup to publish directly
(previously all publishing routed through `aalto`, the only machine
with these configured — see `mapterhorn-japan-bridge/CLAUDE.md`'s
repo×machine split, now partially superseded for this specific
purpose).

- `brew install source-cooperative/tap/source-coop` failed building
  from source: `slate`'s Command Line Tools don't support the current
  macOS version (`softwareupdate --list` only offered a full 3.8GB OS
  update + restart — too disruptive to do casually, not attempted).
  **Workaround**: `source-coop` is a small statically-ish-linked Rust
  binary; copied `aalto`'s already-built binary directly (both
  Apple Silicon, ran immediately with no missing-library issues.
  Valid general technique for simple CLI binaries when a source build
  is blocked by toolchain version mismatches on the target machine.
- `awscli` installed fine via Homebrew (bottled, no compile needed).
- `source-coop login` uses an **OAuth2 loopback/PKCE flow**: it starts
  a local callback HTTP server on `slate` (`--port`) and expects a
  browser to hit `auth.source.coop`, then redirect back to
  `127.0.0.1:<port>/callback` on the *same machine running the CLI*.
  With no local browser on a headless `slate`, used **SSH local port
  forwarding** instead of anything GUI-based (no VNC/Screen Sharing
  needed): `ssh -N -L 8484:localhost:8484 slate.local` from `aalto`,
  then `source-coop login --port 8484` on `slate` over a separate SSH
  session, then opened the resulting `auth.source.coop/oauth2/auth?...`
  URL in a browser on `aalto` — the forwarded tunnel routed the
  callback back to `slate` correctly. **Claude opened the URL but did
  not complete the login itself** — Hidenori authenticated in the
  browser directly, consistent with the standing rule that account
  authentication is a human-only step (`CLAUDE.md`'s Source
  Cooperative publishing section). **This same tunnel-plus-manual-login
  pattern was reused successfully on 2026-08-11 after the token's ~1hr
  TTL expired repeatedly — see that entry.**
- **Near-miss worth flagging**: re-running `source-coop login` with `-v`
  to see the auth URL also logged the live temporary AWS credentials in
  plaintext. Deleted the log immediately (short-lived token, low
  impact) — but this generalizes the existing `source-coop creds`
  warning to *any* verbose/debug flag on credential-handling CLIs, not
  just the obviously-named subcommand. Worth remembering next time
  `-v` gets reached for on any auth-adjacent tool. **Repeated
  successfully and safely on 2026-08-11**: the `-v` log was deleted
  immediately after confirming "Authentication successful," before any
  credential material could be read.
- Once authenticated, `~/.aws/config` on `slate` got the same
  `[profile source-coop]` block as `aalto` (`credential_process =
  source-coop creds`, `endpoint_url = https://data.source.coop`) —
  verified with `aws s3 ls s3://smartmaps/ --profile source-coop`
  (same safe verification pattern as always, never `source-coop
  creds` directly). `just sync 1` from `japan-geotiff-dem-kyushu`
  uploaded real converted output successfully.

### Current state (updated 2026-08-10, mid-session)

- Hokkaido: 46/46 downloaded (unchanged from 2026-08-09).
  Extract/convert backlog **partially processed on `aalto`
  historically** (whatever `dst/1` held as of the 2026-08-09 syncs),
  **now being finished on `slate`** instead — transfer of the
  remaining unconverted `src/1` content is in progress, bottlenecked
  by `aalto`'s degraded HDD read speed as described above. **This
  transfer never completed — see the 2026-08-11 entry: the drive
  failed entirely before it finished, and none of the raw region-pack
  zips made it to `slate` via this path.**
- Kyushu/Okinawa: all 25 parts downloaded (Hidenori finished today).
  Parts `Z001`-`Z009` were extracted on `aalto` before the migration
  (mesh zips held aside from Hokkaido's `src/1` by a sweeper script,
  now cleaned up — see `mapterhorn-japan-bridge` HANDOVER.md's
  2026-08-09 entries). Parts `Z010`-`Z019` fast-tracked to `slate` via
  the `Downloads`-folder shortcut above and are being
  extracted+converted+synced there incrementally. Parts `Z020`-`Z025`
  not yet handled — check whether they're on `aalto`'s external HDD
  (slow path) or reachable via a similar internal-disk shortcut before
  assuming the slow path.
- `slate` now has its own working `source-coop`/`aws` setup
  (`~/.aws/config` profile `source-coop`) and can publish directly —
  no longer strictly dependent on routing through `aalto` for this
  repo's own `sync`/`docs` steps, though `aalto` remains the
  originally-configured machine and nothing here has been migrated
  back off it. **Superseded 2026-08-11: `slate` is now the sole
  machine for this repo going forward, see that entry.**
- `quadrans/1/` still not run (unchanged, still not worth it per D3).

### Lessons learned (2026-08-10)

1. **A "slow" external HDD can get *much* worse under concurrent
   load, not just proportionally worse** — isolate one process on
   troubled storage before assuming a fix didn't work; don't stack
   unzip+convert+delete+background-poller on the same marginal drive
   and expect any of them to make sense of the results.
2. **Single-file `stat` succeeding while directory/glob enumeration
   hangs is a useful, cheap diagnostic** to distinguish "this specific
   operation pattern is slow" from "the disk is actually dead."
3. **Measure I/O optimization hypotheses instead of trusting
   plausible reasoning** — fewer/larger files seemed obviously better
   for a seek-bound drive; it made no measurable difference here
   because the real limit was sustained bandwidth, not seek count.
4. **Moving to fast storage is not automatically a full fix** if the
   *source* data still has to be read off the slow drive to get there
   — the win only fully materializes once both ends of a transfer are
   fast. Always check whether a fast-storage copy of the needed data
   already exists (e.g. a browser's default download location) before
   assuming a slow-drive read is unavoidable.
5. **colima needs an explicit `--mount` for any volume outside its
   default scope** — the failure mode (empty directory, no error) is
   easy to misattribute to application code rather than infra config.
6. **A stray `credsStore` entry in `~/.docker/config.json` from a
   previous, even incomplete, Docker Desktop install silently breaks
   `docker pull`/`run`** on a fresh colima setup on the same machine.
7. **Compiled CLI binaries can often be copied between same-architecture
   Macs** to sidestep a source-build failure from an outdated toolchain,
   without needing a disruptive OS/CLT upgrade.
8. **Headless OAuth loopback logins work via SSH local port forwarding**
   (`ssh -L`) — no remote desktop / screen sharing required, and this
   generalizes to any CLI tool using the same "local callback server +
   browser redirect" pattern.
9. **Verbose/debug flags on credential-handling tools are a secret-leak
   risk in their own right**, separate from and in addition to whatever
   the tool's dedicated "print my credentials" subcommand does — this
   project's existing rule about `source-coop creds` should be read as
   covering `-v`/`--verbose` on *any* subcommand too, not just the one
   explicitly named.

### Blocked on Hidenori (2026-08-10)

- Kyushu/Okinawa parts `Z020`-`Z025`: confirm location (internal disk
  shortcut vs. `aalto`'s external HDD) before choosing a transfer path.
  **Resolved 2026-08-11: moot, see that entry — `aalto`'s HDD failed
  before this could be acted on; those parts are lost and Hokkaido is
  frozen rather than pursued further via this path.**
- Decision, not yet made: replace `aalto`'s external HDD, given today
  demonstrated it's no longer adequate for this workload (see the
  hardware discussion in `mapterhorn-japan-bridge`'s own session log).
  **Decided 2026-08-11: moot — the drive failed outright rather than
  being merely inadequate; retiring it, not replacing it.**

## 2026-08-11: `aalto`'s external HDD failed outright; Hokkaido frozen, Kyushu/Okinawa-only going forward; `slate` becomes this repo's sole machine

Continuing directly from 2026-08-10's in-progress `aalto`→`slate`
transfer of Hokkaido's remaining raw data. That transfer never
completed.

### The drive failure

`aalto`'s external HDD (the same drive flagged as severely degraded on
2026-08-10) went from "very slow" to **effectively unreadable**
during this session, confirmed through an extensive, escalating
troubleshooting sequence — full technical detail lives in
`mapterhorn-japan-bridge`'s own `HANDOVER.md`/`DECISIONS.md` for this
date, this is the summary relevant to this repo:

- A background rsync of the 46 remaining Hokkaido region-pack zips
  (and separately, the 15 not-yet-transferred Kyushu/Okinawa parts)
  hung mid-transfer for an extended period with zero byte progress,
  despite the process still technically running.
- Diagnostic steps tried, in order, **none of which restored real read
  throughput**: killing and restarting the transfer; `diskutil
  unmount`/`unmountDisk force` (both hung/timed out); a physical
  USB unplug/replug (metadata operations like `ls`/`stat` recovered,
  but bulk reads still hung indefinitely); `fsck_hfs -nl` via a live
  verification pass (came back clean — "The volume github appears to
  be OK" — Disk Utility's earlier First Aid pass had apparently
  already repaired real `invalid node structure` B-tree corruption,
  but this did not fix the underlying read hangs); a full system
  restart of `aalto`; a full power cycle of the drive itself. **A
  61-file rescue-copy attempt** (per-file timeout, skip-on-stuck,
  targeting the 46 missing Hokkaido zips + 15 missing Kyushu/Okinawa
  zips) recovered **0 of 61 files** — the first few attempts got real
  `Input/output error` responses (the drive actively failing reads),
  and every file after that failed even a `stat()` call, indicating
  the drive degraded further simply from being under sustained access
  load during the rescue attempt itself.
- Working hypothesis, offered by Hidenori and consistent with the
  symptom progression: this was a ~2019-vintage backup HDD, spun up
  for the first time in roughly 7 years for this project. A long-
  dormant mechanical drive degrading under its first sustained real
  load in years is a plausible, almost textbook failure mode — treated
  as a learning example for this project's own documentation rather
  than a mystery to keep chasing.

**Consequence: the 46 Hokkaido region-pack zips and the 15
not-yet-transferred Kyushu/Okinawa region-pack zips (`Z001`-`Z009`,
`Z020`-`Z025`) are lost.** None of them had reached `slate` (the
2026-08-10 transfer never finished). The 10 Kyushu/Okinawa parts
(`Z010`-`Z019`) that took the `Downloads`-folder fast path on
2026-08-09/10 are unaffected — they already live on `slate`.

### Recovery decision (Hidenori, 2026-08-11)

Rather than pursue further data-rescue attempts against the failed
drive (explicitly declined — not worth the risk or the time), or
immediately re-download all 61 missing region-pack zips from GSI's
portal:

- **Hokkaido is frozen** — deliberately set aside, not pursued this
  round. (Hidenori's own framing: "足利尊氏の九州行きのようなもの" — a
  deliberate, temporary strategic narrowing of scope, not an
  abandonment.) `jphokkaidodem1` in `hfu/mapterhorn`'s
  `source-catalog/` remains exactly as it was (stale `file_list.txt`,
  never run through aggregation) — do not resume it without a fresh
  decision to do so.
- **Kyushu/Okinawa is the sole focus going forward.** The 10 already-
  landed region packs (`Z010`-`Z019`) are enough to build real,
  if partial, bridge coverage — see `mapterhorn-japan-bridge`'s own
  `HANDOVER.md` for the `jpkyushutest1`/`jpkyushutest5m`/
  `jpkyushutest10m` source-catalog entries built from this.
  Best-effort framing: pursue Kyushu/Okinawa as far as it goes with
  available time, without a hard deadline commitment.
- If the remaining 15 Kyushu/Okinawa region-pack zips are wanted
  later, they would need re-downloading from GSI by hand — not
  attempted this round.

### `slate` becomes this repo's sole machine; `aalto`'s copy is being retired

Given the drive failure, the "which machine is canonical" question
`DECISIONS.md` D11 (in `mapterhorn-japan-bridge`'s own log) left open
is now settled by circumstance rather than choice: **`slate` is the
only machine with a live, working copy of this project's data.**
`aalto`'s copy — both the raw external-HDD data and, it turns out,
this **repo's own git history past 2026-08-08** — was never pushed to
GitHub and is now unrecoverable from that machine.

- **Re-authenticated `gh` on `slate`** (the existing token had
  expired): `gh auth login --hostname github.com --git-protocol https
  --web` produces a device code + `https://github.com/login/device`
  URL — no SSH-tunnel/loopback trickery needed here, unlike
  `source-coop login`'s OAuth flow, since `gh`'s device-code flow
  doesn't require a local callback server. Hidenori completed the
  authorization himself in his own browser, same human-only-auth
  convention as always.
- **Cloned a fresh, proper `git clone` of `optgeo/japan-geotiff-dem`
  onto `slate`** at `/Volumes/Migrate-2025-04/github/japan-geotiff-dem-repo`
  — this repo's actual git history only goes up to `0df1cc2` (2026-08-08),
  since nothing from 2026-08-09/2026-08-10 was ever pushed. The
  `japan-geotiff-dem`/`japan-geotiff-dem-kyushu` working directories
  already on `slate` (used throughout 2026-08-10) were Justfile-only,
  never real git clones (an earlier HTTPS clone attempt failed
  non-interactively with `could not read Username`, not fixed at the
  time) — `gh repo clone` sidesteps that by using the now-authenticated
  `gh` CLI instead of a bare `git clone` over HTTPS.
- **This 2026-08-09 entry above is a reconstruction, not a recovery**:
  the original 2026-08-09 session log was never committed anywhere and
  is genuinely lost. What's written there was assembled from
  cross-references in `mapterhorn-japan-bridge`'s own `HANDOVER.md`
  (read in full this session, before the drive failed) — the 2026-08-10
  entry above it, by contrast, **is** a faithful, complete recovery,
  since that file was read here in full earlier in this same session,
  while `aalto`'s drive was still (barely) readable.
- **Not yet done**: migrating the live `japan-geotiff-dem-kyushu`
  working directory's actual data (`src/1z`, `src/1`, `dst/1` — real,
  in-progress pipeline output, currently mid-run) into this newly
  git-tracked clone. The git repo's own `.gitignore` already excludes
  `*.zip`/`*.tif`/`*.vrt`/`*.txt`, so the data directories can live
  inside the git-tracked path without ever being tracked by git — but
  moving them safely while the extract/convert/sync loop is actively
  running needs a deliberate pause-move-resume, not done yet. Until
  that happens, `japan-geotiff-dem-repo` (git-tracked) and
  `japan-geotiff-dem-kyushu` (the live working directory) are still
  two separate paths on `slate`.

### Next steps

- [ ] Migrate `japan-geotiff-dem-kyushu`'s live `src`/`dst` data into
      `japan-geotiff-dem-repo` (the new git-tracked clone), pausing the
      extract/convert/sync loop briefly to do it safely, then point the
      loop at the new location and retire the old Justfile-only
      directory name.
- [ ] Once the working copy and git repo are unified on `slate`, this
      repo's `CLAUDE.md` should describe `slate` as the sole machine —
      done as part of this same 2026-08-11 update, see `CLAUDE.md`.
- [ ] `aalto`'s own copy of this repo (and the failed external HDD
      itself) can be considered safe to erase/disconnect once the
      `slate` migration above is confirmed complete — not yet acted on.
- [ ] If Hokkaido is ever resumed, it starts from zero on the raw-data
      side (all 46 region-pack zips need re-downloading from GSI) —
      `jphokkaidodem1`'s stale `file_list.txt` in `hfu/mapterhorn` can
      stay as-is until that decision is made.
- [x] Kyushu/Okinawa's remaining 15 region-pack zips (`Z001`-`Z009`,
      `Z020`-`Z025`) would need re-downloading from GSI if ever wanted
      — best-effort, no deadline. **In progress, see same-day follow-up
      entry below.**

## 2026-08-11 (same day, follow-up): repo consolidation confirmed healthy; `aalto`'s drive declared a disposal case, not a repair case; first real `slate`-native sync published; remaining-15 region-pack recovery plan started

Continuing directly from the morning's recovery commit (`c8cce4`/
`d92c811` after this entry's own README update). Hidenori asked
several practical follow-ups in sequence; recorded here together since
they're all short.

- **`__japan-geotiff-dem` — a leftover fragment, marked for deletion,
  not removed yet.** Separately from the `japan-geotiff-dem-kyushu`
  consolidation (done in the morning's entry), a *third*, older
  Justfile-only directory turned out to still exist on `slate`
  (`/Volumes/Migrate-2025-04/github/japan-geotiff-dem`, distinct from
  both `japan-geotiff-dem-kyushu` and the new git-tracked
  `japan-geotiff-dem-repo`) — a leftover from the 2026-08-10 in-flight
  `aalto`→`slate` Hokkaido transfer that never finished. It holds
  ~1.2GB of real, valid, but low-value data: one complete Hokkaido
  region-pack zip (`Z001`) plus a handful of already-converted
  `20250507`-vintage (pre-refresh) meshes from mesh blocks
  `6239`/`6240`. Since Hokkaido is frozen (this entry's own D12), this
  isn't worth integrating anywhere — renamed to
  `__japan-geotiff-dem` (leading double-underscore, this project's
  ad hoc "safe to delete" signal) rather than deleted outright, in
  case it's ever useful as a small head start if Hokkaido resumes.
- **`aalto`'s external HDD: disposal, not repair, is the right call.**
  Talked through explicitly with Hidenori rather than assumed: the
  data lost with the drive (46 Hokkaido + 15 Kyushu/Okinawa raw
  region-pack zips) is public GSI data, re-downloadable in principle,
  so paying for professional data recovery isn't worth it for
  non-unique data. Separately, the drive's failure mode (real I/O
  errors and hangs surviving unmount/replug/`fsck_hfs`/a full system
  restart/a full drive power-cycle, worsening further under the
  rescue-script's own read load) is consistent with genuine mechanical/
  electrical degradation, not just a wedged filesystem — reusing it for
  *any* future storage role would carry the same risk. Hidenori's own
  framing: a ~2019 backup drive, spun up for sustained real load for
  the first time in ~7 years, failing exactly as an aged HDD does under
  those conditions. Physical destruction before disposal (given the
  drive's original backup role may hold unrelated old personal data)
  is Hidenori's own call, not something this project needed to weigh
  in further on.
- **Kyushu/Okinawa `Z010`-`Z019` integrity, explicitly re-verified**
  (Hidenori asked directly, given how much has gone wrong with storage
  today): all 10 surviving region-pack zips in
  `japan-geotiff-dem-repo/src/1z/` pass `unzip -tq` (full CRC check of
  every compressed entry, not just the archive's central directory) —
  zero errors. Downstream counts also check out: 215 extracted mesh
  zips, 14,116 converted GeoTIFFs, both matching the running tallies
  from before the drive failure (i.e. nothing was silently lost in the
  `japan-geotiff-dem-kyushu` → `japan-geotiff-dem-repo` directory
  move). 3 random `dst/1` GeoTIFFs spot-checked via `gdalinfo` — all
  valid GTiff, correct 1125×750 raster size, correct CRS. **Conclusion:
  the 10 surviving region-packs' data is fully healthy** — today's
  drive failure claimed the *un-transferred* remainder, not anything
  already on `slate`.
- **Recovery plan for the missing 15 region-packs, started.** Same
  proven fast path as `Z010`-`Z019` originally used: Hidenori downloads
  each part from GSI's portal into `aalto`'s `~/Downloads` (internal
  SSD — the *only* viable source now that the external HDD is gone
  entirely, not just slow), Claude watches for them and transfers to
  `slate`'s canonical `src/1z/` (now
  `japan-geotiff-dem-repo/src/1z/`, not the old
  `japan-geotiff-dem-kyushu` path). Exact numbers needed, confirmed
  against what's actually on `slate` right now (not assumed from
  memory): **`Z001`-`Z009` and `Z020`-`Z025`, 15 of 25 total** —
  `Z010`-`Z019` already present. Hidenori began downloading `Z020`-
  `Z025` this session; watch `aalto`'s `~/Downloads` for
  `FG-GML-kyushu_okinawa-DEM1-*-Z0*.zip`-pattern files and relay them
  as they land, same as the original 2026-08-09/10 fast path.
- **First real `slate`-native `source-coop` publish of this recovery.**
  Re-logged-in (`source-coop login --port 8484` over the same SSH
  tunnel pattern as the morning's `gh` recovery — tunnel reused from
  earlier in the day rather than rebuilt). `just sync 1` published
  the full local `dst/1` (14,116 files, `--size-only` incremental) —
  spot-checked 5 random files afterward directly against S3, all
  present with matching byte sizes (4 already live since the original
  2026-05-28 upload, 1 a genuinely new 2026-05-22-vintage mesh from
  today's Kyushu/Okinawa work). **`source-coop login`'s session token
  keeps expiring on roughly a 1-hour cadence** (matches the `~1hr
  expiry` already noted in the `Expiration` field back on
  2026-08-10) — the unattended `extract`/`convert`/`sync` loop's
  `sync` step will keep failing harmlessly between manual re-logins;
  this is expected, not a bug, and doesn't block extract/convert.
  `source-coop/README.md`'s Changelog got its first real entry since
  2026-05-28 (1m tier, 10 of 25 Kyushu/Okinawa region-packs, 1,829
  newer-survey meshes) — published via `just docs`, committed as
  `d92c811`.

### Current state (updated 2026-08-11, this entry)

- `git`: `japan-geotiff-dem-repo` on `slate` is the sole, canonical,
  fully git-tracked working copy — `origin/main` at `d92c811`. Both
  `japan-geotiff-dem-kyushu` (Justfile-only, superseded, deleted) and
  `__japan-geotiff-dem` (Justfile-only, ~1.2GB of frozen-Hokkaido
  fragments, marked for deletion) are gone or marked gone; only
  `japan-geotiff-dem-repo` remains active.
- Kyushu/Okinawa: 10 of 25 region-packs (`Z010`-`Z019`) verified
  healthy end to end (raw zip → extracted mesh → converted GeoTIFF →
  published to S3). 15 remain missing; recovery via the
  `Downloads`-folder relay is underway.
- The unattended `extract`/`convert`/`sync` loop (`nohup`+`disown`'d,
  pid changes each restart — check `ps aux | grep "while true"` on
  `slate` rather than trusting a specific pid from an old entry) has
  nothing new to do on `extract`/`convert` until more region-packs
  land; `sync` will keep intermittently failing on credential expiry
  until the next manual re-login, harmlessly.
- `hfu/mapterhorn`'s `jpkyushutest1`/`5m`/`10m` downloads (a separate
  repo, see `mapterhorn-japan-bridge`'s own `HANDOVER.md`) continue in
  the background on `slate`, independent of this repo's own pipeline —
  check that repo's docs for current progress/ETA rather than assuming
  it's covered here.

### Next steps

- [ ] Keep relaying `Z001`-`Z009`/`Z020`-`Z025` from `aalto`'s
      `~/Downloads` to `slate`'s `japan-geotiff-dem-repo/src/1z/` as
      Hidenori downloads them from GSI.
- [ ] Re-run `source-coop login` periodically (roughly hourly) whenever
      active work needs a working `sync` — not urgent between sessions,
      `extract`/`convert` don't need it.
- [ ] Once more region-packs land, re-run `extract`→`convert`→`sync`
      (the unattended loop picks this up automatically) and consider
      another `source-coop/README.md` Changelog entry once a
      meaningfully larger batch has actually published.
- [ ] Delete `__japan-geotiff-dem` once Hokkaido is confirmed to stay
      frozen for good, or fold it back in if Hokkaido is ever resumed
      — not urgent either way, 1.2GB is negligible against 1.3TB free.
- [ ] Keep watching for whether upstream `mapterhorn/mapterhorn`'s own
      `jpdem1a` picks up the July 2026 GSI update — still this whole
      effort's eventual retirement condition (see
      `mapterhorn-japan-bridge`'s own `CLAUDE.md`).

## 2026-08-12: Kyushu/Okinawa raw acquisition complete (25/25); `__japan-geotiff-dem` deleted; Hokkaido re-download started, batched instead of relayed live

**All 25 Kyushu/Okinawa region-pack zips (`Z001`-`Z025`) are now on
`slate`**, each individually verified twice (`unzip -tq` full CRC
check both right after download on `aalto` and again after landing in
`src/1z/` on `slate`, plus a byte-size comparison in between) before
the `aalto`-side copy was deleted. The `Z001`-`Z009`/`Z020`-`Z025`
recovery relay (flagged as in-progress in the prior entry) is done.
`extract`/`convert`/`sync` continue to catch up unattended; `sync`
keeps failing harmlessly on hourly `source-coop login` token expiry,
as expected.

**`__japan-geotiff-dem` (the ~1.2GB leftover Hokkaido fragment, marked
for deletion since the prior entry) was deleted** — Hidenori confirmed
Hokkaido is being redone fully from scratch, making the old partial
fragment (one `Z001` zip + a handful of pre-refresh `20250507`-vintage
meshes) obsolete rather than a useful head start.

**Hokkaido re-download started** (Hidenori, via GSI's portal into
`aalto`'s `~/Downloads`, same fast path as Kyushu/Okinawa) — full
from-zero redo of all 46 parts, not a resume of the old partial state.
`Z001`-`Z003` landed, `Z004` in progress as of this entry. **Decided to
batch-accumulate on `aalto` rather than relay each part to `slate`
immediately**: `aalto`'s internal SSD has 212GB free (460GB total,
223GB used) — comfortably enough to hold all 46 parts (~2GB each,
~92GB total) at once — and processing one-by-one immediately/session
overhead isn't worth it given 46 parts vs. Kyushu/Okinawa's 25.
Relay will happen in a batched pass once tokens allow.

**Incident, not caused by this repo's own pipeline**: an unrelated
`grep` invocation from earlier ad hoc research (a "does the Taiwanese
hardware angle appear anywhere in these repos' docs" search) was
accidentally run without an `--include` filter, so it recursed into
`dst/1/`'s tens of thousands of binary `.tif` files — pinned at ~100%
CPU on `slate` for 9+ hours before being noticed and killed. Not a
sign of this repo's own extract/convert/sync loop misbehaving; a
reminder to always scope `grep`/`find` away from binary data
directories, and to check `ps aux` before assuming sustained load is
productive pipeline work.

**Storage/time strategy for a future full-Japan run — captured as a
TODO, not started** (Hidenori's own framing, deliberately deferred
given limited session budget): track which pack/zip/GeoTIFF has been
durably published to Source Cooperative in a lightweight metadata
store (CSV or a simple KVP file), so intermediate `src/{res}z`,
`src/{res}`, and even `dst/{res}` files can be deleted aggressively
once superseded by the S3 copy, rather than kept as a second local
copy indefinitely. Needs, before attempting: a concrete estimate of
how much storage a full-Japan (or Hokkaido+Kyushu/Okinawa) run would
actually need, and whether `slate`'s disk covers it — not yet
estimated for this repo's own `src`/`dst` footprint at that scale (see
`mapterhorn-japan-bridge`'s own `HANDOVER.md` for the parallel
metatile-package angle on the PMTiles side).

### Next steps

- [ ] Batch-relay Hokkaido's accumulating `aalto`-side zips to
      `slate`'s `src/1z/` once there's budget for it — verify (CRC +
      size), transfer, re-verify, delete `aalto`-side, same as always,
      just done as a batch pass instead of per-file.
- [ ] Once Kyushu/Okinawa's `extract`/`convert`/`sync` fully catches
      up on all 25 packs, consider another `source-coop/README.md`
      Changelog entry (full 1m Kyushu/Okinawa coverage, not partial).
- [ ] Re-run `source-coop login` periodically (roughly hourly) whenever
      active work needs a working `sync`.
- [ ] Work out the metadata-driven intermediate-file-deletion scheme
      above before Hokkaido's `convert` stage starts producing a
      second national-scale `dst/1` footprint on top of Kyushu/
      Okinawa's.

## 2026-08-13/14: Kyushu/Okinawa GeoTIFF fully synced; extract/convert/sync loop deliberately stopped; 10-day unattended gap starting

**All 25 Kyushu/Okinawa region-packs' GeoTIFFs are now fully synced to
Source Cooperative** — the last incremental `sync` (after a fresh
`source-coop login`) uploaded the final ~1,000-file delta (newer
2026-survey-date meshes not already covered by the original national
baseline or the prior partial sync). `extract`/`convert` have nothing
new to do; `dst/1` holds 34,522 GeoTIFFs.

**The unattended `extract`/`convert`/`sync` while-loop was
deliberately killed** (2026-08-13 ~01:27 JST, `kill` on the loop's
`bash -c 'while true; ...'` parent PID) — not a failure, a deliberate
resource-contention fix. It was re-scanning all 25 zips and
re-validating 34,500+ `.tif` files every 3 minutes for zero new work,
while competing for CPU/memory/disk-I/O with the concurrent
`hfu-mapterhorn` PMTiles `aggregation_run` (see
`mapterhorn-japan-bridge`'s own `HANDOVER.md` for the full incident —
a stalled `merge_source()` step visibly resumed within hours of
stopping this loop). Safe and fully resumable any time (same
one-liner); nothing was lost, since `extract`/`convert` are idempotent
and `sync`'s only pending work was already completed before the loop
was stopped.

**Hokkaido download is nearly complete on `aalto`, deliberately not
relayed** — Hidenori has been downloading all 46 region-packs from
GSI into `aalto`'s `~/Downloads`, batching there rather than relaying
per-file (per the earlier agreed sequencing: relay happens only after
the current Kyushu/Okinawa PMTiles pipeline completes and the
`hfu/mapterhorn` upstream merge is done — see
`mapterhorn-japan-bridge`'s own `HANDOVER.md`). `aalto` has 189GB+
free, comfortably enough to hold all 46 parts (~92GB) at once.

**10-day unattended gap starting**: Hidenori is stepping away from the
console (this session) for about 10 days, starting a few hours after
this entry. Separately, `aalto` itself is being disconnected from the
network for the same ~10-day window (timing coincides). **Explicit
decision: Hokkaido stays completely untouched during this gap** — no
relay to `slate`, no `extract`/`convert`/`sync`, nothing — even though
the raw downloads will likely be sitting complete in `aalto`'s
`~/Downloads` well before the gap ends. Do not restart the
`extract`/`convert`/`sync` loop either, unless there's a specific
reason to (e.g. a fresh Kyushu/Okinawa delta needs publishing) — it's
fine left stopped.

### Next steps

- [ ] Once resumed (after the ~10-day gap, or sooner if Hidenori
      returns early): check `mapterhorn-japan-bridge`'s own
      `HANDOVER.md` for whether the Kyushu/Okinawa PMTiles pipeline
      (`aggregation_run`/`downsampling_run`/`bundle.py`) has finished
      — that gates the `hfu/mapterhorn` upstream merge, which itself
      gates the Hokkaido relay (see that repo's own sequencing notes).
- [ ] Do not touch Hokkaido (relay or processing) without confirming
      the above sequence has actually progressed — do not assume it's
      safe just because 10 days have passed.
- [ ] If restarting `extract`/`convert`/`sync`, use the same one-liner
      documented above; check `mapterhorn-japan-bridge`'s pipeline
      isn't mid-run first, to avoid repeating the same resource
      contention this entry describes.

## 2026-08-18: JCI 2026-09 kickoff — latest/obsolete filelists (D13), delta-skip conversion (D14), aalto-direct pack processing (D15); Hokkaido underway

**Context**: Oliver Wipfli (Mapterhorn lead) asked whether fresh GSI
1m DEM data could reach Source Cooperative in the next few weeks,
ahead of Mapterhorn's own October update. This became "**JCI
2026-09**" (Mapterhorn Japan Continuous Improvement), tracked as a
single living issue, `unopengis/7#978` — not a new repo; this repo
remains the pipeline. Hidenori replied (LinkedIn; see the issue for
the actual sent text) proposing **full national coverage by around
2026-09-10/15** as a question, not a firm commitment, and offering the
issue for Oliver to follow. All of the work below happened entirely
from `aalto`, without `slate` (unreachable 2026-08-14 until
2026-08-24) — see `DECISIONS.md` D13/D14/D15 for the full ADRs; this
entry is the narrative.

**D13 — `latest_file_list.txt.gz` / `obsolete_file_list.txt.gz`**:
resolves D9's old flagged gap (superseded meshes staying published
forever with no signal of which is current). Plain-text, one full URL
per line, gzipped, one pair per resolution prefix (`{res}/latest_file_
list.txt.gz`, `{res}/obsolete_file_list.txt.gz`). Generated and
published for real against all three resolutions: `1/` (274,724
files → 270,778 latest / 3,946 obsolete), `5/` (378,618, all latest),
`10/` (4,981, all latest). Naming settled on `file_list` (underscore),
matching `hfu-mapterhorn`'s existing convention, after catching the
inconsistent `filelist` spelling and fixing it everywhere (code,
`source-coop/README.md`, the already-uploaded S3 objects, the
`unopengis/7#978` issue text). **Correction caught the same day**: an
earlier claim that `data.source.coop` needs authentication was wrong —
a plain `urlopen()` 403 was Python's default User-Agent getting
blocked, not real access control; a browser-equivalent UA gets a plain
`200 OK`, no login needed. Fixed in `DECISIONS.md` D14 and the
`unopengis/7#978` thread.

**D14 — `scripts/skip_already_published.py`**: pre-filters
`src/{res}/*.zip` before `convert`, moving aside anything whose entire
content is already in `latest_file_list.txt.gz`, since `gmldem2tif.rb`'s
own `tif_valid?` only checks local `dst/{res}`, not S3. Verified twice:
first against two hand-built synthetic zips (one real published
filename, one fabricated), then — after Hidenori asked a sharp
question about whether the zip-inside-zip structure was actually being
opened correctly — against real Hokkaido data. That check surfaced a
real structural fact worth remembering: **`src/{res}/*.zip` (after
`extract`) is a GSI "collection" zip covering a broader area code
(e.g. `FG-GML-624076-DEM1A-20251107.zip`), containing up to ~100
individual mesh `.xml` files with independently-varying survey dates**
— not one zip per mesh. Both this script and `gmldem2tif.rb` already
open exactly one level correctly, so there was no real bug there, but
`process_pack.py`'s logged `mesh_count` turned out to actually be
counting collection-zips — renamed to `collection_zip_count`, and
`skip_already_published.py` now also reports true mesh-level counts.
Hand-verified 4 real mesh matches against the live bucket (one
confirmed as an actual S3 object, uploaded 2026-05-25 as part of the
original national baseline) before trusting the early 100%-skip
results.

**D15 — process pack-by-pack directly on `aalto`**: with `slate`
unreachable through 2026-08-24 and JCI's Sept target live, decided not
to wait. Verified the premise first: `aalto`'s internal SSD measured
~1.68GB/s write / ~1.94GB/s read, vs. `slate`'s external USB SSD's
known ~300MB/s ceiling — roughly 6x faster. Docker was installed on
`aalto` but not running (`open -a Docker` started it); `gmldem2tif:latest`
was already built locally (2026-05-26) and confirmed same-day to
already reflect `unopengis/gmldem2tif`'s latest commit (2025-12-07, no
repo changes since) — no rebuild needed, smoke-tested (Ruby + GDAL
binding both load fine). Cleared ~11GB of unrelated stopped-project
Docker images (`senrigan`, `poc-cng-cog-tile`, `kitavolca`,
`mgrs-pmtiles-toolchain`, `vt-optimizer-rs`, `mzellou/micmac` — all
Exited 3 months, confirmed with Hidenori before deleting) plus build
cache, since `aalto` only had 96GB free against Hokkaido's 87GB of raw
packs alone. `scripts/process_pack.py {res} {zone} {pack_zip_path}`
does one pack fully in isolation (asserts `src/{res}z`, `src/{res}`,
`src/{res}-skip`, `dst/{res}` are all empty first) — `extract` →
`skip-published` → `convert` → `sync` → verify every produced `.tif`
against S3 by byte size → delete local data only if verification
passed. Every run appends to `logs/aalto_pack_log.jsonl`, committed to
this repo (linked from `unopengis/7#978`, not duplicated there) for
traceability. Two bugs found and fixed on the first real run: `dir_empty()`
didn't ignore the repo's own `.gitkeep` placeholders (false "not
empty"); credentials expire hourly same as always, needs a fresh
`source-coop login` (trivial on `aalto` — real desktop, no SSH tunnel
needed unlike `slate`).

**Decided**: packs processed this way must **not** also be relayed to
`slate`'s `src/1z/` later — they're already fully published. Keep
track of which Zones `aalto` has fully finished so `slate` (once back
2026-08-24) doesn't redundantly grab the same region.

**Hokkaido progress** (processing in order, Z001→Z046, per Hidenori's
explicit preference over cherry-picking a more "interesting" pack to
prove the implementation): `Z001`-`Z024` all came back 100% already-
published (unchanged since the 2026-05-25 national baseline) — 24
packs, safely skipped and deleted, zero new uploads needed. **`Z025`
was the first pack with real new content**: 1,283 meshes total, 85
new — full pipeline exercised for real (Docker/GDAL convert → `aws s3
sync` → per-file S3 size verification → local delete), all succeeded,
reported to `unopengis/7#978`. Remaining `Z026`-`Z046` in progress as
of this entry — check `logs/aalto_pack_log.jsonl`'s tail for exact
current position rather than assuming.

**Other Zones staged on `aalto`, not yet run through D15** (only
Hokkaido is being worked right now): Shikoku (17/17 packs, downloaded
+ CRC-verified) and Chugoku (target 23 packs per Hidenori, downloading
steadily — check `~/Downloads` for current count). Process these the
same way once Hokkaido's `Z046` is done.

### Next steps

- [ ] Finish Hokkaido `Z026`-`Z046` via `process_pack.py`, committing
      `logs/aalto_pack_log.jsonl` periodically.
- [ ] Then Shikoku (17 packs), then Chugoku (once its download
      finishes) — same `process_pack.py` flow, zone name changes only.
- [ ] Do **not** relay any Zone `aalto` has already fully processed to
      `slate`'s `src/1z/` once reconnected 2026-08-24 — check this
      file's own progress notes / `logs/aalto_pack_log.jsonl` first.
- [ ] Once `slate` reconnects: check `mapterhorn-japan-bridge`'s own
      `HANDOVER.md` for whatever happened to the Kyushu/Okinawa
      PMTiles prototype (`aggregation_run`/`downsampling_run`/
      `bundle.py`) during the gap — that side of the project hasn't
      been touched since 2026-08-14 and is unrelated to the JCI/D15
      work above.
- [ ] Keep `unopengis/7#978` current as Zones complete — Oliver may be
      watching it.

## 2026-08-18 (same day, follow-up): Chugoku verified complete, Kinki downloading, Oliver's reply, credential-expiry incidents

Quick addendum to the same-day entry above — this is a natural
`/clear` point, so capturing state precisely rather than letting it
drift.

**Hokkaido**: 30/46 packs done as of this entry (`Z001`-`Z030`).
`Z001`-`Z024` all already-published (2026-05-25 baseline). From
`Z025` on, real new content started appearing — several packs (`Z025`
85 new, `Z026` 399, `Z028` 1,038, `Z029` 1,344 meshes) converted +
uploaded + verified successfully. **Two `source-coop` credential-
expiry incidents this session, both now understood and fixed**:
`Z027` produced a false "607/937 files missing" verify failure (fixed
per-file `aws s3 ls` calls conflating auth errors with genuine
absence — see `DECISIONS.md` D15's follow-up); `Z030`'s `sync` itself
failed cleanly on expired credentials (the fix from the `Z027`
incident meant this one failed loudly and correctly instead of
silently corrupting anything) — re-logged in, re-ran `just sync 1`
manually, verified via the new bulk-listing method, completed. Neither
incident lost or corrupted any data; both are documented as real
incidents in `DECISIONS.md` D15 because a differently-shaped version
of either bug could have. **16 packs remain** (`Z031`-`Z046`).

**Chugoku**: all 23 packs (Hidenori's own corrected count, not the
~19 area-based estimate from earlier) downloaded and CRC-verified
clean on `aalto`. Not yet run through `process_pack.py` — Hokkaido is
being finished first, in order, per Hidenori's stated preference.

**Kinki (Zone 8)**: 24 packs total (Hidenori's real count); download
just started.

**Oliver Wipfli replied** (see `unopengis/7#978` for full text): 9/15
works fine on his end for Mapterhorn's own ingestion; confirmed the
`latest`/`obsolete` filelist approach, and shared genuinely useful
practitioner context — Swisstopo does the same "new file per update"
approach we landed on, while LINZ updates files in place. Hidenori
sent a reply back noting the pipeline has actually sped up since (D14
skip-conversion + D15 aalto-direct processing working around `slate`
being unreachable) — see the issue for the sent text.

**Auth**: `source-coop` sessions expire roughly hourly, same as
always — expect to re-run `source-coop login` periodically (trivial
on `aalto`, real desktop, no SSH tunnel needed) whenever a `sync` or
verify step fails with a credentials-expired error.

### Next steps

- [ ] Finish Hokkaido `Z031`-`Z046`.
- [ ] Then Chugoku (23 packs, already verified, ready to go).
- [ ] Then Kinki once its download finishes (24 packs).
- [ ] Keep re-running `source-coop login` as needed — don't let an
      expired-credential failure get treated as "file genuinely
      missing" without checking (the `Z027` lesson).
- [ ] Do **not** relay any Zone `aalto` has already fully processed to
      `slate`'s `src/1z/` once it reconnects 2026-08-24.
- [ ] Keep `unopengis/7#978` current as Zones complete — Oliver is
      actively reading it.

## 2026-08-18 (continued, post-`/clear`): Hokkaido/Shikoku/Chugoku all complete; Kinki in progress; Tohoku download started; concurrency incident (D16); README improvements

Picked up exactly at the prior entry's resume prompt. `logs/
aalto_pack_log.jsonl` tail and `~/Downloads` confirmed the prior
session's state (Hokkaido at `Z030`, Chugoku/Kinki downloaded/
downloading) before resuming.

**Hokkaido finished: 46/46.** `Z031`-`Z046` processed one at a time.
`Z037` and `Z042` both hit the same hourly `source-coop`
credential-expiry pattern as `Z027`/`Z030` — both recovered manually
(re-login, resume from whichever stage failed, bulk-listing verify),
no data lost either time. 17 of 46 packs total carried real new
content; **10,577 new meshes** converted/uploaded/verified for
Hokkaido overall.

**Shikoku finished: 17/17, 988 new meshes.** Also hit one credential
expiry (`Z010`, at the `skip-published` stage's own `aws s3 cp` this
time, not `sync`/`verify` — same root cause, different call site).

**Real incident: `Z003` and `Z004` ran concurrently for about a
minute**, an operator (Claude) mistake — a shell command with a 30s
timeout returned control before printing output, and the *next* pack
was started without waiting for `Z003`'s actual completion
notification. Both instances shared `src/1z`/`src/1`/`dst/1` with no
locking between them; `extract` merged both packs' collection-zips
into one shared `src/1`, `dst/1` had 132 tifs from a mix of both
before it was caught. **Caught before `sync`** — neither instance had
uploaded anything yet, so no S3-side cleanup was needed. Both original
zips in `~/Downloads` were untouched and still CRC-clean (`process_pack.py`
copies rather than moves into `src/{res}z`). Recovery: killed both
processes, deleted the contaminated local intermediate state, re-ran
`Z003` then `Z004` serially from their still-intact Downloads copies.
Recorded as `DECISIONS.md` D16 — the standing rule now is: never start
the next `process_pack.py` run until the previous one's completion
notification has actually arrived, full stop, no exceptions for
"probably done by now."

**Chugoku finished: 23/23, 1,065 new meshes.** No incidents this time
— processed cleanly pack by pack, strictly serial per the new D16
discipline.

**`latest_file_list.txt.gz`/`obsolete_file_list.txt.gz` rebuilt twice
mid-Hokkaido**, at Hidenori's explicit request to run it in parallel
with pack processing rather than waiting for a Zone to fully finish
("不完全であっても file list を更新することは良いことだと思っている" —
even an incomplete file list is worth publishing). Confirmed safe to
run concurrently with `process_pack.py`: `just filelists` only touches
the live S3 listing plus two local files in the repo root, never
`src/{res}*`/`dst/{res}`. 1m tier ended this session at 283,973 files
(278,523 latest / 5,450 obsolete) as of the second rebuild, mid-way
through Hokkaido — further out of date now that Shikoku/Chugoku have
since landed, which is expected and fine per Hidenori's own framing
above; rebuild again next natural pause point.

**`source-coop/README.md` improved twice, both Hidenori's own
suggestions**:
1. Spelled out all 6 direct `latest`/`obsolete_file_list.txt.gz` URLs
   (10m/5m/1m × latest/obsolete) plus a `curl | gzcat` SYNOPSIS —
   Source Cooperative's own browse UI makes these tedious to find by
   clicking through.
2. Title changed from "Japan DEM (10m / 5m / 1m), as GeoTIFF" to
   "...as Cloud-Native GeoTIFF" — verified first against a live
   published file (`gdalinfo` over `/vsicurl/`): internally tiled
   (512×512 blocks on a 1125×750 mesh), ZSTD-compressed, genuinely
   usable via HTTP range reads. Deliberately "Cloud-Native" rather
   than the stricter "Cloud-Optimized" (COG) term, since this dataset
   has no overviews (Mapterhorn's own ingestion builds its own
   pyramid downstream, so overviews at the per-mesh source level would
   be redundant — confirmed by `quadrans_script.rb`'s explicit
   `COPY_SRC_OVERVIEWS=NO`). Both changes published via `just docs`
   immediately after editing.

**Kinki started, in progress**: `Z001`/`Z002` processed (`Z001` fully
already-published, `Z002` 100 new meshes), `Z003` running as of this
entry. 24 packs total; Hidenori finished downloading the bulk of them
during this session.

**Tohoku download started** (Hidenori, per his own message: "ダウン
ロードは東北に移る。一から順番でいいね？全体で34ある。" — starting
from `Z001`, sequential, per the established download-order
convention). 34 packs total, none processed yet.

**`unopengis/7#978` kept current throughout**: Zone table updated
three times (after Hokkaido finished, after Shikoku/Chugoku progress,
after Tohoku's download start), plus two comprehensive progress
comments (per-Zone pack/mesh tallies). Oliver has not replied further
on the issue itself this session — his earlier reply (documented in
the prior HANDOVER entry) was via LinkedIn, not posted to the issue.

**`CLAUDE.md`/`README.md`/`DECISIONS.md` brought up to date this
entry** (Hidenori asked for a general documentation pass): `CLAUDE.md`'s
"Current machine and scope" section rewritten (was describing the
2026-08-11 "Kyushu/Okinawa only, frozen Hokkaido" scope, now describes
JCI 2026-09's full-national push and the temporary `aalto`-direct
arrangement); both `CLAUDE.md` and root `README.md`'s pipeline-stage
lists updated to include `skip-published` and `filelists` (added by
D14/D13 but never added to either doc until now); `DECISIONS.md` D15's
status line updated to reflect three full Zones proven, not just the
first pack; D16 added for the concurrency incident.

### Current state (updated 2026-08-18, end of this entry — session paused here on Hidenori's instruction)

- Hokkaido: **complete**, 46/46, 10,577 new meshes.
- Shikoku: **complete**, 17/17, 988 new meshes.
- Chugoku: **complete**, 23/23, 1,065 new meshes.
- Kinki: **complete**, 24/24, 946 new meshes. One more credential
  expiry (`Z023`, same hourly pattern), recovered manually as usual.
- **Four Zones complete this session, 13,576 new meshes total.**
- Tohoku: download in progress, `Z001`-`Z008` or so landed as of this
  entry (Hidenori's own count), 34 packs total, **none processed yet
  — deliberately paused, see below.**
- `latest`/`obsolete` file lists rebuilt once more after Kinki
  finished: 1m tier now 285,259 files (279,005 latest / 6,254
  obsolete).
- `unopengis/7#978`'s Zone table and a closing progress comment are
  current as of this entry.

**Session paused here deliberately**: Hidenori's own call — Tohoku's
download hasn't caught up enough yet (34 packs, still arriving) to be
worth processing piecemeal, so stop after Kinki + the file list
rebuild rather than nibbling at a handful of Tohoku packs now. Resume
once more of Tohoku has landed — no fixed threshold given, use
judgment (or ask) when picking this back up.

### Next steps

- [ ] **Do not start processing Tohoku until Hidenori says to resume**
      — this session ended paused by his explicit instruction, not by
      running out of work.
- [ ] When resumed: process Tohoku as it downloads (`Z001`-`Z034`,
      sequential, strictly one `process_pack.py` invocation at a time
      per D16), then whatever Zone comes after.
- [ ] Rebuild `latest`/`obsolete` file lists again at the next natural
      pause point — Hidenori wants this done periodically, not just
      once at the very end.
- [ ] Keep re-running `source-coop login` as needed (hourly TTL,
      unchanged) — don't treat a credential error as data loss without
      checking first (the `Z027`/`Z037`/`Z042`/`Z010`/`Z023` pattern).
- [ ] **Never start a new `process_pack.py` run before the previous
      one's completion notification has actually arrived** (D16) — no
      exceptions, this is exactly how the `Z003`/`Z004` incident
      happened.
- [ ] Do **not** relay any Zone `aalto` has already fully processed to
      `slate`'s `src/1z/` once it reconnects 2026-08-24 — that's now
      Hokkaido, Shikoku, Chugoku, and Kinki.
- [ ] Keep `unopengis/7#978` current as Zones complete — Oliver is
      actively reading it.

## 2026-08-19 (continued, post-`/clear`): Tohoku finished, Hokuriku started; a parallel `slate` research thread (SSH restored, trial confirmed, `japan.pmtiles` rebuilt)

Picked up exactly at the prior entry's resume prompt: Kinki was
complete, Tohoku's download hadn't caught up, session was paused
deliberately. This entry covers a long continued session that
resumed Tohoku, finished it, started Hokuriku, and — in parallel, on
`slate` rather than `aalto` — did substantial unplanned investigation
work on the sibling `hfu/mapterhorn` / `mapterhorn-japan-bridge`
effort. That side has its own full narrative in
`mapterhorn-japan-bridge`'s own `HANDOVER.md` (three detailed entries
from this same session) — this entry only summarizes it for
cross-reference, since it happened concurrently with this repo's own
pipeline work and used some of the same background-task-monitoring
rhythm.

**Tohoku finished: 34/34, 18,426 new meshes** — the highest hit rate
of any zone this session (31 of 34 packs carried new content, vs.
much lower ratios for Hokkaido/Shikoku/Chugoku/Kinki), reflecting
active ongoing GSI survey work in this region. Incidents: the usual
hourly credential-expiry pattern (`Z001`/`Z020`/`Z028`, recovered
manually as always) plus one **new failure class** — `Z031` hit a
transient HTTP 520 from Cloudflare on a single `PutObject` call during
`sync`, which is *not* a credential problem and doesn't need
`source-coop login` — a plain retry of `just sync 1` resolved it
immediately. Worth remembering as a distinct pattern from the
credential-expiry one: check the actual error text before assuming
every `sync` failure needs a re-login.

Posted the consolidated Tohoku-complete report to `unopengis/7#978`
per Hidenori's explicit instruction ("東北全数が終わった時点でissueに
報告するように") — this zone got one comment at full completion
rather than the earlier per-Zone-completion cadence, since he
specifically flagged how much new data this one had.

**Hokuriku started**: order confirmed as 北陸→関東3→関東2→関東1→中部
(the five zones remaining after everything else this session
finished). 16 packs total, all downloaded before processing began.
4/16 done as of this entry (1,742 new meshes so far), `Z005` in
progress — check `~/Downloads` and `logs/aalto_pack_log.jsonl` on
resume rather than trusting this count if time has passed.

**Session running total**: 148 packs processed across six zones
(Hokkaido/Shikoku/Chugoku/Kinki/Tohoku complete, Hokuriku in
progress), **33,744 new meshes** converted/uploaded/verified via D15
this session alone.

### The parallel `slate` thread (full detail in `mapterhorn-japan-bridge`'s own HANDOVER.md)

Hidenori set up an SSH jump-host route from `aalto` to `slate` this
session (topology deliberately not detailed in this public repo,
same reasoning as `mapterhorn-japan-bridge`'s own redaction — ask
Hidenori or check `aalto`'s `~/.ssh/config`), restoring the ability to
inspect and drive `slate` directly for the first time since it went
unreachable 2026-08-14. This led to a long side-thread of real
findings, all recorded in detail in `mapterhorn-japan-bridge`'s own
`HANDOVER.md` (search for the 2026-08-19 entries):

- **The 2026-08-14 aggregation/downsampling/bundle trial was confirmed
  to have actually completed successfully** (1,119/1,119 aggregation,
  2,697/2,697 downsampling, `bundle.py 1` done) — it only *looked*
  stuck because `check_progress.py` has a real glob-pattern bug that
  always reports 0% regardless of true state.
- **`polygon-store` fast-storage relocation was investigated and its
  premise disproven**: a real `ogr2ogr -update -append` benchmark
  (matching the actual production command) showed only a ~10%
  difference between `slate`'s internal SSD and external USB SSD —
  storage speed is not the bottleneck for that workload, subprocess-
  spawn overhead is. Also found and fixed a real regression: GDAL
  3.13.3 (auto-upgraded via Homebrew, released 2026-08-13) rejects a
  duplicate `-append` flag that `source_polygonize.py` had always
  passed — fixed in `hfu/mapterhorn`.
- **`jpkyushutest1`'s `file_list.txt` regenerated** against
  `japan-geotiff-dem`'s current published state: 71,577 → 75,724
  positions. Confirmed (by direct JIS-mesh-code computation) that this
  source-catalog entry's mesh-code-range filter (3900-5199) has always
  covered not just Kyushu/Okinawa but all of Shikoku and western
  Chugoku too — confirmed **intentional** by Hidenori ("日本を一つの
  広域ソースとして扱い" — treating Japan as one broad-area source on
  purpose), not a bug. A download+bounds+polygonize pipeline for this
  expanded coverage was kicked off and is still running as of this
  entry (see `mapterhorn-japan-bridge`'s HANDOVER for live status).
- **`japan.pmtiles` was rebuilt successfully** after three earlier
  attempts crashed with ENOSPC. Root cause: the `pmtiles` Python
  library's `Writer` streams tile data into `tempfile.TemporaryFile()`
  before `finalize()`, and `tempfile` defaults to the small internal
  volume rather than wherever the script's own output lives — not a
  memory/swap problem as first suspected. Fix: `TMPDIR` pointed at the
  external volume, no code changes. Result: 789,984 tiles, ~70.7GB,
  verified non-corrupt (header's declared `tile_data_length` exactly
  matches the file's actual size). **Local only — not yet published**;
  Hidenori wants to verify it and upload to Source Cooperative next,
  after `/clear`.
- Also: killed 3 harmless but long-orphaned `colima start` zombie
  processes from 2026-08-10; reclaimed ~31GB on `slate`'s tight
  internal SSD (228GB total, was 55GB free, now 85GB) by deleting an
  abandoned Docker Desktop install's leftover container data plus
  assorted safe app/dev-tool caches; confirmed FileVault is enabled on
  `slate` (so a reboot without physical/GUI access would strand it —
  the pending macOS update stays deferred until physical access is
  available, expected around 2026-08-23 night).

None of this touched `japan-geotiff-dem`'s own pipeline or data —
purely parallel work on the sibling repos, using the same
background-task-monitoring rhythm as this repo's own Zone processing.

### Next steps

- [ ] Finish Hokuriku (`Z005`-`Z016` as of this entry).
- [ ] Then 関東3 (Kanto-3, Yamanashi/Nagano) → 関東2 → 関東1 → 中部, per
      the confirmed order.
- [ ] Rebuild `latest`/`obsolete` file lists at the next natural pause
      — still Hidenori's standing preference.
- [ ] Keep re-running `source-coop login` on credential-expiry errors
      (hourly TTL) — but check the actual error text first: a
      transient HTTP 520 (like `Z031`) needs a plain retry, not a
      re-login, and re-logging in for that class of error wastes a
      step without fixing anything.
- [ ] **Never start a new `process_pack.py` run before the previous
      one's completion notification has arrived** (D16) — unchanged.
- [ ] Do **not** relay any Zone `aalto` has already fully processed to
      `slate`'s `src/1z/` once it reconnects — that's now Hokkaido,
      Shikoku, Chugoku, Kinki, and Tohoku.
- [ ] Keep `unopengis/7#978` current — post per-Zone as before, except
      follow whatever cadence Hidenori specifies per zone (Tohoku got
      a "wait for full completion" instruction; default back to
      per-completion posting unless told otherwise).
- [ ] On the `slate`/`mapterhorn` side (tracked in that repo's own
      HANDOVER.md, not here): verify the freshly-rebuilt
      `japan.pmtiles` and upload it to Source Cooperative — explicitly
      queued as this session's next action after `/clear`.

## Resume prompt

Paste this after `/clear` to pick up exactly here:

> Resuming `japan-geotiff-dem` / JCI 2026-09. Read, in order: this
> file's 2026-08-19 "continued" entry (Tohoku finishing, Hokuriku
> starting, and the parallel `slate`/`mapterhorn` research thread
> summary), `DECISIONS.md` D13-D16 for the full ADRs, and
> `unopengis/7#978` for the JCI issue itself (Zone list, progress
> comments). Note `CLAUDE.md` normally describes this repo as running
> on `slate` — that's still true long-term, but this whole effort has
> been running from `aalto` instead this cycle (a working clone at
> whatever path you're reading this from, not
> `/Volumes/Migrate-2025-04/...`) — `slate` itself is now reachable
> again via an SSH jump-host route Hidenori set up mid-session
> (details in `aalto`'s own `~/.ssh/config`, deliberately not written
> here since this is a public repo), and has its own substantial
> parallel work in progress — see below.
>
> **First thing on resume, `japan-geotiff-dem` side**: check
> `logs/aalto_pack_log.jsonl`'s tail and `~/Downloads` on `aalto` to
> see exactly what's there — Hokuriku was ~4/16 done (`Z005` in
> progress) as of this entry, don't trust that number if real time has
> passed. If a `sync`, `verify`, or `skip-published` step fails with a
> credentials-expired error, that's normal (hourly TTL) — re-run
> `source-coop login` and continue. **But check the actual error text
> first**: `Z031` this session hit a transient HTTP 520 from
> Cloudflare, a different failure class that just needs a plain retry,
> not a re-login — don't assume every `sync` failure is credential
> expiry.
>
> **First thing on resume, `slate` side (separate, higher priority
> per Hidenori)**: verify the freshly-rebuilt `bundle-store/
> japan.pmtiles` (789,984 tiles, ~70.7GB, built this session after
> fixing a `tempfile`-directory bug — see `mapterhorn-japan-bridge`'s
> own HANDOVER.md for the full story) and **upload it to Source
> Cooperative** — this was the explicit next action queued before this
> `/clear`. Check `mapterhorn-japan-bridge`'s own HANDOVER.md first for
> exactly how far the `jpkyushutest1` download+bounds+polygonize
> pipeline (also still running as of this entry) has gotten, and for
> the standing rule about not publishing without Hidenori's own
> go-ahead on the actual upload step.
>
> **Standing rule (D15)**: any Zone `aalto` finishes processing must
> **not** be relayed to `slate`'s `src/1z/` once reconnected — as of
> this entry that's Hokkaido, Shikoku, Chugoku, Kinki, and Tohoku.
>
> **Standing rule (D16)**: never start a new `process_pack.py`
> invocation for a given `res` until the previous invocation's
> completion has actually been confirmed — no exceptions.
>
> **Order of remaining work on `aalto`**: finish Hokuriku (`Z005`
> onward) → 関東3 (Kanto-3) → 関東2 → 関東1 → 中部, per Hidenori's
> confirmed order. Rebuild `latest`/`obsolete` file lists periodically
> at natural pauses. Update `unopengis/7#978` per Zone completion by
> default (Tohoku got a "wait for full completion" instruction
> specifically — ask if unsure whether that was a one-off or a new
> standing preference).

## 2026-08-19 (continued): session checkpoint before an expected `/clear`

Zone progress since the last checkpoint entry above (which is now
stale — Hokuriku, 関東3, 関東2 all finished since):

- **Hokkaido, 東北, 中国, 近畿, 九州沖縄, 北陸, 関東3, 関東2: all
  complete.** (関東3 was briefly mis-reported "8/8" on `UNopenGIS/7#978`
  — it's actually 18 packs; corrected with a follow-up issue comment
  once Hidenori caught leftover `Z009`-`Z018` zips still in
  `~/Downloads` — see that repo's own comment thread for the numbers.)
- **関東1 (Kanto-1)**: in progress. Z001-Z004 done, Z005 running as
  this entry is written. 10 packs total, all already downloaded to
  `~/Downloads`.
- **中部 (Chubu)**: 23 packs total, Z001-Z006 done (see
  `logs/aalto_pack_log.jsonl`), Z007+ not yet processed — was
  deliberately paused mid-Zone-006 to let 関東1 go first (Hidenori's
  own call, avoiding download/processing collisions), not yet resumed.
- **D17 (new)**: `build_filelists.py` now emits `latest_file_list.csv.gz`/
  `obsolete_file_list.csv.gz` (columns `url,size,md5`) instead of plain
  `.txt.gz` URL lists — `size`+`md5` come free from `aws s3api
  list-objects-v2`'s ETag (verified = true MD5 for these files). This
  exists to let `mapterhorn-japan-bridge`'s downloader skip
  already-correct local files without a network request; see that
  repo's own D14/D15 for the full downstream story (a much bigger
  rewrite happened there this session: CSV manifests + `aria2c` for
  downloads, and a batched `gdal vector concat` rewrite of
  `source_polygonize.py` — ~16x measured speedup, verified end-to-end).
  Regenerated all three tiers same day (1m 305,019 / 5m 378,618 /
  10m 4,981 files).
- Credential TTL (~1hr) kept expiring mid-pack throughout this session,
  same as always — recovery pattern each time: re-run `source-coop
  login`, then manually re-run whichever stage failed (`just sync 1`
  for a sync failure, or just the S3-listing+compare for a verify-only
  failure), log a manual JSONL entry noting the TTL interruption, clean
  up, continue. Nothing new here, just confirming the pattern held.

### Next steps, in order

- [ ] Finish 関東1 (Z005 running now, then Z006-Z010).
- [ ] Resume 中部 from Z007 (17 packs remaining of 23).
- [ ] Once all Zones done: `just filelists 1` (and 5/10 if anything
      changed there) for a final manifest refresh, then a final
      `UNopenGIS/7#978` Zone-table update marking JCI 2026-09's aalto
      side complete.
- [ ] `jpnational1`'s (on `slate`) own national-scope expansion is
      gated on this repo finishing — once all 11 Zones are done here,
      that's the trigger to tell `slate` it's clear to proceed (see
      `mapterhorn-japan-bridge`'s own HANDOVER.md for exactly what that
      involves).

## Resume prompt

Paste this after `/clear` to pick up exactly here:

> Resuming `japan-geotiff-dem` (JCI 2026-09) work on `aalto`, clone at
> `/Users/hfu/japan-geotiff-dem` (not `/Volumes/github/...` — that
> path is stale, see this file's own note from earlier if confused
> about where the working clone lives). Read this file's last entry
> and `DECISIONS.md` D17 before assuming anything about current state.
>
> **Immediate next action**: check `~/Downloads` and
> `logs/aalto_pack_log.jsonl`'s tail to see exactly which 関東1
> (Kanto-1, 10 packs total) pack is next — as of this checkpoint Z005
> was running, Z001-Z004 done. Continue with
> `python3 scripts/process_pack.py 1 kanto1 ~/Downloads/FG-GML-kanto1-DEM1-20260616-Z00N.zip`
> for each remaining pack in order. If a `sync`/`verify` step fails
> with a credentials-expired error, ask Hidenori to run `source-coop
> login` again (hourly TTL, expected), then manually re-run the failed
> stage and log a JSONL entry noting the interruption before continuing
> — don't just retry blindly, this repo's own pattern for that is
> documented in recent `logs/aalto_pack_log.jsonl` entries and this
> file's own recent history.
>
> **After 関東1**: resume 中部 (Chubu) from **Z007** (Z001-Z006 already
> done, 17 of 23 packs remain) — this was deliberately paused
> mid-Zone to let 関東1 finish first, not because anything went wrong.
>
> **When all 11 Zones are done**: run `just filelists 1` for a final
> manifest refresh, post a final Zone-table completion update to
> `UNopenGIS/7#978`, and let `slate`'s session know — `jpnational1`'s
> national-scope expansion there is waiting on this.
>
> A large, separate body of work happened on `slate` this same session
> (`mapterhorn-japan-bridge`'s `japan.pmtiles` pipeline) — see that
> repo's own `HANDOVER.md` for its own resume prompt if picking that up
> too; the two threads are related (same upstream DEM data) but
> operate independently day to day.

## 2026-08-19 (continued): further checkpoint before `/clear` — 中部 nearly done, a macOS TCC permission scare (resolved, not a data issue)

Progress since the last checkpoint entry above:

- **関東1 (Kanto-1): complete**, 10/10 packs, 5,864 new meshes. Posted
  to `UNopenGIS/7#978`.
- **中部 (Chubu)**: Z001-Z007 done. Z008 running as this entry is
  written. 15 packs remain after Z008 (Z009-Z023) — **this is the
  last Zone**; once Chubu finishes, all 11 Zones of JCI 2026-09 are
  done on the `aalto` side.

**Environment scare, worth knowing about but not a real blocker**:
partway through Z008's first attempt, `~/Downloads` became completely
inaccessible to this session (`ls`/`unzip`/`rm` all failed with
`Operation not permitted`, even though `stat`/`ls -ld` on the
directory itself still worked — a classic macOS TCC "protected folder"
symptom, not a real Unix permission or data problem). Hidenori's own
diagnosis: a Claude.app auto-update likely invalidated the app's Files-
and-Folders/Full-Disk-Access grant even though the toggle still showed
"on" in System Settings (known macOS quirk after a code-signature
change) — fixed by quitting and relaunching Claude.app. **If this
happens again**: check `ls ~/Downloads` specifically fails while
`stat ~/Downloads` succeeds — that combination is the TCC signature,
distinct from real file corruption. The Z008 zip that got a false
"CRC check failed" during the outage was actually fine (`unzip -tq`
passed cleanly once access was restored) — don't assume a `process_
pack.py` failure during/right after an access hiccup means the
downloaded file is bad; re-check once access is confirmed working
again before re-downloading anything.

### Next steps, in order

- [ ] Finish 中部 (Z008 running now, then Z009-Z023 — 15 more packs
      after Z008).
- [ ] Once all 11 Zones done: `just filelists 1` (and 5/10 if
      anything changed), final `UNopenGIS/7#978` Zone-table update.
- [ ] Tell `slate`'s session (`mapterhorn-japan-bridge`) it's clear to
      start `jpnational1`'s own national-scope expansion — that's the
      one piece gated on this repo finishing (see that repo's own
      HANDOVER.md, its D14/D15 entries).

## Resume prompt

Paste this after `/clear` to pick up exactly here:

> Resuming `japan-geotiff-dem` (JCI 2026-09) on `aalto`, clone at
> `/Users/hfu/japan-geotiff-dem`. Read this file's last 2 entries
> before assuming anything.
>
> **Immediate next action**: check `~/Downloads` and
> `logs/aalto_pack_log.jsonl`'s tail — as of this checkpoint, 中部
> (Chubu, 23 packs total) had Z001-Z007 done, Z008 running. This is
> the **last remaining Zone** (北海道・東北・中国・近畿・九州沖縄・
> 北陸・関東1・関東2・関東3 are all already complete). Continue with
> `python3 scripts/process_pack.py 1 chubu ~/Downloads/FG-GML-chubu-DEM1-20260616-Z0NN.zip`
> for each remaining pack in order.
>
> **If `~/Downloads` access fails oddly** (`ls` errors with `Operation
> not permitted` while `stat ~/Downloads` still works): that's a macOS
> TCC/Full-Disk-Access glitch, not real file corruption — ask Hidenori
> to check Claude.app's Files-and-Folders permission (toggle off/on,
> or relaunch the app), don't assume downloaded files are bad.
>
> **credential TTL** (~1hr) will keep expiring mid-pack as always —
> ask Hidenori to re-run `source-coop login`, then manually re-run
> just the failed stage (see recent `logs/aalto_pack_log.jsonl`
> entries with a `"note"` field for the established recovery pattern),
> log a JSONL entry, continue. Don't restart the whole pack from
> scratch.
>
> **When all 11 Zones are done**: `just filelists 1`, final Zone-table
> update on `UNopenGIS/7#978`, then let `slate`'s session know
> `jpnational1` can start its own national-scope expansion (its
> `jpnational5`/`jpnational10` siblings already went national earlier
> this same overall effort — see `mapterhorn-japan-bridge`'s own
> HANDOVER.md D14/D15 for that whole other thread, which was running
> in parallel this session and is substantially further along).
