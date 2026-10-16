"""Create private configured copies; never edit the public workflow templates."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(config: dict, output: Path) -> int:
    output = output.resolve()
    private_root = (ROOT / '.work').resolve()
    if not output.is_relative_to(private_root) or output == private_root:
        raise ValueError('Configured exports must be under .work/, which is git-ignored')
    if output.exists():
        raise FileExistsError('Output already exists; choose a new directory')
    values = config.get('values', {})
    required = {'CONFIG_BASE_ID', 'ACCOUNTS_TABLE_ID', 'PIPELINES_TABLE_ID'}
    allowed = required | {'FEISHU_CREDENTIAL_ID', 'DEEPSEEK_CREDENTIAL_ID', 'FEED_QUERY_CREDENTIAL_ID', 'METRICS_CREDENTIAL_ID'}
    if set(values) - allowed or not required.issubset(values):
        raise ValueError('Provide the three environment identifiers; only documented placeholders are allowed')
    if any(not isinstance(v, str) or not v.strip() for v in values.values()):
        raise ValueError('Replacement identifiers must be non-empty strings')
    manifest = json.loads((ROOT / 'n8n/manifest.json').read_text())['workflows']
    remap = config.get('workflow_ids', {})
    known = {w['id'] for w in manifest}
    if set(remap) - known or any(not isinstance(v, str) or not v.strip() for v in remap.values()):
        raise ValueError('Unknown workflow mapping or empty ID')
    if len({remap.get(i, i) for i in known}) != len(known):
        raise ValueError('Workflow IDs must remain unique')

    def replace(value):
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace(v) for v in value]
        if isinstance(value, str):
            for key, replacement in values.items():
                value = value.replace(key, replacement)
            return remap.get(value, value)
        return value

    prepared = [(w['file'], replace(json.loads((ROOT / 'n8n/workflows' / w['file']).read_text()))) for w in manifest]
    output.mkdir(parents=True)
    for filename, data in prepared:
        (output / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return len(prepared)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / '.work/n8n-configured')
    args = parser.parse_args()
    try:
        count = prepare(json.loads(args.config.read_text()), args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Cannot prepare workflows: {exc}\n')
    print(f'Prepared {count} inactive workflow copies under .work/. No credentials were created or sent.')
