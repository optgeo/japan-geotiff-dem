#!/usr/bin/env python3
"""Pre-filter src/{res}/*.zip before running `convert`: move aside any
mesh-zip whose entire content is already published as 'latest' on
Source Cooperative, so `convert`'s Docker/GDAL work isn't spent
reproducing identical output. See DECISIONS.md D14.

Usage: python3 scripts/skip_already_published.py <res>

Fetches {res}/latest_file_list.txt.gz fresh each run via the
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
in latest_file_list.txt.gz; any zip with even one not-yet-published
entry is left in place for `convert` as usual.

NOT YET VERIFIED against a real src/{res}/ directory -- written and
committed from `aalto` while `slate` was unreachable (network split,
scheduled to reconnect 2026-08-24). Run once, on a small res first,
and read its output carefully before trusting it on a full region.
"""
import gzip
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

BUCKET = 's3://smartmaps/japan-geotiff-dem'


def fetch_latest_names(res):
    with tempfile.NamedTemporaryFile(suffix='.txt.gz') as tmp:
        subprocess.run(
            ['aws', 's3', 'cp', f'{BUCKET}/{res}/latest_file_list.txt.gz',
             tmp.name, '--profile', 'source-coop'],
            check=True,
        )
        with gzip.open(tmp.name, 'rt') as f:
            urls = f.read().splitlines()
    return set(url.rsplit('/', 1)[-1] for url in urls)


def main():
    if len(sys.argv) != 2:
        print('Usage: skip_already_published.py <res>')
        sys.exit(1)
    res = sys.argv[1]

    print(f'Fetching latest_file_list.txt.gz for {res} (authenticated)...')
    latest_names = fetch_latest_names(res)
    print(f'{len(latest_names)} currently-published filenames.')

    src_dir = Path(f'src/{res}')
    skip_dir = Path(f'src/{res}-skip')
    skip_dir.mkdir(exist_ok=True)

    total = 0
    skipped = 0
    for zip_path in sorted(src_dir.glob('*.zip')):
        total += 1
        try:
            with zipfile.ZipFile(zip_path) as zf:
                xml_names = [n for n in zf.namelist() if n.lower().endswith('.xml')]
        except zipfile.BadZipFile:
            print(f'  WARNING: {zip_path.name} is not a valid zip, leaving in place')
            continue
        if not xml_names:
            continue
        expected_tifs = [n.rsplit('/', 1)[-1].rsplit('.', 1)[0] + '.tif' for n in xml_names]
        if all(t in latest_names for t in expected_tifs):
            zip_path.rename(skip_dir / zip_path.name)
            skipped += 1
            print(f'  skip: {zip_path.name} (all {len(xml_names)} entries already published)')

    print()
    print(f'{skipped} / {total} zips fully redundant with already-published '
          f'data, moved to {skip_dir}/')
    print(f'{total - skipped} zips remain in {src_dir}/ for `convert`.')
    print(f'To undo: mv {skip_dir}/*.zip {src_dir}/')


if __name__ == '__main__':
    main()
