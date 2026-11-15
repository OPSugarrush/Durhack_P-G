"""Reproducible local profiles and complete report snapshots for parity checks."""
import argparse
import cProfile
import gzip
import json
from pathlib import Path
import pstats
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['workbook', 'ocr'], default='workbook')
    parser.add_argument('--label', required=True)
    parser.add_argument('--no-profile', action='store_true', help='Measure normal wall time without profiler overhead')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / 'artifacts' / 'performance'
    output.mkdir(parents=True, exist_ok=True)
    clock = time.perf_counter()
    previous = clock
    timings = {}
    def mark(label):
        nonlocal previous
        now = time.perf_counter()
        print(f'{label}: elapsed {now-clock:.3f}s; previous stage {now-previous:.3f}s', flush=True)
        timings[label] = now-clock
        previous = now
    profile = cProfile.Profile()
    if not args.no_profile:
        profile.enable()
    if args.mode == 'workbook':
        from needstate.workspace import config, workbook, analyse_lines
        cfg = config()
        mark('Python imports and configuration')
        lines, _ = workbook(cfg.input_path.read_bytes(), cfg.mapping)
        mark(f'Workbook parsed ({len(lines)} rows)')
        result = analyse_lines(lines, cfg, progress=mark)
        mark('Analysis complete')
    else:
        from needstate_receipt_ingestion.images import prepare_images
        from needstate_receipt_ingestion.extraction import extract_receipt
        from needstate_receipt_ingestion.ocr import get_engine
        mark('Python imports')
        get_engine()
        mark('OCR engine loaded')
        result = []
        for name in ['demo_receipt.png', 'test1.jpg']:
            file = root / 'receipt_ingestion' / 'examples' / name
            images = prepare_images(file.read_bytes(), name)
            mark('Prepared '+name)
            receipt = extract_receipt(images)
            result.append(receipt.model_dump(mode='json'))
            mark('Extracted '+name)
    stem = output / f'{args.mode}-{args.label}'
    if not args.no_profile:
        profile.disable()
        profile.dump_stats(str(stem)+'.prof')
    with gzip.open(str(stem)+'.json.gz', 'wt', encoding='utf8') as f:
        json.dump(result, f, ensure_ascii=False, allow_nan=False)
    Path(str(stem)+'.timings.json').write_text(json.dumps(timings, indent=2), encoding='utf8')
    if not args.no_profile:
        pstats.Stats(profile).strip_dirs().sort_stats('cumulative').print_stats(25)


if __name__ == '__main__':
    main()
