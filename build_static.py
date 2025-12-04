"""
Utility script to render every FastAPI page into plain HTML files so the site
can be hosted statically (e.g. on GitHub Pages).

Usage:
    python build_static.py

Output:
    ./static_site/
        index.html
        Basics/Overview/index.html
        ...
        static/ (copied assets)
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from main import app, list_pages, BASE_DIR, STATIC_DIR  # type: ignore

OUTPUT_DIR = BASE_DIR / "static_site"
# Set this to the public prefix you will host from, e.g.
# "https://username.github.io/repo/static_site"
# Leave empty to use relative links (good for local file:// testing).
PUBLIC_BASE = r"github.com/WilliamChristopherAlt/TetrisGuide/static_site"


def rewrite_paths(html: str, page_path: str, base_url: str) -> str:
    """Rewrite asset and internal links so they work in a static context."""
    static_prefix = compute_static_prefix(page_path, base_url)
    root_prefix = compute_root_prefix(page_path, base_url)

    replacements = [
        ('href="/static/', f'href="{static_prefix}/'),
        ("href='/static/", f"href='{static_prefix}/"),
        ('src="/static/', f'src="{static_prefix}/'),
        ("src='/static/", f"src='{static_prefix}/"),
        ('href="http://testserver/static/', f'href="{static_prefix}/'),
        ("href='http://testserver/static/", f"href='{static_prefix}/"),
        ('src="http://testserver/static/', f'src="{static_prefix}/'),
        ("src='http://testserver/static/", f"src='{static_prefix}/"),
    ]
    for old, new in replacements:
        html = html.replace(old, new)

    def convert_href(match):
        path = match.group(1)
        if not path or path.startswith("static/"):
            target = f"{root_prefix}index.html"
        else:
            if "?" in path or "#" in path:
                return match.group(0)
            encoded = quote(path, safe="/:")
            target = f"{root_prefix}{encoded}/index.html"
        return f'href="{target}"'

    def convert_href_single(match):
        path = match.group(1)
        if not path or path.startswith("static/"):
            target = f"{root_prefix}index.html"
        else:
            if "?" in path or "#" in path:
                return match.group(0)
            encoded = quote(path, safe="/:")
            target = f"{root_prefix}{encoded}/index.html"
        return f"href='{target}'"

    html = re.sub(r'href="http://testserver/([^"]*)"', convert_href, html)
    html = re.sub(r"href='http://testserver/([^']*)'", convert_href_single, html)

    html = html.replace(
        'window.location.href = "/" + name;',
        f'window.location.href = "{root_prefix}" + name + "/index.html";',
    )

    return html


def compute_static_prefix(page_path: str, base_url: str) -> str:
    """Return the correct static prefix for a page path."""
    if base_url:
        return f"{base_url.rstrip('/')}/static"
    if not page_path:
        return "static"
    depth = len(Path(page_path).parts)
    relative = "../" * depth
    return f"{relative}static"


def compute_root_prefix(page_path: str, base_url: str) -> str:
    """Return the correct root prefix for internal links."""
    if base_url:
        return base_url.rstrip("/") + "/"
    if not page_path:
        return ""
    depth = len(Path(page_path).parts)
    return "../" * depth


def dump_route(
    client: TestClient,
    route: str,
    target_dir: Path,
    page_path: str,
    base_url: str,
) -> None:
    """Request a route and write the HTML to target_dir/index.html."""
    print(f"Rendering {route}")
    response = client.get(route)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to render {route}: {response.status_code}")

    output_file = target_dir / "index.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    html = rewrite_paths(response.text, page_path, base_url)
    output_file.write_text(html, encoding="utf-8")


def copy_static_assets() -> None:
    """Copy /static files into the static build directory."""
    dest = OUTPUT_DIR / "static"
    shutil.copytree(STATIC_DIR, dest)


def main() -> None:
    base_url = PUBLIC_BASE.rstrip("/")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    copy_static_assets()

    with TestClient(app) as client:
        # Root index
        dump_route(client, "/", OUTPUT_DIR, "", base_url)

        # Individual content pages
        for page_path in list_pages():
            route = f"/{page_path}"
            target_dir = OUTPUT_DIR / Path(page_path)
            dump_route(client, route, target_dir, page_path, base_url)

    print(f"Static site exported to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

