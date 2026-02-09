"""Run extraction on samples and assert recommended routes match expected.jsonl."""
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
samples_dir = repo_root / 'samples'

sys.path.insert(0, str(repo_root))
from fnol_agent.extractor import extract_from_file
from fnol_agent.router import build_output


def load_expected(path: Path):
    entries = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


if __name__ == '__main__':
    expected_path = samples_dir / 'expected.jsonl'
    if not expected_path.exists():
        print('expected.jsonl not found in samples/', file=sys.stderr)
        sys.exit(2)
    entries = load_expected(expected_path)
    failures = []
    for e in entries:
        fname = e.get('file')
        expected_route = e.get('expectedRoute')
        sample_path = samples_dir / fname
        if not sample_path.exists():
            failures.append(f"Missing sample file: {sample_path}")
            continue
        out = extract_from_file(str(sample_path))
        result = build_output(out)
        got = result.get('recommendedRoute')
        print(f"{fname} -> expected: {expected_route}, got: {got}")
        if got != expected_route:
            failures.append(f"Route mismatch for {fname}: expected {expected_route}, got {got}")
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        sys.exit(1)
    print('All sample routes matched expected values.')
    sys.exit(0)
