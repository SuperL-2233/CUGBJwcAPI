from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .api import ApiApplication, NoticeCollection
from .client import NoticeClient
from .cms_client import CmsNoticeClient
from .repository import NoticeRepository
from .server import serve
from .settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cugb-api",
        description="公开通知列表只读 JSON API",
    )
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--verbose", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    serve_parser = commands.add_parser("serve", help="启动 HTTP API 服务")
    serve_parser.add_argument("--host", help="覆盖监听地址")
    serve_parser.add_argument("--port", type=int, help="覆盖监听端口")
    commands.add_parser("check-config", help="检查配置但不访问网络")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        settings = load_settings(args.config)
        if args.command == "check-config":
            print("配置有效。")
            return 0
        host = args.host or settings.server.host
        port = args.port if args.port is not None else settings.server.port
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        client = NoticeClient(
            settings.source_url,
            timeout_seconds=settings.request_timeout_seconds,
            retries=settings.request_retries,
        )
        repository = NoticeRepository(client, settings.cache_ttl_seconds)
        teaching_updates_client = NoticeClient(
            settings.teaching_updates_url,
            timeout_seconds=settings.request_timeout_seconds,
            retries=settings.request_retries,
        )
        extra_collections = {
            "/api/v1/teaching-updates": NoticeCollection(
                NoticeRepository(
                    teaching_updates_client, settings.cache_ttl_seconds
                ),
                settings.teaching_updates_url,
            )
        }
        for prefix, source_url in {
            "/api/v1/ai-college/news": settings.ai_college.news_url,
            "/api/v1/ai-college/notices": settings.ai_college.notices_url,
        }.items():
            ai_college_client = CmsNoticeClient(
                source_url,
                timeout_seconds=settings.request_timeout_seconds,
                retries=settings.request_retries,
            )
            extra_collections[prefix] = NoticeCollection(
                NoticeRepository(ai_college_client, settings.cache_ttl_seconds),
                source_url,
            )
        for prefix, source_url in {
            "/api/v1/student-affairs/news": settings.student_affairs.news_url,
            "/api/v1/student-affairs/notices": settings.student_affairs.notices_url,
        }.items():
            student_affairs_client = CmsNoticeClient(
                source_url,
                timeout_seconds=settings.request_timeout_seconds,
                retries=settings.request_retries,
                detail_path_prefix="/xgb/c",
            )
            extra_collections[prefix] = NoticeCollection(
                NoticeRepository(student_affairs_client, settings.cache_ttl_seconds),
                source_url,
            )
        serve(
            ApiApplication(
                repository,
                settings.source_url,
                extra_collections=extra_collections,
            ),
            host,
            port,
        )
        return 0
    except KeyboardInterrupt:
        print("已停止。")
        return 0
    except Exception as error:
        logging.error("%s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
