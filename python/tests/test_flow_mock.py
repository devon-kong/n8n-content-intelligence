"""End-to-end central kitchen with fully mocked HTTP."""

from __future__ import annotations

import httpx
import respx

from article_catch.clients.feishu import FeishuClient
from article_catch.clients.jizhile import JizhileClient
from article_catch.clients.llm import LlmClient
from article_catch.clients.wechat2rss import Wechat2RssClient
from article_catch.config import Settings
from article_catch.flows.central_kitchen import load_pipeline_config, run_one
from article_catch.stages.catch import run_catch
from article_catch.store.sqlite_log import SqliteLog


def _settings(tmp_path) -> Settings:
    return Settings(
        FEISHU_APP_ID="app",
        FEISHU_APP_SECRET="sec",
        FEISHU_CONFIG_BASE="cfgbase",
        FEISHU_LIST_TABLE="listtbl",
        FEISHU_CONFIG_TABLE="cfgtbl",
        WECHAT2RSS_BASE="http://w2r.test",
        LLM_API_KEY="k",
        LLM_BASE_URL="https://llm.test",
        JIZHILE_BASE_URL="https://jz.test/api",
        SQLITE_PATH=str(tmp_path / "log.db"),
    )


@respx.mock
def test_catch_create_update_skip(tmp_path):
    settings = _settings(tmp_path)
    respx.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal").respond(
        200, json={"code": 0, "tenant_access_token": "tok", "expire": 7200}
    )
    # list accounts
    respx.post(
        "https://open.feishu.cn/open-apis/bitable/v1/apps/cfgbase/tables/listtbl/records/search"
    ).respond(
        200,
        json={
            "code": 0,
            "data": {
                "has_more": False,
                "items": [
                    {
                        "record_id": "acc1",
                        "fields": {"biz_id": "biz1", "账号名称": "号1", "是否启用": True, "pipeline_key": "industry_news"},
                    }
                ],
            },
        },
    )
    # feed
    respx.get("http://w2r.test/feed/biz1.json").respond(
        200,
        json={
            "items": [
                {
                    "title": "文章一",
                    "url": "https://mp.weixin.qq.com/s/art1",
                    "date_published": "2099-07-01T00:00:00Z",
                    "content_html": "<p>正文内容足够长</p>",
                }
            ]
        },
    )
    # existing search → empty → create
    respx.post(
        "https://open.feishu.cn/open-apis/bitable/v1/apps/tgtbase/tables/tgttbl/records/search"
    ).mock(
        side_effect=[
            httpx.Response(200, json={"code": 0, "data": {"items": [], "has_more": False}}),
            # visibility search
            httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "record_id": "rnew",
                                "fields": {
                                    "article_id": None,  # filled below dynamically hard
                                    "markdown": "正文内容足够长",
                                    "地址": {"link": "https://mp.weixin.qq.com/s/art1", "text": "文章一"},
                                },
                            }
                        ],
                        "has_more": False,
                    },
                },
            ),
        ]
    )
    created = {}

    def on_create(request):
        import json as _json

        body = _json.loads(request.content)
        created["fields"] = body["fields"]
        aid = body["fields"]["article_id"]
        # patch visibility response article_id
        return httpx.Response(200, json={"code": 0, "data": {"record": {"record_id": "rnew", "fields": body["fields"]}}})

    respx.post("https://open.feishu.cn/open-apis/bitable/v1/apps/tgtbase/tables/tgttbl/records").mock(
        side_effect=on_create
    )

    # Fix visibility: intercept search after create and inject article_id from created
    search_calls = {"n": 0}

    def on_search(request):
        search_calls["n"] += 1
        if search_calls["n"] == 1:
            return httpx.Response(200, json={"code": 0, "data": {"items": [], "has_more": False}})
        aid = created.get("fields", {}).get("article_id", "wx_x")
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "items": [
                        {
                            "record_id": "rnew",
                            "fields": {
                                "article_id": aid,
                                "markdown": "正文内容足够长",
                                "地址": {
                                    "link": "https://mp.weixin.qq.com/s/art1",
                                    "text": "文章一",
                                },
                            },
                        }
                    ],
                    "has_more": False,
                },
            },
        )

    respx.post(
        "https://open.feishu.cn/open-apis/bitable/v1/apps/tgtbase/tables/tgttbl/records/search"
    ).mock(side_effect=on_search)

    with httpx.Client() as http:
        feishu = FeishuClient("app", "sec", client=http)
        w2r = Wechat2RssClient("http://w2r.test", client=http)
        report = run_catch(
            "industry_news",
            "tgtbase",
            "tgttbl",
            36500,
            settings=settings,
            feishu=feishu,
            w2r=w2r,
        )
    assert report.created == 1
    assert report.article_count == 1
    assert report.visibility_ok is True
    assert "summary_status" not in created["fields"]
    assert set(created["fields"].keys()) <= {"标题", "markdown", "发布时间", "地址", "账号", "article_id"}


@respx.mock
def test_load_pipeline_config(tmp_path):
    settings = _settings(tmp_path)
    respx.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal").respond(
        200, json={"code": 0, "tenant_access_token": "tok", "expire": 7200}
    )
    respx.post(
        "https://open.feishu.cn/open-apis/bitable/v1/apps/cfgbase/tables/cfgtbl/records/search"
    ).respond(
        200,
        json={
            "code": 0,
            "data": {
                "items": [
                    {
                        "fields": {
                            "pipeline_key": "benchmark",
                            "是否启用": True,
                            "summary_enabled": True,
                            "metric_enabled": True,
                            "process_mode": "benchmark",
                            "target_base": "B1",
                            "target_table": "T1",
                            "window_days": "7",
                            "summary_prompt": "请摘要",
                            "summary_version": "v1",
                            "model": "deepseek-v4-flash",
                        }
                    }
                ]
            },
        },
    )
    with httpx.Client() as http:
        cfg = load_pipeline_config(
            "benchmark",
            settings=settings,
            feishu=FeishuClient("app", "sec", client=http),
        )
    assert cfg.summary_enabled is True
    assert cfg.process_mode == "benchmark"
    assert cfg.target_base == "B1"
