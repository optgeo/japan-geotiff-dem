set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# extract 10, extract 5, extract 1
# This will extract grid-based zip files from region zip files.
extract res:
  find src/{{res}}z -name '*.zip' -print0 | xargs -0 -n 1 unzip -n -d src/{{res}}

# convert 10, convert 5, convert 1
# This will convert the grid-based zip files into GeoTIFF files.
# Safe to re-run: gmldem2tif.rb skips any mesh whose output GeoTIFF already
# exists and is readable, so adding new src/{res} zips incrementally and
# re-running only converts what's new.
# See github.com/unopengis/gmldem2tif for the tool.
convert res:
  mkdir -p dst/{{res}}
  docker run --rm -u $(id -u):$(id -g) \
  -v $(realpath src/{{res}}):/src -v $(realpath dst/{{res}}):/dst \
  --entrypoint /bin/bash gmldem2tif \
  -c "bundle exec ruby gmldem2tif.rb -v -n $(nproc) -c zstd-max /src /dst"

# Parameter for Source Cooperative
# - Requires a one-time `source-coop login` (done by a human, not Claude:
#   see CLAUDE.md). That populates the `source-coop` profile in
#   ~/.aws/config (credential_process + endpoint_url), so every command
#   below only ever needs `--profile source-coop` and never touches raw
#   credentials.
bucket := "s3://smartmaps/japan-geotiff-dem"

# upload documents to Source Cooperative
# Uploads source-coop/README.md (data-facing, DECISIONS.md D8) -- NOT
# the repo-root README.md, which is engineering-facing and would read
# strangely on the product page (self-referential links, "repository"
# language aimed at people running `just`, not people browsing data).
docs:
  aws s3 cp source-coop/README.md {{bucket}}/README.md --profile source-coop --acl bucket-owner-full-control
  aws s3 rm {{bucket}}/INCOMPLETE --profile source-coop
#  aws s3 cp INCOMPLETE {{bucket}}/INCOMPLETE --profile source-coop --acl bucket-owner-full-control

# upload Japan GeoTIFF DEM data to Source Cooperative, additive only.
# Deliberately does NOT pass --delete (see DECISIONS.md D9): local
# dst/{res} usually holds only whatever prefecture was just
# (re)processed, not the full national dataset, so a --delete mirror
# sync would erase every other prefecture's already-published files
# still missing locally. Only ever adds new objects or overwrites ones
# whose content changed; never removes anything remote.
# --size-only (DECISIONS.md D10): compares by size only, not mtime.
# Every local file gets today's mtime after a fresh `convert`, which
# would otherwise flag already-published, byte-identical files for a
# pointless re-upload on every run. Mesh filenames already encode the
# survey date, so a same-name/same-size file is the same data.
sync res:
  aws s3 sync dst/{{res}} {{bucket}}/{{res}} --size-only --profile source-coop --acl bucket-owner-full-control

# DANGER: full-mirror sync, WILL DELETE any remote {res} object missing
# from local dst/{res}. Only correct when dst/{res} genuinely holds the
# complete, current national dataset for that resolution -- not for
# incremental per-prefecture publishing. Confirm with Hidenori and
# `--dryrun` it first; see DECISIONS.md D9.
sync-mirror res:
  aws s3 sync dst/{{res}} {{bucket}}/{{res}} --delete --size-only --profile source-coop --acl bucket-owner-full-control

# create quadrans version of GeoTIFF
quadrans res:
  ruby scripts/quadrans_script.rb {{res}}

