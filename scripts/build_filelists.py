#!/usr/bin/env python3
"""Build latest_file_list.txt.gz / obsolete_file_list.txt.gz for one
japan-geotiff-dem resolution tier and upload them back to the same
Source Cooperative prefix. See DECISIONS.md D13 for why, and
source-coop/README.md for the published format spec.

Usage: python3 scripts/build_filelists.py <res>
Example: python3 scripts/build_filelists.py 1
"""
import gzip
import re
import subprocess
import sys
from collections import defaultdict

BUCKET = 's3://smartmaps/japan-geotiff-dem'
BASE_URL = 'https://data.source.coop/smartmaps/japan-geotiff-dem'
PATTERN = re.compile(r'^(?P<key>.+)-(?P<date>\d{8})\.tif$')


def list_objects(res):
    result = subprocess.run(
        ['aws', 's3', 'ls', f'{BUCKET}/{res}/', '--profile', 'source-coop'],
        capture_output=True, text=True, check=True,
    )
    filenames = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        filename = parts[3]
        if filename.endswith('.tif'):
            filenames.append(filename)
    return filenames


def split_latest_obsolete(filenames):
    groups = defaultdict(list)
    unmatched = []
    for filename in filenames:
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


def write_gz(filenames, res, out_path):
    with gzip.open(out_path, 'wt') as f:
        for fn in sorted(filenames):
            f.write(f'{BASE_URL}/{res}/{fn}\n')


def upload(local_path, res, remote_name):
    subprocess.run(
        ['aws', 's3', 'cp', local_path, f'{BUCKET}/{res}/{remote_name}',
         '--profile', 'source-coop', '--acl', 'bucket-owner-full-control'],
        check=True,
    )


def main():
    if len(sys.argv) != 2:
        print('Usage: build_filelists.py <res>')
        sys.exit(1)
    res = sys.argv[1]

    print(f'Listing s3://smartmaps/japan-geotiff-dem/{res}/ ...')
    filenames = list_objects(res)
    print(f'{len(filenames)} .tif files found.')

    latest, obsolete = split_latest_obsolete(filenames)
    print(f'latest: {len(latest)}, obsolete: {len(obsolete)}')

    write_gz(latest, res, 'latest_file_list.txt.gz')
    write_gz(obsolete, res, 'obsolete_file_list.txt.gz')

    upload('latest_file_list.txt.gz', res, 'latest_file_list.txt.gz')
    upload('obsolete_file_list.txt.gz', res, 'obsolete_file_list.txt.gz')
    print('Uploaded both files.')


if __name__ == '__main__':
    main()
