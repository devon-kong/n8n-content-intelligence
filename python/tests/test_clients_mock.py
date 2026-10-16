"""HTTP clients with respx mocks."""

import httpx
import respx

from article_catch.clients.feishu import FeishuClient
from article_catch.clients.jizhile import JizhileClient, to_number
from article_catch.clients.llm import LlmClient
from article_catch.clients.wechat2rss import Wechat2RssClient


@respx.mock
def test_feishu_token_and_search():
    respx.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal").respond(
        200, json={"code": 0, "tenant_access_token": "t-abc", "expire": 7200}
    )
    respx.post(
        "https://open.feishu.cn/open-apis/bitable/v1/apps/base1/tables/tbl1/records/search"
    ).respond(200, json={"code": 0, "data": {"items": [{"record_id": "r1", "fields": {}}], "has_more": False}})

    with httpx.Client() as http:
        c = FeishuClient("id", "secret", client=http)
        assert c.tenant_token() == "t-abc"
        data = c.search_records("base1", "tbl1", page_size=10)
        assert data["code"] == 0


@respx.mock
def test_wechat2rss_fetch():
    respx.get("http://127.0.0.1:8080/feed/biz1.json").respond(
        200, json={"items": [{"title": "t", "url": "u", "content_html": "<p>x</p>"}]}
    )
    with httpx.Client() as http:
        c = Wechat2RssClient("http://127.0.0.1:8080", client=http)
        feed = c.fetch_feed("biz1")
        assert "items" in feed


@respx.mock
def test_llm_chat():
    respx.post("https://api.deepseek.com/v1/chat/completions").respond(
        200,
        json={"choices": [{"message": {"content": "  摘要结果  "}}]},
    )
    with httpx.Client() as http:
        c = LlmClient("key", "https://api.deepseek.com", client=http)
        out = c.chat("deepseek-chat", [{"role": "user", "content": "hi"}])
        assert out == "摘要结果"


@respx.mock
def test_jizhile_success():
    respx.post("https://www.dajiala.com/fbmain/monitor/v3/read_zan_pro").respond(
        200,
        json={
            "code": 0,
            "data": {
                "read": "1.2万",
                "zan": 3,
                "looking": "10+",
                "share_num": 1,
                "collect_num": 2,
                "comment_count": 4,
            },
        },
    )
    with httpx.Client() as http:
        c = JizhileClient(client=http)
        m = c.fetch_metrics("https://mp.weixin.qq.com/s/x")
        assert m["status"] == "success"
        assert m["read_count"] == 12000
        assert m["like_count"] == 3


def test_to_number():
    assert to_number("1.5万") == 15000
    assert to_number("10+") == 10
    assert to_number(None) == 0
