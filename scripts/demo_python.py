"""Offline synthetic catch demonstration; no clients, credentials or writes."""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from article_catch.util.article import articles_from_feed
from article_catch.ops.feishu_upsert import article_to_catch_fields, decide_actions

fixture = json.loads((ROOT / "examples/catch-scenario.json").read_text())
# Freeze the boundary explicitly; do not depend on today's date.
from article_catch.util.article import normalize_feed_item, dedupe_by_article_id
cutoff = datetime.fromisoformat(fixture["as_of"].replace("Z", "+00:00")).timestamp() - fixture["window_days"] * 86400
articles = [normalize_feed_item(i, account_name=fixture["account"]["account_name"], account_biz_id=fixture["account"]["biz_id"]) for i in fixture["feed"]["items"]]
articles = dedupe_by_article_id([a for a in articles if a and (a.publish_time_ms is None or a.publish_time_ms / 1000 >= cutoff)])
existing = {a.article_id: {"record_id": f"demo-record-{idx + 1}", "fields": article_to_catch_fields(a)} for idx, a in enumerate(articles[1:])}
existing[articles[1].article_id]["fields"]["标题"] = "Previous export outlook"
existing[articles[2].article_id]["fields"]["markdown"] = "Different stored markdown formatting"
decisions = decide_actions(articles, existing)
result = {
    "mode": "synthetic_fixture",
    "runtime": "Python normalization and upsert decision functions; no external calls",
    "as_of": fixture["as_of"],
    "counts": {a: sum(d.action == a for d in decisions) for a in ["create", "update", "skip"]},
    "decisions": [{"article_id": d.article.article_id, "title": d.article.title, "action": d.action} for d in decisions],
}
print(json.dumps(result, ensure_ascii=False, indent=2))
