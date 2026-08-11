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

## Resume prompt

Paste this after `/clear` to pick up exactly here:

> Resuming `japan-geotiff-dem`. Read, in order:
> `/Volumes/Migrate-2025-04/github/japan-geotiff-dem-repo/CLAUDE.md`
> (this repo now runs entirely on `slate` — `aalto`'s external HDD
> failed outright on 2026-08-11 and is being disposed of, not
> repaired), this file's two 2026-08-11 entries (the recovery/policy
> pivot, then the same-day follow-up), and `DECISIONS.md` D12 (the
> frozen-Hokkaido/Kyushu-only/slate-sole-machine decision).
>
> **Current scope: Kyushu/Okinawa only, best-effort, no deadline.**
> Hokkaido is deliberately frozen — do not resume it without checking
> with Hidenori first. `__japan-geotiff-dem` (a small leftover
> Hokkaido fragment, ~1.2GB) is marked for deletion, not yet removed.
>
> **Immediate state**: of Kyushu/Okinawa's 25 region-pack zips, 10
> (`Z010`-`Z019`) are verified healthy on `slate`
> (`japan-geotiff-dem-repo/src/1z/` → `src/1/` → `dst/1/`, 14,116
> GeoTIFFs, published to
> `s3://smartmaps/japan-geotiff-dem/1/`). The other 15
> (`Z001`-`Z009`, `Z020`-`Z025`) are being re-downloaded by Hidenori
> from GSI's portal into `aalto`'s `~/Downloads` (internal SSD — the
> only viable path now) and relayed to `slate` as they land. Check
> `aalto`'s `~/Downloads` for `FG-GML-kyushu_okinawa-DEM1-*-Z0*.zip`
> files first thing on resume.
>
> The unattended `extract`/`convert`/`sync` loop is running on `slate`
> (`nohup`+`disown`'d — find it with `ps aux | grep "while true"`, pid
> changes on restart). `sync` needs `source-coop login` refreshed
> roughly hourly (session token TTL) — re-run via the SSH-tunnel
> pattern (`ssh -N -L 8484:localhost:8484 slate.local`, then
> `source-coop login --port 8484` on `slate`, Hidenori completes the
> browser auth himself; delete any `-v` log immediately after
> confirming success). `extract`/`convert` don't need login.
>
> Once more region-packs land: let the loop absorb them, consider
> another `source-coop/README.md` Changelog entry once a meaningfully
> larger batch has published (see `CLAUDE.md`'s rule — only after a
> real publish, not preemptively).
>
> Also check `mapterhorn-japan-bridge`'s own `HANDOVER.md` for the
> downstream PMTiles-build side (`jpkyushutest1`/`5m`/`10m` downloads
> on `slate`, a separate repo/pipeline) — likely still running, check
> current progress/ETA there rather than assuming.
