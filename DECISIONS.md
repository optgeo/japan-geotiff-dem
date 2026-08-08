# DECISIONS.md

Architecture Decision Records (ADR) for `japan-geotiff-dem`. Each entry has:

- **Status**: current state (`Accepted` / `Open` / `Superseded`)
- **Context**: why the decision was needed
- **Decision**: what was decided
- **Consequences**: what follows from it, and when to reconsider

This file is the *why*, kept stable. Session-by-session narrative --
what happened, what's still running, what broke -- lives in
`HANDOVER.md` instead; don't duplicate rationale into both files. Same
split as the sibling `optgeo/cogenerate` repo's `DECISIONS.md` /
`HANDOVER.md`, reused here for consistency across the `optgeo` family.

## Table of contents

| # | Title | Status | Date |
|---|---|---|---|
| [D1](#d1-placement-of-a-new-download-is-decided-by-content-not-by-convention) | Placement of a new download is decided by content, not by convention | Accepted | 2026-08-08 |
| [D2](#d2-source-cooperative-publishing-path) | Source Cooperative publishing path | Accepted | 2026-08-08 |
| [D3](#d3-skip-already-done-work-by-default-quadrans-is-the-one-exception) | Skip already-done work by default; `quadrans` is the one exception | Accepted | 2026-08-08 |
| [D4](#d4-trust-content-dates-over-the-update-announcement-date-full-download-diff-only) | Trust content dates over the update-announcement date; full-download-diff only | Accepted | 2026-08-08 |
| [D5](#d5-working-copy-lives-on-external-storage) | Working copy lives on external storage | Accepted | 2026-08-08 |
| [D6](#d6-quadransres-has-no-source-cooperative-sync-path-yet) | `quadrans/{res}` has no Source Cooperative sync path yet | Open | 2026-08-08 |
| [D7](#d7-readmemds-changelog-only-records-real-publish-events) | README.md's Changelog only records real publish events | Superseded by D8 | 2026-08-08 |
| [D8](#d8-a-separate-readmemd-for-the-source-cooperative-product-itself) | A separate README.md for the Source Cooperative product itself | Accepted | 2026-08-08 |
| [D9](#d9-syncres-must-never-pass---delete-for-incremental-per-prefecture-publishing) | `sync <res>` must never pass `--delete` for incremental per-prefecture publishing | Accepted | 2026-08-08 |
| [D10](#d10-sync-uses---size-only-to-avoid-re-uploading-unchanged-files) | `sync` uses `--size-only` to avoid re-uploading unchanged files | Accepted | 2026-08-08 |

---

## D1: Placement of a new download is decided by content, not by convention

**Status**: Accepted

**Context**: `gmldem2tif.rb` (inside the `gmldem2tif` Docker image) only
unzips one level: it opens each `.zip` in the directory it's given and
converts `.xml` entries found directly inside. GSI's kiban download
service, however, hands out zips of at least two different
granularities depending on how a download is requested -- a bulk
region/prefecture pack containing many mesh-level zips, or a single
mesh-level zip with GML XML directly inside. Nothing in the filename
alone reliably distinguishes the two ahead of time.

**Decision**: `src/{res}z/` is not "for region packs" by definition --
it's for whatever needs `extract` first. Before placing a new download,
peek inside it (`unzip -l`). If it contains further `.zip` entries, it
goes in `src/{res}z/` and needs `just extract {res}`. If it already
contains `.xml` directly, it can go straight into `src/{res}/`,
skipping `extract` entirely.

**Consequences**: A human (or Claude) has to actually look at each new
download once before deciding where it lands; there's no way to
automate the choice from the filename alone. Documented in `CLAUDE.md`.

---

## D2: Source Cooperative publishing path

**Status**: Accepted

**Context**: The repo's own `Justfile` (`docs`/`sync` recipes) predated
a role-split pattern that the sibling repo `cogenerate` later worked
out and validated end to end for Source Cooperative publishing
(`cogenerate`'s D10). The old recipes here pointed at
`s3://us-west-2.opendata.source.coop/smartmaps/japan-geotiff-dem` with
no `--profile` flag, relying on ad hoc exported AWS environment
variables per the old comment ("You need to additionally set
environment variables from Source Cooperative"). Separately,
`cogenerate`'s HANDOVER.md records a real incident: running
`source-coop creds` directly printed a live temporary AWS access
key/secret/session token into the conversation transcript.

**Decision**: Adopt `cogenerate`'s pattern here. Hidenori runs
`source-coop login` once, locally -- a human-only step, since it's an
account-level action. That populates the `source-coop` profile in
`~/.aws/config` (`credential_process = source-coop creds`, plus
`endpoint_url`). Claude only ever invokes `aws ... --profile
source-coop`, and never runs `source-coop creds` directly -- use `aws
s3 ls s3://smartmaps/japan-geotiff-dem/ --profile source-coop` instead
if the login session needs confirming, since it authenticates via the
same `credential_process` without printing secret material (**not**
`aws sts get-caller-identity` -- confirmed 2026-08-08 that it fails
with an opaque `Unknown` error under this profile, since the profile's
`endpoint_url` is S3-only and doesn't serve the STS API). Bucket target
corrected to `s3://smartmaps/japan-geotiff-dem` (matches the product's
real Source Cooperative URL, already linked from `README.md`), with
`--acl bucket-owner-full-control` added per `cogenerate`'s working
recipe.

**Consequences**: `Justfile`'s `docs`/`sync` recipes now depend on the
`source-coop` profile existing locally -- they will fail cleanly (auth
error) rather than silently if that setup hasn't been done on a given
machine. `just docs` was exercised for real on 2026-08-08 (see D8 and
`HANDOVER.md`) -- upload succeeded, and the live product page was
re-fetched to confirm the new `source-coop/README.md` actually
rendered. `just sync` (the actual data) has not been exercised yet.

---

## D3: Skip already-done work by default; `quadrans` is the one exception

**Status**: Accepted

**Context**: Hokkaido alone ships as 46 separate region-pack files
(`Z001`-`Z046`), arriving over an extended download session rather than
all at once. Re-running the whole pipeline from scratch on every new
part would be wasteful and, for `convert`, would re-touch GDAL/Ruby
work that's already correct.

**Decision**: Rely on the idempotency already built into `extract`
(`unzip -n`, silently skips files that already exist) and `convert`
(`gmldem2tif.rb`'s `tif_valid?` check skips any mesh whose output
`.tif` already opens cleanly). Both are safe to re-run after every new
batch lands in `src/{res}z/`. `quadrans_script.rb` is explicitly the
exception: it globs *all* of `dst/{res}/*.tif` on every run and rebuilds
each quadrant's VRT + LERC mosaic from scratch, with no skip logic. Run
it once a prefecture's parts are all converted, not after each one.

**Consequences**: No code changes were needed to get incremental
re-runs of `extract`/`convert` -- the existing scripts already do the
right thing. `quadrans` staying non-incremental is accepted as-is for
now (rebuilding a whole prefecture's mosaic isn't that expensive
compared to the download+convert time); revisit if it becomes a
bottleneck once full-Japan coverage is attempted.

---

## D4: Trust content dates over the update-announcement date; full-download-diff only

**Status**: Accepted

**Context**: Hidenori downloaded a Hokkaido region pack after seeing
GSI's kiban update-info page (https://service.gsi.go.jp/kiban/app/data_update_info/)
announce a 2026-07-31 DEM1A update, but the pack's own filename carried
a `20260616` date, and the mesh zips extracted from it carried an even
earlier `20250507` date. This raised a real question of whether the
download actually reflected the announced update.

**Decision**: Treat the update-info page's date as *announcement* date,
not *generation* date -- past entries on that page show the same
pattern (e.g. the 2025-07 update page entry postdates the underlying
correction work it describes). A mesh's embedded date is the
authoritative signal for that mesh's vintage; compare it against this
repo's *previous* local baseline, not against the announcement date,
to judge whether a given download is actually new. Separately
confirmed with Hidenori that GSI's download site exposes no
inventory/diff API at all -- it's a POST-with-selection that returns a
ZIP, nothing more -- so there is no way to ask "what changed" ahead of
downloading.

**Consequences**: Update detection is inherently a full-download +
content-diff process; don't build tooling that assumes a lighter-weight
check is possible. When a downloaded part's meshes all carry an old
date (as Hokkaido `Z001` did), that's a signal to check other parts of
the same prefecture, not a sign the download itself is broken.

---

## D5: Working copy lives on external storage

**Status**: Accepted

**Context**: Full-Japan 1m DEM coverage, converted and mosaicked, will
not fit comfortably on the internal disk that hosted the repo
previously.

**Decision**: Hidenori relocated the working clone from
`/Users/hfu/japan-geotiff-dem` to `/Volumes/github/japan-geotiff-dem`
(external volume). Confirmed via `git remote -v` this is the same
`optgeo/japan-geotiff-dem` clone, not a divergent copy.

**Consequences**: Storage/hardware provisioning is Hidenori's call, not
something Claude manages or should second-guess. Paths referenced in
future sessions should be checked against wherever the working copy
currently lives, not assumed to be under `/Users/hfu/`.

---

## D6: `quadrans/{res}` has no Source Cooperative sync path yet

**Status**: Open

**Context**: The repo is titled "for Mapterhorn," and `quadrans_script.rb`
exists specifically to produce a Mapterhorn-compatible, LERC-compressed,
quadrant-merged mosaic -- but `Justfile` only has a `sync` recipe for
`dst/{res}` (the raw per-mesh GeoTIFFs). The quadrant mosaic is
generated locally and never uploaded anywhere.

**Decision**: Deferred. Adding a sync path for `quadrans/{res}` would
mean deciding what public path/product it should be served from
(a prefix under the existing `smartmaps/japan-geotiff-dem` product, or
a separate product entirely) -- ask Hidenori before inventing one.

**Consequences**: Until this is decided, `quadrans/{res}` output stays
local-only, disposable, and safe to delete/regenerate at will.

---

## D7: README.md's Changelog only records real publish events

**Status**: Superseded by D8 — repo-root `README.md` is no longer what
gets uploaded to Source Cooperative at all, so this decision now
applies to `source-coop/README.md`'s Changelog instead. The underlying
rule is unchanged, just relocated; kept here for history.

**Context**: `README.md` was, at the time, itself uploaded to the
public bucket via `just docs`, so it doubled as the product's public
description on Source Cooperative, not just a repo README. Its
`## Changelog` section should describe what a downstream consumer of
the published data can actually observe, not in-progress local work.

**Decision**: Only append a `## Changelog` entry after a `just
sync`/`just docs` run has actually completed against the public
bucket -- format: `- YYYY-MM-DD: <what changed> (resolution(s), and
region if partial-coverage).` Session-by-session narrative of
in-progress work (downloads in flight, local pipeline runs, bugs found)
belongs in `HANDOVER.md` instead, which is not synced anywhere.

**Consequences**: `HANDOVER.md` and the Changelog will show different
timelines by design -- `HANDOVER.md` moves in real time, the Changelog
only moves on actual publish. Don't try to keep them in sync
entry-for-entry.

---

## D8: A separate README.md for the Source Cooperative product itself

**Status**: Accepted

**Context**: Hidenori noticed that `https://source.coop/smartmaps/japan-geotiff-dem`
was serving the repo-root `README.md` verbatim, and it read as
noticeably out of place there: it says "This repository provides..."
(a GitHub-ism, not language for someone browsing an S3 bucket), its
"Features" section reads like software marketing ("Simplifies working
with...", "Ready to use with various mapping tools") rather than a
dataset description, and its `## Links` section links back to
`https://source.coop/smartmaps/japan-geotiff-dem` — i.e. the very page
the reader is already on. `optgeo/cogenerate` hit the identical problem
and already has a solution on record (its own D14): a separate
data-facing README, uploaded to the product root instead of the repo's
own `README.md`.

**Decision**: Added `source-coop/README.md` — describes the dataset
(what it is, format/CRS, GSI attribution and Survey Act reproduction
approval, changelog of real publish events per D7), one-directionally
links to `optgeo/japan-geotiff-dem` for the pipeline code (never links
back to the Source Cooperative page itself), and deliberately doesn't
hardcode current coverage extent (points at the bucket's own file
listing instead, same reasoning as `cogenerate`'s D14). `Justfile`'s
`docs` recipe now uploads `source-coop/README.md` to `{{bucket}}/README.md`,
not the repo-root file. Repo-root `README.md` was trimmed to drop the
now-redundant self-referential GitHub link and the dataset-marketing
language, refocused as purely the engineering/pipeline README.

**Consequences**: Two README files to keep in sync conceptually (not
textually) going forward — repo-root `README.md` for people running
`just` commands, `source-coop/README.md` for people who only ever touch
the S3 bucket. When the pipeline's stages or output format change,
check whether `source-coop/README.md`'s format/CRS description needs
updating too.

---

## D9: `sync <res>` must never pass `--delete` for incremental per-prefecture publishing

**Status**: Accepted

**Context**: Hidenori asked, before running any real `sync`, whether
repeated syncs are safe (differential upload) or risk "disaster" —
correctly suspecting the direction of the risk without yet knowing its
shape. Checked: the already-published remote `1/` prefix holds Japan's
full national 1m coverage (~184k objects, from the 2026-05-28 upload),
while local `dst/1` at the time held only Hokkaido's in-progress subset
(~7k files, 7 of 46 parts). The `Justfile`'s original `sync` recipe
passed `aws s3 sync ... --delete` — which deletes any *remote* object
missing from *local* source. Running it as originally written would
have deleted essentially all non-Hokkaido 1m coverage (~177k files)
still legitimately published and in use (this pipeline's own output is
referenced from `mapterhorn/mapterhorn#142`). This was caught before
ever running a real (non-dryrun) sync.

Separately, a `--dryrun` of the `--delete`-free version showed *every*
local file flagged for upload, including ones already present remotely
with identical size — `aws s3 sync`'s default change-detection is
size+mtime, not content hash, and every local file has today's mtime
since it was just regenerated. So a per-prefecture sync run transfers
the whole batch's data every time, not a true minimal diff of what
actually changed content-wise. Not dangerous, just not as cheap as
"differential" might imply — worth setting that expectation rather than
assuming re-running `sync` is free.

**Decision**: `Justfile`'s `sync <res>` recipe never passes `--delete` —
it only adds new objects or overwrites ones whose local copy differs by
size/mtime, never removes remote objects. A separate `sync-mirror <res>`
recipe keeps the `--delete` behavior, clearly labeled `DANGER`, for the
(rare, and not yet needed) case where `dst/{res}` genuinely holds the
complete, current, national dataset for that resolution and a real
mirror is intended — always `--dryrun` it first and confirm with
Hidenori before running for real.

**Consequences**: Because a mesh's filename encodes its survey date
(e.g. `-DEM1A-20250507.tif` vs `-DEM1A-20260603.tif`), an updated mesh
uploads under a *new* key rather than overwriting the old one in place
— the old, now-superseded file stays published alongside the new one
indefinitely under the additive-only `sync`. This is a real gap
(consumers have no signal that an older-dated file for the same
coordinates has been superseded) but an accepted one for now, not
solved by this decision — revisit once full-Japan re-coverage makes it
a bigger practical problem, e.g. with a follow-up cleanup step keyed
off duplicate mesh-code prefixes.

---

## D10: `sync` uses `--size-only` to avoid re-uploading unchanged files

**Status**: Accepted

**Context**: A `--dryrun` of `sync` (D9) showed every local file flagged
for upload, including ones already published remotely with an
identical size. `aws s3 sync`'s default change-detection is size +
modification time; a freshly-run `convert` gives every local file
today's mtime regardless of whether its content actually changed, so
the mtime comparison is useless here and forces a full re-transfer of
the whole batch on every `sync`. Measured concretely against the
Hokkaido batch through `Z010`: of 10,418 local files, only 1,198 didn't
already exist remotely under the same name — the other 9,220 would
have been re-uploaded for nothing.

**Decision**: Added `--size-only` to both `sync` and `sync-mirror` in
`Justfile`. Since mesh filenames already encode the survey date (a
content-identifying attribute — a changed mesh gets a new filename, not
just new bytes under the old name), a same-name file with a matching
size is safe to treat as unchanged. The residual risk — a genuinely
different file landing on an identical byte count under an unchanged
name — is real in principle but not in practice for this kind of
raster data.

**Consequences**: `sync` now only transfers genuinely new or
differently-sized files. If GDAL/ZSTD versions ever change in a way
that alters output byte-for-byte without changing raster content, a
size-based comparison could theoretically miss a legitimate re-upload
in the exact scenario `--size-only` is designed to skip — acceptable
tradeoff, but worth remembering if `gmldem2tif`'s Docker image is ever
rebuilt against a newer toolchain.
