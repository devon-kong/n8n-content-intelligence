"""Tests for decide create/update/skip."""

from article_catch.models import Article
from article_catch.ops.feishu_upsert import (
    CATCH_FIELD_WHITELIST,
    article_to_catch_fields,
    decide_actions,
)
from article_catch.util.feishu_fields import make_url_field


def test_catch_field_whitelist():
    assert set(CATCH_FIELD_WHITELIST) == {
        "标题",
        "markdown",
        "发布时间",
        "地址",
        "账号",
        "article_id",
    }


def test_article_to_catch_fields_keys():
    a = Article(
        article_id="wx_1",
        title="t",
        markdown="m",
        published_at="2026-01-01T00:00:00Z",
        url="https://example.com",
        account="acc",
        publish_time_ms=1_704_067_200_000,
    )
    fields = article_to_catch_fields(a)
    assert set(fields.keys()) <= set(CATCH_FIELD_WHITELIST)
    assert fields["article_id"] == "wx_1"
    assert fields["地址"]["link"] == "https://example.com"
    assert "summary_status" not in fields


def test_decide_create():
    a = Article(article_id="wx_new", title="t", markdown="m", url="https://u", account="a", publish_time_ms=1)
    decisions = decide_actions([a], {})
    assert decisions[0].action == "create"


def test_decide_skip_unchanged():
    a = Article(
        article_id="wx_1",
        title="标题",
        markdown="不同 markdown 不应影响 skip",
        url="https://example.com/a",
        account="账号A",
        publish_time_ms=1700000000000,
    )
    existing = {
        "wx_1": {
            "record_id": "rec1",
            "fields": {
                "article_id": "wx_1",
                "标题": "标题",
                "发布时间": 1700000000000,
                "地址": make_url_field("https://example.com/a", "标题"),
                "账号": "账号A",
            },
        }
    }
    d = decide_actions([a], existing)[0]
    assert d.action == "skip"
    assert d.record_id == "rec1"


def test_decide_update_on_title_change():
    a = Article(
        article_id="wx_1",
        title="新标题",
        markdown="m",
        url="https://example.com/a",
        account="账号A",
        publish_time_ms=1700000000000,
    )
    existing = {
        "wx_1": {
            "record_id": "rec1",
            "fields": {
                "article_id": "wx_1",
                "标题": "旧标题",
                "发布时间": 1700000000000,
                "地址": {"link": "https://example.com/a", "text": "旧标题"},
                "账号": "账号A",
            },
        }
    }
    d = decide_actions([a], existing)[0]
    assert d.action == "update"
    assert "标题" in d.changed_fields
