#!/usr/bin/env python3
"""Build latest_file_list.csv.gz / obsolete_file_list.csv.gz for one
japan-geotiff-dem resolution tier and upload them back to the same
Source Cooperative prefix. See DECISIONS.md D13 for why, and
source-coop/README.md for the published format spec.

CSV columns: url,size,md5. size and md5 come from a single paginated
`aws s3api list-objects-v2` listing -- no per-file HEAD/GET needed.
`md5` is each object's ETag, which equals its true MD5 for these
single-part-uploaded GeoTIFFs (verified 2026-08-19 against a real
file's locally-computed MD5). Downstream consumers (source_download.py
on the mapterhorn-japan-bridge side) use this to skip already-correct
local files without any network round-trip at all.

Usage: python3 scripts/build_filelists.py <res>
Example: python3 scripts/build_filelists.py 1
"""
import csv
import gzip
import json
import re
import subprocess
import sys
from collections import defaultdict

BUCKET = 'smartmaps'
PREFIX = 'japan-geotiff-dem'
BASE_URL = 'https://data.source.coop/smartmaps/japan-geotiff-dem'
ENDPOINT = 'https://data.source.coop'
PATTERN = re.compile(r'^(?P<key>.+)-(?P<date>\d{8})\.tif$')


def list_objects(res):
    result = subprocess.run(
        ['aws', 's3api', 'list-objects-v2',
         '--bucket', BUCKET, '--prefix', f'{PREFIX}/{res}/',
         '--profile', 'source-coop', '--endpoint-url', ENDPOINT,
         '--output', 'json'],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    objects = {}  # filename -> (size, md5)
    for obj in data.get('Contents', []):
        key = obj['Key']
        filename = key.rsplit('/', 1)[-1]
        if not filename.endswith('.tif'):
            continue
        etag = obj['ETag'].strip('"')
        if '-' in etag:
            # multipart-upload ETag, not a real MD5 -- shouldn't happen
            # for these files, but don't silently record a wrong hash.
            raise ValueError(
                f'{filename}: ETag {etag!r} looks like a multipart '
                f'ETag, not a plain MD5 -- investigate before trusting it'
            )
        objects[filename] = (obj['Size'], etag)
    return objects


def split_latest_obsolete(objects):
    groups = defaultdict(list)
    unmatched = []
    for filename in objects:
        m = PATTERN.match(filename)
        if not m:
            unmatched.append(filename)
            continue
        groups[m.group('key')].append((m.group('date'), filename))

    if unmatched:
        print(f'WARNING: {len(unmatched)} filenames did not match the '
              f'expected pattern, excluded from both lists:')
        for fn in unmatched[:20]:
            print(f'  {fn}')

    latest, obsolete = [], []
    for key, entries in groups.items():
        dates = [d for d, _ in entries]
        max_date = max(dates)
        if dates.count(max_date) > 1:
            tied = [fn for d, fn in entries if d == max_date]
            raise ValueError(
                f'tie at max date for key {key}: {tied} -- needs manual '
                f'resolution, refusing to guess'
            )
        for d, fn in entries:
            (latest if d == max_date else obsolete).append(fn)
    return latest, obsolete


def write_gz(filenames, objects, res, out_path):
    with gzip.open(out_path, 'wt', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['url', 'size', 'md5'])
        for fn in sorted(filenames):
            size, md5 = objects[fn]
            writer.writerow([f'{BASE_URL}/{res}/{fn}', size, md5])


def upload(local_path, res, remote_name):
    subprocess.run(
        ['aws', 's3', 'cp', local_path, f's3://{BUCKET}/{PREFIX}/{res}/{remote_name}',
         '--profile', 'source-coop', '--acl', 'bucket-owner-full-control'],
        check=True,
    )


def remove_stale_txt_gz(res):
    # Clean up the pre-CSV .txt.gz manifests so the bucket doesn't carry
    # two conflicting formats indefinitely.
    for name in ['latest_file_list.txt.gz', 'obsolete_file_list.txt.gz']:
        subprocess.run(
            ['aws', 's3', 'rm', f's3://{BUCKET}/{PREFIX}/{res}/{name}',
             '--profile', 'source-coop'],
            check=False,
        )


def main():
    if len(sys.argv) != 2:
        print('Usage: build_filelists.py <res>')
        sys.exit(1)
    res = sys.argv[1]

    print(f'Listing s3://{BUCKET}/{PREFIX}/{res}/ (with size+ETag) ...')
    objects = list_objects(res)
    print(f'{len(objects)} .tif files found.')

    latest, obsolete = split_latest_obsolete(objects)
    print(f'latest: {len(latest)}, obsolete: {len(obsolete)}')

    write_gz(latest, objects, res, 'latest_file_list.csv.gz')
    write_gz(obsolete, objects, res, 'obsolete_file_list.csv.gz')

    upload('latest_file_list.csv.gz', res, 'latest_file_list.csv.gz')
    upload('obsolete_file_list.csv.gz', res, 'obsolete_file_list.csv.gz')
    remove_stale_txt_gz(res)
    print('Uploaded both files (csv.gz), removed stale txt.gz if present.')


if __name__ == '__main__':
    main()
