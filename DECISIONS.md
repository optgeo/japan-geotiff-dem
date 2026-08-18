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
| [D13](#d13-latest_file_listtxtgz--obsolete_file_listtxtgz-resolve-d9s-superseded-file-ambiguity) | `latest_file_list.txt.gz` / `obsolete_file_list.txt.gz` resolve D9's superseded-file ambiguity | Accepted | 2026-08-14 |
| [D14](#d14-skip-convert-work-for-meshes-already-published-using-latest_file_listtxtgz) | Skip `convert` work for meshes already published, using `latest_file_list.txt.gz` | Accepted, unverified | 2026-08-14 |

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

**Status**: Accepted. **Superseded 2026-08-11 (D12)**: that external
volume (`aalto`'s HDD) failed outright; the working copy now lives on
`slate`'s internal-adjacent SSD instead. The storage-headroom reasoning
below still applies to *why* an external/secondary volume was chosen
in the first place — just not that specific, now-dead, drive.

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

## D11: `convert` moved to `slate` (via colima), not fixed in place on `aalto`

**Status**: adopted 2026-08-10. **Superseded 2026-08-11 (D12)**: what
started as "running in parallel with `aalto`'s own copy of the
pipeline" became the *only* copy once `aalto`'s drive failed outright.

**Context**: `aalto`'s external USB HDD degraded over 2026-08-10 to
the point of blocking work outright (see HANDOVER.md's same-day entry
for the full diagnostic trail) — a controlled test showed real but
useless throughput (~1.3 already-converted-file skip-checks/second),
and a plausible-sounding optimization (fewer/larger transferred files)
measured no improvement, pointing at the drive's raw read bandwidth
itself as the ceiling, not something fixable by changing how this
repo's own code accesses it.

**Decision**: rather than wait out or work around `aalto`'s drive,
stood up this repo's pipeline (Docker image, `Justfile` recipes,
`aws`/`source-coop` credentials) fresh on `slate`, which already had
spare fast-SSD capacity for unrelated reasons (see
`mapterhorn-japan-bridge`'s own decision log for that space having
just been freed). Chose **colima** over Docker Desktop specifically
because `slate` is headless (no GUI login flow available over SSH);
colima is CLI-only end to end. A same-day smoke test (5 mesh zips,
26 seconds vs. `aalto`'s indefinite stall) confirmed the move was
worth the setup cost.

**Consequence**: this repo's pipeline no longer has a single canonical
machine — `aalto` remains the "on-paper" home (this file, `CLAUDE.md`,
and `HANDOVER.md`'s older entries all still describe it that way) but
`slate` is doing real conversion work too, under a separate working
copy (`japan-geotiff-dem-kyushu`) rather than the same checkout.
**Open question, not resolved**: whether `slate` becomes the permanent
home for this pipeline (in which case `aalto`'s HDD should probably be
replaced and the machine's role reconsidered, or this repo's own
`CLAUDE.md` updated to describe `slate` as primary) or whether this was
a one-time rescue for today's backlog specifically. Revisit once the
current Hokkaido/Kyushu-Okinawa backlog is fully drained — don't let
this ambiguity persist indefinitely, since a split canonical-machine
setup is confusing for any future session that hasn't read this entry.

**Resolved 2026-08-11, by circumstance rather than by the planned
revisit-once-drained process (D12)**: `aalto`'s drive failed outright
before the backlog drained. `slate` is now the sole machine, not
because the question was deliberately settled but because `aalto`'s
copy stopped being usable at all.

## D12: `aalto`'s external HDD failed outright; Hokkaido frozen, Kyushu/Okinawa-only, `slate` is now this repo's sole machine

**Status**: Decided 2026-08-11, in effect immediately.
**Hokkaido-freeze portion superseded 2026-08-12**: Hidenori restarted
Hokkaido fully from scratch (all 46 region-packs re-downloading via
the same `aalto`→`slate` relay as Kyushu/Okinawa — see `HANDOVER.md`'s
2026-08-12 entry); the slate-sole-machine and Kyushu/Okinawa-first
parts of this decision stand unchanged.

**Context**: The drive D11 already flagged as "severely degraded"
continued to worsen and, this session, crossed from "very slow" to
functionally unreadable — see `HANDOVER.md`'s 2026-08-11 entry for the
full diagnostic sequence (unmount attempts, physical unplug/replug,
`fsck_hfs` live verification, a full system restart, a full drive
power cycle, and a 61-file rescue-copy attempt that recovered 0
files). None of it restored real read throughput. Working hypothesis:
a ~2019-vintage backup HDD, spun up for sustained real load for the
first time in ~7 years, failing under exactly that load — plausible
and not worth further forensic investigation.

**Consequence, not a choice**: the 46 Hokkaido region-pack zips and 15
not-yet-transferred Kyushu/Okinawa region-pack zips
(`Z001`-`Z009`/`Z020`-`Z025`) that only ever existed on that drive are
lost. Only the 10 Kyushu/Okinawa parts (`Z010`-`Z019`) that had
already reached `slate` via the 2026-08-09/10 `Downloads`-folder fast
path survive.

**Decision**: Hidenori declined further data-rescue attempts against
the failed drive (not worth the risk/time relative to the value of
what's on it) and set two scope decisions:

1. **Hokkaido is frozen** — deliberately set aside this round, not
   abandoned. (Hidenori's own analogy: "足利尊氏の九州行きのようなもの"
   — a deliberate strategic narrowing, with the implication of
   returning to it later, not giving it up.) If resumed later, it
   starts from zero on raw data (all 46 parts need re-downloading from
   GSI).
2. **Kyushu/Okinawa is the sole focus**, best-effort, no hard
   deadline — proceed as far as available time allows using the 10
   already-landed region packs, rather than blocking on recovering or
   re-downloading the other 15.

Separately, since `aalto`'s copy of this **repo itself** (not just the
raw downloaded data) turned out to have 2026-08-09/2026-08-10 commits
that were never pushed to GitHub, and is now unrecoverable from that
machine: **`slate` becomes this repo's sole machine going forward**,
formalizing what D11 left as an open question. `gh` was
re-authenticated on `slate` (device-code flow, no loopback tunnel
needed — simpler than `source-coop login`'s OAuth flow) and a fresh
`gh repo clone optgeo/japan-geotiff-dem` was made there. This repo's
own git history genuinely has a gap: everything after `0df1cc2`
(2026-08-08) until this entry was never committed anywhere and had to
be reconstructed from cross-references in `mapterhorn-japan-bridge`'s
own (surviving) `HANDOVER.md` rather than recovered verbatim — see
that file's 2026-08-09 entry for the explicit "reconstructed, not
recovered" caveat.

**Consequences**:
- `aalto`'s copy of this repo, and the failed external drive itself,
  are safe to erase/disconnect once the live pipeline data
  (`japan-geotiff-dem-kyushu`'s `src`/`dst`) is migrated into the new
  git-tracked clone on `slate` — not yet done as of this entry, see
  `HANDOVER.md`'s next steps.
- `CLAUDE.md` no longer describes this project as running on `aalto`;
  updated to describe `slate` as the sole machine.
- Any future session should **not** re-attempt Hokkaido processing
  without a fresh, explicit decision to resume it — `jphokkaidodem1`
  in `hfu/mapterhorn`'s `source-catalog/` stays as-is (stale, never
  aggregated) until then.
- **Lesson for committing practice going forward**: this incident is
  the second time in this project's history (see
  `mapterhorn-japan-bridge`'s own parallel incident the same day) that
  multi-day uncommitted local work turned out to be sitting on a
  single point of failure. Commit more eagerly, even mid-session,
  rather than treating "the working tree is fine for now" as
  sufficient — a healthy git history costs little and this is the
  second time its absence has caused real, unrecoverable loss.

---

## D13: `latest_file_list.txt.gz` / `obsolete_file_list.txt.gz` resolve D9's superseded-file ambiguity

**Status**: Accepted

**Context**: D9 established that `sync` is additive-only — an updated
mesh uploads under its own new survey-dated filename rather than
overwriting the old one, so the old file stays published indefinitely
alongside the new one. D9 flagged this as "a real gap... not solved by
this decision" for a downstream consumer to know which of two
same-cell files is current. Mapterhorn's own `jpdem1a` ingestion
(maintained by Oliver Wipfli) hit this exact question when discussing
the JCI 2026-09 upload cycle (see `unopengis/7#978`).

**Decision**: For each resolution tier `{res}`, generate
`{res}/latest_file_list.txt.gz` and `{res}/obsolete_file_list.txt.gz`:
plain text, one full `https://data.source.coop/...` URL per line,
gzip-compressed — no CSV, no extra fields (a file-size column was
considered and dropped; it wasn't needed for the actual question these
files answer, and would have broken the plain-text simplicity for no
real benefit). Group all `.tif` filenames in `{res}/` by everything
except the trailing `YYYYMMDD` survey date; within each group, the
newest date is "latest," everything else is "obsolete." A group with
only one file is trivially "latest." Verified against the live `1/`
prefix (274,724 files, 270,778 groups, 3,946 with more than one date,
zero ties) before adopting this as the real format. Implemented in
`scripts/build_filelists.py`, run via `just filelists {res}`, uploaded
into the same resolution prefix as the data it describes. Format
documented in `source-coop/README.md` since it's meant for consumers
who never touch this GitHub repo.

**Consequences**: A tie at the max date (two files, same cell, same
survey date, different content) makes the script raise rather than
guess — should never happen given how GSI dates its releases, but if
it ever does, it needs a human decision, not a silent pick. This does
not delete or mirror-sync anything (D9's `--delete` caution still
applies in full) — `obsolete` files stay published, just labeled;
actual cleanup, if ever wanted, is a separate future decision. Only
`1/` is generated for the 2026-09 JCI cycle; `5/` and `10/` can use
the same tool once/if needed, since it already takes `{res}` as a
parameter.

---

## D14: Skip `convert` work for meshes already published, using `latest_file_list.txt.gz`

**Status**: Accepted, implementation not yet verified against a real
`src/{res}/` directory (see Consequences)

**Context**: `gmldem2tif.rb`'s `tif_valid?` skip check (D3) only looks
at whether the *local* `dst/{res}/{name}.tif` already exists and opens
cleanly — it has no notion of what's already published on Source
Cooperative. A freshly extracted `src/{res}/` mesh-zip whose content
is byte-identical to something already on S3 (same mesh, same survey
date, i.e. unchanged since a previous publish) still gets fully
re-converted locally before `sync`'s `--size-only` check finally
discards the redundant upload. For a large region pack where most
meshes haven't actually been resurveyed, this wastes real Docker/GDAL
time on output that will never actually get uploaded.

**Decision**: `scripts/skip_already_published.py {res}` fetches the
current `{res}/latest_file_list.txt.gz` (D13) via the authenticated
`source-coop` profile — confirmed 2026-08-14 that `data.source.coop`
is **not** anonymously readable (a plain `urlopen()` gets `403
Forbidden` even for `README.md`), so this cannot be a plain public
HTTP fetch. For each `src/{res}/*.zip`, it opens the zip (cheap — just
reading the entry list, no GDAL/Docker involved) and checks whether
*every* `.xml` entry's corresponding `.tif` name is already in the
latest list. If so, the whole zip is moved (not deleted) to
`src/{res}-skip/`, out of `convert`'s way. A zip with even one
not-yet-published entry is left alone. Exposed as `just skip-published
{res}`, run manually before `convert {res}`, not chained
automatically.

**Consequences**: The output-filename derivation
(`fetch_latest_names`) was verified against the live bucket from
`aalto` (4,981 names fetched for `10/`, matching D13's own count). The
zip-opening and move logic could **not** be verified the same way —
it needs a real `src/{res}/` directory, which only exists on `slate`,
unreachable from 2026-08-14 until 2026-08-24 (see `HANDOVER.md`). Run
it on one small region first and read the skip/keep counts before
trusting it on a full Zone. If a mesh-zip ever contains more than one
`.xml` entry with only some already published, the whole zip is kept
(not partially skipped) — `tif_valid?`'s own per-entry local check
still applies as a second, finer-grained skip layer during `convert`
itself, so nothing gets reconverted twice either way.
