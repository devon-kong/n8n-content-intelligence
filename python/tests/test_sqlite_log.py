"""SqliteLog unit tests."""

from article_catch.store.sqlite_log import SqliteLog


def test_summary_lock_and_success(tmp_path):
    db = SqliteLog(tmp_path / "t.db")
    db.init_schema()
    key = "v1:model:wx_1"
    assert db.summary_get_success(key) is None
    r = db.summary_acquire_lock(
        task_key=key,
        article_id="wx_1",
        run_id="run1",
        record_id="rec1",
        model="m",
        prompt_version="v1",
    )
    assert r == "CLAIMED"
    r2 = db.summary_acquire_lock(
        task_key=key,
        article_id="wx_1",
        run_id="run2",
        record_id="rec1",
        model="m",
        prompt_version="v1",
    )
    assert r2 == "ALREADY_PROCESSING"
    db.summary_mark_success(key, "run1", "摘要正文")
    hit = db.summary_get_success(key)
    assert hit is not None
    assert hit["result"]["summary"] == "摘要正文"
    r3 = db.summary_acquire_lock(
        task_key=key,
        article_id="wx_1",
        run_id="run3",
        record_id="rec1",
        model="m",
        prompt_version="v1",
    )
    assert r3 == "ALREADY_SUCCESS"


def test_metrics_cache(tmp_path):
    db = SqliteLog(tmp_path / "m.db")
    db.init_schema()
    r = db.metrics_acquire_lock(article_id="a1", run_id="r1", record_id="rec", url="https://u")
    assert r == "CLAIMED"
    db.metrics_mark_success(
        "a1",
        "r1",
        {
            "read_count": 10,
            "like_count": 2,
            "wow_count": 1,
            "share_count": 0,
            "collect_count": 0,
            "comment_count": 3,
        },
    )
    fresh = db.metrics_get_fresh_success("a1")
    assert fresh is not None
    assert fresh["read_count"] == 10


import pytest


@pytest.mark.parametrize('stage', ['summary', 'metrics'])
@pytest.mark.parametrize('origin', ['expired', 'response'])
def test_uncertainty_persists_across_restarts(tmp_path, stage, origin):
    path = tmp_path / 'calls.sqlite'
    store = SqliteLog(path)
    args = dict(article_id='a1', run_id='r1', record_id='demo', lock_ttl_ms=-1)
    if stage == 'summary':
        args.update(task_key='v1:m:a1', model='m', prompt_version='v1')
    else:
        args.update(url='https://example.test/a1')
    acquire = getattr(store, f'{stage}_acquire_lock')
    assert acquire(**args) == 'CLAIMED'
    if origin == 'expired':
        assert acquire(**{**args, 'run_id': 'r2'}) == 'LOCK_EXPIRED_REVIEW'
    else:
        getattr(store, f'{stage}_mark_non_success')(
            'v1:m:a1' if stage == 'summary' else 'a1', 'r1', 'uncertain', 'TIMEOUT', 'synthetic timeout')
    restarted = SqliteLog(path)
    for run in ['r3', 'r4']:
        assert getattr(restarted, f'{stage}_acquire_lock')(**{**args, 'run_id': run}) == 'UNCERTAIN_REVIEW'


@pytest.mark.parametrize('stage', ['summary', 'metrics'])
def test_reviewed_uncertainty_can_be_retried(tmp_path, stage):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('review_paid_calls', Path(__file__).resolve().parents[2] / 'scripts/review_paid_calls.py')
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)
    path = tmp_path / 'calls.sqlite'
    store = SqliteLog(path)
    args = dict(article_id='a1', run_id='r1', record_id='demo', lock_ttl_ms=-1)
    if stage == 'summary':
        args.update(task_key='v1:m:a1', model='m', prompt_version='v1')
    else:
        args.update(url='https://example.test/a1')
    acquire = getattr(store, f'{stage}_acquire_lock')
    assert acquire(**args) == 'CLAIMED'
    assert acquire(**args) == 'LOCK_EXPIRED_REVIEW'
    review.approve_retry(path, stage, 1, 'Synthetic remote request settled; cost accepted', 'demo-operator')
    assert getattr(SqliteLog(path), f'{stage}_acquire_lock')(**{**args, 'run_id': 'r3'}) == 'CLAIMED'
