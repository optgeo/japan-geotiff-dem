#!/usr/bin/env python3
"""Pre-filter src/{res}/*.zip before running `convert`: move aside any
mesh-zip whose entire content is already published as 'latest' on
Source Cooperative, so `convert`'s Docker/GDAL work isn't spent
reproducing identical output. See DECISIONS.md D14.

Usage: python3 scripts/skip_already_published.py <res>

Fetches {res}/latest_file_list.csv.gz fresh each run via the
authenticated source-coop profile, for consistency with every other
command in this repo's Justfile -- data.source.coop is actually
plainly readable by any normal HTTP client (a default Python urllib
request gets a misleading 403, but that's just its User-Agent getting
blocked, not a real access-control requirement; confirmed 2026-08-14
by comparing against a browser-equivalent User-Agent, which gets a
plain 200 OK with no authentication at all).

Moves fully-redundant zips from src/{res}/ to src/{res}-skip/ (not
deleted -- reversible, and extract's own src/{res}z/ raw downloads are
never touched, so nothing about provenance is lost). A zip is only
moved if *every* .xml entry inside it already has a matching filename
in latest_file_list.csv.gz; any zip with even one not-yet-published
entry is left in place for `convert` as usual.

Verified end to end across all 244 region-packs of JCI 2026-09's 1m
refresh (DECISIONS.md D15) -- the per-mesh filename derivation here is
resolution- and product-type-agnostic (it just swaps a zip-internal
.xml entry's own name for .tif), so it applies unchanged to 5m/10m,
including 5m's multiple product types sharing one resolution folder
(DEM5A/DEM5B/DEM5C -- confirmed distinct mesh-cell keys in
latest_file_list.csv.gz, so a DEM5B file is never mistaken for an
obsolete DEM5A of the same cell). Still worth reading its output
carefully the first time a new resolution tier is run through it.
"""
import csv
import gzip
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

BUCKET = 's3://smartmaps/japan-geotiff-dem'


def fetch_latest_names(res):
    with tempfile.NamedTemporaryFile(suffix='.csv.gz') as tmp:
        subprocess.run(
            ['aws', 's3', 'cp', f'{BUCKET}/{res}/latest_file_list.csv.gz',
             tmp.name, '--profile', 'source-coop'],
            check=True,
        )
        with gzip.open(tmp.name, 'rt', newline='') as f:
            reader = csv.DictReader(f)
            urls = [row['url'] for row in reader]
    return set(url.rsplit('/', 1)[-1] for url in urls)


def main():
    if len(sys.argv) != 2:
        print('Usage: skip_already_published.py <res>')
        sys.exit(1)
    res = sys.argv[1]

    print(f'Fetching latest_file_list.csv.gz for {res} (authenticated)...')
    latest_names = fetch_latest_names(res)
    print(f'{len(latest_names)} currently-published filenames.')

    # NOTE on terminology: each entry in src/{res}/*.zip found here is
    # a GSI "collection" zip (one per broader area code, e.g.
    # FG-GML-624076-DEM1A-20251107.zip) containing up to ~100
    # individual mesh .xml files with their OWN, possibly differing,
    # survey dates -- confirmed 2026-08-18 by inspecting a real
    # Hokkaido pack (see DECISIONS.md D15's follow-up note). A zip is
    # only skipped if *every* mesh inside it is already published;
    # otherwise the whole zip is kept for `convert` (which itself,
    # like this script, opens exactly one level and finds the .xml
    # entries directly -- no further nesting to worry about).
    src_dir = Path(f'src/{res}')
    skip_dir = Path(f'src/{res}-skip')
    skip_dir.mkdir(exist_ok=True)

    zips_total = 0
    zips_skipped = 0
    meshes_total = 0
    meshes_skipped = 0
    for zip_path in sorted(src_dir.glob('*.zip')):
        zips_total += 1
        try:
            with zipfile.ZipFile(zip_path) as zf:
                xml_names = [n for n in zf.namelist() if n.lower().endswith('.xml')]
        except zipfile.BadZipFile:
            print(f'  WARNING: {zip_path.name} is not a valid zip, leaving in place')
            continue
        if not xml_names:
            continue
        meshes_total += len(xml_names)
        expected_tifs = [n.rsplit('/', 1)[-1].rsplit('.', 1)[0] + '.tif' for n in xml_names]
        if all(t in latest_names for t in expected_tifs):
            zip_path.rename(skip_dir / zip_path.name)
            zips_skipped += 1
            meshes_skipped += len(xml_names)
            print(f'  skip: {zip_path.name} (all {len(xml_names)} meshes already published)')

    meshes_kept = meshes_total - meshes_skipped
    print()
    print(f'{zips_skipped} / {zips_total} collection-zips fully redundant with '
          f'already-published data, moved to {skip_dir}/')
    print(f'{zips_total - zips_skipped} collection-zips remain in {src_dir}/ for `convert`.')
    print(f'({meshes_total} individual meshes total: {meshes_skipped} already '
          f'published, {meshes_kept} remaining to convert)')
    print(f'To undo: mv {skip_dir}/*.zip {src_dir}/')
    print(f'SUMMARY: zips_total={zips_total} zips_skipped={zips_skipped} '
          f'meshes_total={meshes_total} meshes_skipped={meshes_skipped} '
          f'meshes_kept={meshes_kept}')


if __name__ == '__main__':
    main()
