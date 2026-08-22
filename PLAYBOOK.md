# PLAYBOOK: running the next major GSI DEM update

A short, standalone checklist for the next time GSI ships a major DEM
update (the kind that triggers a new JCI-style cycle, not routine
maintenance). Read `CLAUDE.md` for full operating detail and
`DECISIONS.md` for the reasoning — this file is just "what to actually
do, in order," kept short on purpose so it stays usable cold.

## Trigger

- GSI's update-info page (https://service.gsi.go.jp/kiban/app/data_update_info/)
  announces a new DEM1A/DEM5A/etc. release, **or**
- Hidenori decides it's time regardless (e.g. a Mapterhorn release
  cycle is coming up — see the `unopengis/7` issue thread and
  `mapterhorn/mapterhorn#142` for prior-cycle context).

Confirm this isn't already covered by an in-flight cycle before
starting a new one — check `unopengis/7` for an open JCI-style issue
first.

## Repo and machine

- Repo: `optgeo/japan-geotiff-dem`, working copy on **`aalto`**
  (`/Users/hfu/japan-geotiff-dem`, this directory) — that's the
  intended machine for this workflow going forward, Downloads-folder
  and all, not just a `slate`-unreachable workaround.
- Driver script: `scripts/process_pack.py <res> <zone> <pack_zip_path>`
  — runs one region-pack zip through extract → skip-published →
  convert → sync → verify-against-S3 → delete-local, fully
  self-cleaning on success, leaves everything in place for inspection
  on any failure. This is the tool built for exactly this workflow
  (DECISIONS.md D15) — use it per pack rather than running `just`
  recipes by hand.

## Division of labor

**Hidenori's side:**
1. Pick target resolution(s)/zones for this cycle (1m is the usual
   priority; 5m/10m only if GSI's update actually touches them — check
   the announcement).
2. Download each region-pack zip from GSI's portal
   (https://service.gsi.go.jp/kiban/app/download-basic) by hand, one
   part at a time, into `~/Downloads` — this is a browser/session-bound
   flow with no bulk API (CLAUDE.md's Mission section), so there's no
   way to script around it. Large prefectures ship as multiple parts
   (e.g. Hokkaido Z001–Z046) — download them serially as convenient,
   no need to wait for a whole prefecture before handing parts off.
3. Run `source-coop login` when asked — session tokens expire on
   roughly a 1-hour cadence, so expect to be asked again mid-session
   if a sync fails on credential expiry. Verify with
   `aws s3 ls s3://smartmaps/japan-geotiff-dem/ --profile source-coop`,
   never `source-coop creds` directly (prints secrets to stdout).
4. Decide zone order and when to call a batch "done enough to report,"
   when asked.

**Claude's side:**
1. Watch `~/Downloads` for new pack zips as Hidenori downloads them.
2. For each: `python3 scripts/process_pack.py <res> <zone> <pack_path>`.
   Confirm `src/{res}z`, `src/{res}`, `src/{res}-skip`, `dst/{res}` are
   empty first if the script refuses to start (it asserts this itself
   — usually means a previous failed run wasn't cleaned up; inspect
   before clearing).
3. On failure, diagnose before retrying blindly:
   - `HTTP 520` from S3 and credential-expiry sync failures are a
     known, recoverable, recurring pattern — just retry the same
     `process_pack.py` invocation (or `just sync <res>` alone if only
     the sync stage failed) once the cause is addressed (fresh
     `source-coop login`, or the transient 520 clears). Re-verify
     against a fresh `aws s3 ls` afterward.
     **Never delete local data on a bare failure** — the script
     already doesn't, by design.
   - Anything else (CRC failure, convert failure): read the actual
     error, don't assume it's the same transient pattern.
4. Every run appends to `logs/aalto_pack_log.jsonl` automatically —
   check it for a running tally rather than re-deriving progress by
   hand.
5. Once a batch (e.g. a whole zone/prefecture) completes:
   - Run `just filelists <res>` to refresh `latest_file_list.csv.gz` /
     `obsolete_file_list.csv.gz`.
   - Add a dated entry to `source-coop/README.md`'s Changelog, then
     `just docs` to publish it.
   - Report progress on the relevant `unopengis/7` issue (Zone-table
     style, like JCI 2026-09's #978) and, once the whole cycle wraps,
     a summary comment on `mapterhorn/mapterhorn#142` for Oliver
     Wipfli / downstream `jpdem1a` consumers — include the
     `latest_file_list.csv.gz`/`obsolete_file_list.csv.gz` URLs, they're
     the diffable-without-rehashing manifest downstream actually wants.
6. Update `HANDOVER.md` with what happened this session (narrative),
   and `DECISIONS.md` only if something new was actually decided (not
   every session needs a new entry).

## Known gotchas (don't rediscover these)

- GSI's announcement date ≠ the mesh file's embedded survey date —
  don't treat a mismatch as staleness; compare against the *previous*
  local baseline instead (DECISIONS.md D4).
- A single region-pack zip can contain a mix of old and new survey
  vintages — check extracted filenames, don't assume uniform vintage
  across a whole pack or prefecture.
- No `--delete` on `sync`, ever (D9) — local `dst/{res}` only ever
  holds whatever's just been processed, not the full national set.
- Check disk space on `aalto`'s internal SSD before a large zone (large
  prefectures can be tens of GB in `~/Downloads` before cleanup).
- If `slate` is back in the picture by the next cycle, reconcile which
  zones each machine already finished (`logs/aalto_pack_log.jsonl` vs.
  `slate`'s own state) before resuming its loop — don't let both
  machines grab the same zone.

## Downstream: `mapterhorn-japan-bridge`

Once this repo's data is published, the downstream tiling effort
(`hfu/mapterhorn-japan-bridge`, on `slate`) picks it up separately —
see that repo's own `CLAUDE.md`/`DECISIONS.md`/`HANDOVER.md`. Not this
repo's concern beyond publishing clean, verified, sync'd data for it to
consume.
