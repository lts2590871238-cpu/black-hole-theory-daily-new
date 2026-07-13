"""Command-line interface for updates, builds, validation, demo and local serving."""

from __future__ import annotations

import argparse
import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from theory_daily.config import load_settings, load_topics
from theory_daily.demo import demo_papers
from theory_daily.health import validate_dist
from theory_daily.logging_config import configure_logging
from theory_daily.models import PaperCollection
from theory_daily.pipeline import update
from theory_daily.render import build_site, load_published_papers
from theory_daily.storage import ensure_directories, write_json


def _root(path: str | None) -> Path:
    root = Path(path).resolve() if path else Path.cwd().resolve()
    if not (root / "pyproject.toml").exists() or not (root / "config").is_dir():
        raise RuntimeError(f"找不到项目根目录：{root}")
    return root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="黑洞与引力理论每日论文精选")
    parser.add_argument("--root", help="项目根目录，默认当前目录")
    parser.add_argument("--verbose", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    update_parser = commands.add_parser("update", help="抓取、筛选、翻译并构建")
    update_parser.add_argument("--since-days", type=int, default=None)
    commands.add_parser("build", help="用正式历史重新生成静态站点")
    commands.add_parser("validate", help="验证 dist 静态输出")
    demo_parser = commands.add_parser("demo", help="生成不访问网络的演示站")
    demo_parser.add_argument("--fixtures", action="store_true", help="使用内置 8 篇虚构夹具")
    serve_parser = commands.add_parser("serve", help="在本地预览 dist")
    serve_parser.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = _root(args.root)
        configure_logging(root, verbose=args.verbose)
        ensure_directories(root)
        settings, topics = load_settings(root), load_topics(root)
        if args.command == "update":
            report = update(root, settings, topics, since_days=args.since_days)
            print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
            return 0
        if args.command == "build":
            output = build_site(root, load_published_papers(root), settings, topics)
            print(f"静态站点已生成：{output}")
            return 0
        if args.command == "demo":
            papers = demo_papers()
            collection = PaperCollection(generated_at=papers[0].published_at, papers=papers)
            write_json(root / "data" / "demo" / "papers.json", collection)
            output = build_site(root, papers, settings, topics, demo=True)
            errors = validate_dist(output)
            if errors:
                raise RuntimeError("演示站验证失败：" + "; ".join(errors))
            print(f"离线演示已生成：{output}（{len(papers)} 篇明确标记的虚构示例）")
            return 0
        if args.command == "validate":
            errors = validate_dist(root / "dist")
            if errors:
                print("静态输出验证失败：", file=sys.stderr)
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            print("静态输出验证通过")
            return 0
        if args.command == "serve":
            dist = root / "dist"
            if not (dist / "index.html").exists():
                raise RuntimeError("dist/index.html 不存在；请先运行 build 或 demo --fixtures")
            handler = partial(SimpleHTTPRequestHandler, directory=str(dist))
            server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
            print(f"本地预览：http://127.0.0.1:{args.port} （Ctrl+C 停止）")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                server.server_close()
            return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
