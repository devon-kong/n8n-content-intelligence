"""Tests for util.article / html_md / text_norm."""

from article_catch.models import Article
from article_catch.util.article import (
    articles_from_feed,
    dedupe_by_article_id,
    filter_by_window,
    normalize_feed_item,
    parse_date,
    stable_hash,
)
from article_catch.util.html_md import clean_markdown, html_to_markdown, strip_html
from article_catch.util.text_norm import skip_fingerprint


def test_stable_hash_prefix():
    h = stable_hash("https://mp.weixin.qq.com/s/abc")
    assert h.startswith("wx_")
    assert stable_hash("https://mp.weixin.qq.com/s/abc") == h


def test_stable_hash_deterministic_diff():
    assert stable_hash("a") != stable_hash("b")


def test_dedupe_by_article_id():
    items = [
        Article(article_id="a1", title="t1"),
        Article(article_id="a1", title="t1-dup"),
        Article(article_id="a2", title="t2"),
        Article(article_id="", title="no-id"),
    ]
    out = dedupe_by_article_id(items)
    assert [a.article_id for a in out] == ["a1", "a2"]


def test_normalize_feed_item_html():
    a = normalize_feed_item(
        {
            "title": "Hello",
            "url": "https://example.com/x",
            "date_published": "2026-07-01T12:00:00Z",
            "content_html": "<p>正文<strong>加粗</strong></p><img src='x'>",
        },
        account_name="acct",
    )
    assert a is not None
    assert a.article_id.startswith("wx_")
    assert a.title == "Hello"
    assert a.account == "acct"
    assert "正文" in a.markdown
    assert "**加粗**" in a.markdown
    assert "<img" not in a.markdown


def test_normalize_skips_empty_markdown():
    a = normalize_feed_item({"title": "t", "url": "https://x.com", "content_html": ""})
    # content empty after clean → None
    assert a is None or a.markdown  # if only title-based empty content returns None


def test_clean_markdown_noise():
    md = "正文\n\n阅读原文\nhttps://example.com/only\n---\n更多"
    out = clean_markdown(md)
    assert "阅读原文" not in out
    assert "https://example.com/only" not in out
    assert "正文" in out


def test_html_to_markdown_strip_script():
    out = html_to_markdown("<script>evil()</script><p>ok</p>")
    assert "evil" not in out
    assert "ok" in out


def test_strip_html():
    assert strip_html("<b>hi</b>") == "hi"


def test_parse_date_ms():
    d = parse_date(1_704_067_200_000)
    assert d is not None
    assert d.year >= 2023


def test_filter_by_window_old_dropped():
    old = Article(article_id="1", published_at="2020-01-01T00:00:00Z", title="o")
    new = Article(article_id="2", published_at="2099-01-01T00:00:00Z", title="n")
    out = filter_by_window([old, new], window_days=7)
    assert all(a.article_id != "1" for a in out)


def test_articles_from_feed():
    feed = {
        "title": "Feed",
        "items": [
            {
                "title": "T1",
                "url": "https://mp.weixin.qq.com/s/1",
                "date_published": "2099-06-01T00:00:00Z",
                "content_html": "<p>hello world content</p>",
            }
        ],
    }
    arts = articles_from_feed(feed, account_name="A", account_biz_id="biz", window_days=36500)
    assert len(arts) == 1
    assert arts[0].title == "T1"


def test_skip_fingerprint_no_markdown():
    fp = skip_fingerprint("t", "2020", "https://u", "acc")
    assert len(fp) == 4
