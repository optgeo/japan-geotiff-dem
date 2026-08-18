#!/usr/bin/env python3
"""Process one region-pack zip end to end, locally (designed for
running on `aalto` while `slate` is unreachable -- see DECISIONS.md
D15): extract -> skip already-published meshes (D14) -> convert ->
sync -> verify against S3 -> delete local data. Keeps peak local disk
usage to about one pack at a time by processing packs one at a time
and fully cleaning up after each.

Usage: python3 scripts/process_pack.py <res> <zone> <pack_zip_path>
Example:
  python3 scripts/process_pack.py 1 hokkaido \
    ~/Downloads/FG-GML-hokkaido-DEM1-20260616-Z001.zip

Every run appends one JSON line to logs/aalto_pack_log.jsonl,
regardless of success or failure, so processing history stays
traceable in this repo. Local data (the pack zip, extracted meshes,
converted GeoTIFFs) is only deleted after every produced .tif is
confirmed present on Source Cooperative with a matching byte size --
on any failure, nothing is deleted and the run is left in place for
inspection.

Requires src/{res}z, src/{res}, src/{res}-skip, dst/{res} to all be
empty before starting (asserts this) -- each pack is processed in
total isolation from any other, on purpose.
"""
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path('logs/aalto_pack_log.jsonl')


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def dir_empty(path):
    p = Path(path)
    if not p.exists():
        return True
    return not any(child for child in p.iterdir() if child.name != '.gitkeep')


def count_files(path, pattern='*'):
    p = Path(path)
    return len(list(p.glob(pattern))) if p.exists() else 0


def main():
    if len(sys.argv) != 4:
        print('Usage: process_pack.py <res> <zone> <pack_zip_path>')
        sys.exit(1)
    res, zone = sys.argv[1], sys.argv[2]
    pack_path = Path(sys.argv[3]).expanduser()

    record = {
        'timestamp': datetime.now(timezone.utc).astimezone().isoformat(),
        'zone': zone,
        'res': res,
        'pack': pack_path.name,
        'stages': {},
        'deleted_local': False,
        'overall_status': 'failed',
    }

    def finish(status, reason=None):
        record['overall_status'] = status
        if reason:
            record['reason'] = reason
        LOG_PATH.parent.mkdir(exist_ok=True)
        with open(LOG_PATH, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(json.dumps(record, indent=2, ensure_ascii=False))
        sys.exit(0 if status == 'success' else 1)

    for d in [f'src/{res}z', f'src/{res}', f'src/{res}-skip', f'dst/{res}']:
        if not dir_empty(d):
            finish('failed', f'{d} is not empty -- refusing to start '
                              f'(pack isolation would be broken)')

    if not pack_path.is_file():
        finish('failed', f'{pack_path} not found')

    crc = run(['unzip', '-tq', str(pack_path)])
    if crc.returncode != 0:
        finish('failed', f'CRC check failed on {pack_path.name}')
    record['stages']['crc'] = {'status': 'ok'}

    Path(f'src/{res}z').mkdir(parents=True, exist_ok=True)
    shutil.copy(pack_path, f'src/{res}z/{pack_path.name}')

    r = run(['just', 'extract', res])
    # NOTE: these are GSI "collection" zips (one per broader area
    # code), each containing up to ~100 individual mesh .xml files --
    # not one-zip-per-mesh. See skip_already_published.py's own note
    # and DECISIONS.md D15's follow-up for how this was confirmed.
    collection_zip_count = count_files(f'src/{res}', '*.zip')
    record['stages']['extract'] = {
        'status': 'ok' if r.returncode == 0 else 'failed',
        'collection_zip_count': collection_zip_count,
    }
    if r.returncode != 0:
        record['stages']['extract']['stderr_tail'] = r.stderr[-500:]
        finish('failed', 'extract failed')

    r = run(['just', 'skip-published', res])
    kept = count_files(f'src/{res}', '*.zip')
    skipped = count_files(f'src/{res}-skip', '*.zip')
    meshes_total = meshes_skipped = meshes_kept = None
    for line in r.stdout.splitlines():
        if line.startswith('SUMMARY:'):
            parts = dict(kv.split('=') for kv in line[len('SUMMARY:'):].split())
            meshes_total = int(parts.get('meshes_total', 0))
            meshes_skipped = int(parts.get('meshes_skipped', 0))
            meshes_kept = int(parts.get('meshes_kept', 0))
    record['stages']['skip_published'] = {
        'status': 'ok' if r.returncode == 0 else 'failed',
        'collection_zips_kept': kept,
        'collection_zips_skipped': skipped,
        'meshes_total': meshes_total,
        'meshes_skipped': meshes_skipped,
        'meshes_kept': meshes_kept,
    }
    if r.returncode != 0:
        record['stages']['skip_published']['stderr_tail'] = r.stderr[-500:]
        finish('failed', 'skip-published failed')

    converted = 0
    if kept > 0:
        r = run(['just', 'convert', res])
        converted = count_files(f'dst/{res}', '*.tif')
        record['stages']['convert'] = {
            'status': 'ok' if r.returncode == 0 else 'failed',
            'converted': converted,
        }
        if r.returncode != 0:
            record['stages']['convert']['stderr_tail'] = r.stderr[-800:]
            finish('failed', 'convert failed')
    else:
        record['stages']['convert'] = {'status': 'skipped', 'reason': 'nothing to convert'}

    if converted > 0:
        r = run(['just', 'sync', res])
        record['stages']['sync'] = {'status': 'ok' if r.returncode == 0 else 'failed'}
        if r.returncode != 0:
            record['stages']['sync']['stderr_tail'] = r.stderr[-800:]
            finish('failed', 'sync failed')

        mismatches = []
        for tif in Path(f'dst/{res}').glob('*.tif'):
            local_size = tif.stat().st_size
            ls = run(['aws', 's3', 'ls',
                      f's3://smartmaps/japan-geotiff-dem/{res}/{tif.name}',
                      '--profile', 'source-coop'])
            if ls.returncode != 0 or not ls.stdout.strip():
                mismatches.append({'file': tif.name, 'issue': 'not found on S3'})
                continue
            remote_size = int(ls.stdout.split()[2])
            if remote_size != local_size:
                mismatches.append({
                    'file': tif.name,
                    'issue': f'size mismatch local={local_size} remote={remote_size}',
                })
        record['stages']['verify'] = {
            'status': 'ok' if not mismatches else 'failed',
            'checked': converted,
            'mismatches': mismatches[:20],
        }
        if mismatches:
            finish('failed', f'{len(mismatches)} file(s) failed verification '
                              f'-- NOT deleting local data')
    else:
        record['stages']['sync'] = {'status': 'skipped', 'reason': 'nothing new to upload'}
        record['stages']['verify'] = {'status': 'skipped', 'reason': 'nothing to verify'}

    shutil.rmtree(f'src/{res}z', ignore_errors=True)
    shutil.rmtree(f'src/{res}', ignore_errors=True)
    shutil.rmtree(f'src/{res}-skip', ignore_errors=True)
    shutil.rmtree(f'dst/{res}', ignore_errors=True)
    pack_path.unlink()
    record['deleted_local'] = True

    finish('success')


if __name__ == '__main__':
    main()
