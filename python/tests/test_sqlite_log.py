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
