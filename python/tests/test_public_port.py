"""Compatibility regressions discovered while preparing the public snapshot."""

import httpx
import respx

from article_catch.clients.wechat2rss import Wechat2RssClient
from article_catch.util.article import stable_hash


@respx.mock
def test_feed_auth_uses_same_k_query_parameter_as_n8n():
    route = respx.get("https://feed.example.test/feed/demo.json").respond(200, json={"items": []})
    with httpx.Client() as http:
        client = Wechat2RssClient("https://feed.example.test", "synthetic-test-key", client=http)
        client.fetch_feed("demo")
    assert dict(route.calls.last.request.url.params) == {"k": "synthetic-test-key"}


def test_article_id_matches_javascript_utf16_for_non_bmp_url():
    # Expected value executed from the exported n8n stableHash function.
    assert stable_hash("https://example.com/😀") == "wx_1n15pietxkl"
    assert stable_hash("😀") == "wx_2b93dkjpbgy"
