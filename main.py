from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
CONTENT_ROOT = BASE_DIR / "content"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


app = FastAPI(title="Tetris Guide Blog")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _iter_page_folders() -> List[Path]:
    """
    Recursively find all page folders under CONTENT_ROOT.
    A page folder is any directory that contains a 'page.txt' file.
    """
    if not CONTENT_ROOT.exists():
        return []

    page_dirs: List[Path] = []
    # Find all 'page.txt' files anywhere under CONTENT_ROOT and treat their
    # parent directories as page folders.
    for page_file in CONTENT_ROOT.rglob("page.txt"):
        parent = page_file.parent
        # Skip technical folders we don't want to expose as pages
        if parent.name in {"boards", "pages", "boards_old"}:
            continue
        page_dirs.append(parent)
    return page_dirs


def list_pages() -> List[str]:
    """
    Return list of available page paths (relative to CONTENT_ROOT),
    e.g. 'openers/t-spin-basics', 'misc/demo'.
    """
    pages: List[str] = []
    for page_dir in _iter_page_folders():
        rel = page_dir.relative_to(CONTENT_ROOT)
        # Use POSIX-style path (with forward slashes) for URLs
        pages.append(rel.as_posix())
    pages.sort()
    return pages


def page_has_valid_boards(page_path: str) -> bool:
    """Check if a page references only existing board files."""
    import re
    try:
        page_file = CONTENT_ROOT / page_path / "page.txt"
        if not page_file.exists():
            return False
        
        content = page_file.read_text(encoding="utf-8")
        board_pattern = re.compile(
            r"\[\[\s*(BOARD|BOARDS)\s*:\s*([^\]]+?)\s*\]\]",
            flags=re.IGNORECASE,
        )
        
        for match in board_pattern.finditer(content):
            payload = match.group(2)
            filenames = [p.strip() for p in payload.split(",") if p.strip()]
            for filename in filenames:
                board_path = CONTENT_ROOT / page_path / "boards" / filename
                if not board_path.exists():
                    return False
        return True
    except Exception:
        return False


def build_sidebar_tree() -> List[Dict[str, Any]]:
    """
    Build a simple directory tree for the sidebar.

    Structure:
    [
      {
        "type": "dir",
        "name": "openers",
        "children": [
          {"type": "page", "name": "T-Spin Basics", "path": "openers/t-spin-basics"},
          ...
        ],
      },
      ...
    ]
    """
    pages = list_pages()
    # Build hierarchical tree: top-level dirs, optional second-level dirs, then pages
    tree: Dict[str, Dict[str, Any]] = {}
    for page_path in pages:
        # Skip pages that reference non-existent board files
        if not page_has_valid_boards(page_path):
            continue
        parts = page_path.split("/")
        if len(parts) == 1:
            top_key = "root"
            subdir = None
            name = parts[0]
        elif len(parts) == 2:
            top_key = parts[0]
            subdir = None
            name = parts[1]
        else:
            top_key = parts[0]
            subdir = parts[1]
            name = parts[-1]

        if top_key not in tree:
            pretty_top = top_key.replace("-", " ").title() if top_key != "root" else "Root"
            tree[top_key] = {
                "type": "dir",
                "name": pretty_top,
                "key": top_key,
                "children": [],
            }

        top_node = tree[top_key]
        pretty_name = name.replace("-", " ").title()

        if subdir:
            # Find or create subdirectory node
            sub_node = None
            for child in top_node["children"]:
                if child.get("type") == "dir" and child.get("key") == subdir:
                    sub_node = child
                    break
            if sub_node is None:
                sub_node = {
                    "type": "dir",
                    "name": subdir.replace("-", " ").title(),
                    "key": subdir,
                    "children": [],
                }
                top_node["children"].append(sub_node)
            sub_node["children"].append(
                {"type": "page", "name": pretty_name, "path": page_path}
            )
        else:
            top_node["children"].append(
                {"type": "page", "name": pretty_name, "path": page_path}
            )

    # Define desired page order for each directory (using directory/page names as they appear in filesystem)
    page_order_map: Dict[str, List[str]] = {
        "Basics": ["Overview", "T-Spin Double", "T-Spin Triple"],
        "Single Double": ["Main setup"],
        "Double Double": ["Fractal", "Cut Copy", "STSD & Imperial Cross"],
        "Double Triple": ["DT Cannon", "DT Cannon 2", "BT Cannon"],
        "Super T-Spin Double": ["Main setup", "Used in spliced setups"],
        "Imperial Cross": ["Main setup", "Used in spliced setups"],
        "C-Spin": ["Main setup"],
        "Advanced": [
            "Spliced STSD variants",
            "Sandwhiching a setup with notch and base",
            "Sandwhiching a T-Spin Triple",
            "Layering a setup on top of a setup",
            "Sandwhiching a set up inside a setup",
        ],
    }
    
    # Helper function to extract page key from path
    def get_page_key_from_path(path: str) -> str:
        """Extract the page directory name from a page path."""
        parts = path.split("/")
        return parts[-1] if parts else ""
    
    # Sort children inside each directory (dirs first, then pages in desired order)
    def sort_children(children: List[Dict[str, Any]], parent_key: str = "") -> None:
        for child in children:
            if child.get("type") == "dir":
                sort_children(child["children"], child.get("key", ""))
        
        # Separate dirs and pages
        dirs = [c for c in children if c.get("type") == "dir"]
        pages = [c for c in children if c.get("type") == "page"]
        
        # Sort pages according to desired order
        if parent_key in page_order_map:
            order_list = page_order_map[parent_key]
            # Create a map from page key (directory name) to page dict
            page_map = {}
            for p in pages:
                page_key = get_page_key_from_path(p.get("path", ""))
                page_map[page_key] = p
            
            ordered_pages = []
            seen_keys = set()
            
            # Add pages in desired order (matching by directory name)
            for order_name in order_list:
                if order_name in page_map:
                    ordered_pages.append(page_map[order_name])
                    seen_keys.add(order_name)
            
            # Add any remaining pages not in the order list (alphabetically)
            remaining = [p for p in pages if get_page_key_from_path(p.get("path", "")) not in seen_keys]
            remaining.sort(key=lambda p: p["name"].lower())
            ordered_pages.extend(remaining)
            
            # Rebuild children list: dirs first, then ordered pages
            children.clear()
            children.extend(sorted(dirs, key=lambda c: c.get("name", "").lower()))
            children.extend(ordered_pages)
        else:
            # Default alphabetical sort if no order specified
            children.sort(
                key=lambda c: (c.get("type") != "dir", c.get("name", "").lower())
            )

    for node in tree.values():
        sort_children(node["children"], node.get("key", ""))

    # Produce an ordered list according to user's desired order
    desired_order = [
        "Basics",
        "Single Double",
        "Double Double",
        "Double Triple",
        "Super T-Spin Double",
        "Imperial Cross",
        "C-Spin",
        "Advanced",
    ]
    
    # Build ordered list preserving user's desired order
    ordered: List[Dict[str, Any]] = []
    seen_keys = set()
    
    # Add directories in desired order
    for key in desired_order:
        if key in tree:
            ordered.append(tree[key])
            seen_keys.add(key)
    
    # Add any remaining directories not in the desired order (alphabetically)
    for key in sorted(tree.keys()):
        if key not in seen_keys:
            ordered.append(tree[key])
    
    return ordered


def base_context(**extra: Any) -> Dict[str, Any]:
    """Common template context."""
    # Only expose pages that have valid board references
    valid_pages = [p for p in list_pages() if page_has_valid_boards(p)]
    ctx: Dict[str, Any] = {
        "year": datetime.now().year,
        "sidebar_tree": build_sidebar_tree(),
        "all_pages": valid_pages,
    }
    ctx.update(extra)
    return ctx


def read_page_source(page_path: str) -> str:
    """Load raw text for a page from its folder."""
    page_dir = CONTENT_ROOT / page_path
    page_file = page_dir / "page.txt"
    if not page_file.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return page_file.read_text(encoding="utf-8")


def read_board(page_path: str, board_filename: str) -> Dict[str, Any]:
    """
    Read a board text file for a given page.

    Supports optional metadata header at the top:
      # PIECES: i, o, t

    Returns:
      {
        "rows": [...],
        "pieces": ["i", "o", "t"] or None,
      }
    """
    board_path = CONTENT_ROOT / page_path / "boards" / board_filename
    if not board_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Board file not found: {page_path}/boards/{board_filename}",
        )

    raw_lines = board_path.read_text(encoding="utf-8").splitlines()
    pieces: List[str] | None = None
    rows: List[str] = []
    in_grid = False

    for line in raw_lines:
        stripped = line.strip()
        if not in_grid:
            if not stripped:
                # skip empty lines before grid
                continue
            if stripped.startswith("#"):
                # metadata line
                meta = stripped.lstrip("#").strip()
                if meta.upper().startswith("PIECES:"):
                    payload = meta[len("PIECES:") :].strip()
                    if payload:
                        pieces = [p.strip().lower() for p in payload.split(",") if p.strip()]
                continue
            # first non-empty, non-metadata line starts the grid
            in_grid = True
            rows.append(line)
        else:
            rows.append(line)

    return {"rows": rows, "pieces": pieces}


def render_board_html(page_path: str, board_filename: str, editor_mode: bool = False) -> str:
    """Convert a board text file into HTML for a single board."""
    board = read_board(page_path, board_filename)
    rows = board["rows"]
    
    # Ensure board is exactly 20 rows high (pad with empty rows if needed)
    BOARD_HEIGHT = 20
    while len(rows) < BOARD_HEIGHT:
        rows.append("__________")  # 10 underscores for empty row
    
    # Trim if somehow more than 20 rows
    rows = rows[:BOARD_HEIGHT]
    
    # Build HTML string manually; this is injected with |safe in templates
    pieces_attr = ""
    pieces = board.get("pieces")
    if pieces:
        pieces_attr = f' data-pieces="{",".join(pieces)}"'
    board_id = f'{page_path}/boards/{board_filename}'
    grid_attr = ""
    if rows:
        safe_rows = [r.replace('"', "&quot;") for r in rows]
        grid_attr = f' data-grid="{"|".join(safe_rows)}"'

    html_parts: List[str] = []
    
    # Add dropdown menu if in editor mode
    if editor_mode:
        html_parts.append('<div class="tetris-board-header">')
        html_parts.append('<div class="board-dropdown">')
        html_parts.append('<button class="board-dropdown-toggle" type="button" aria-label="Board options">')
        html_parts.append('<span class="board-dropdown-icon">⋯</span>')
        html_parts.append('</button>')
        html_parts.append('<div class="board-dropdown-menu" style="display: none;">')
        html_parts.append(f'<button class="board-dropdown-item" data-action="edit" data-board-id="{board_id}">Edit Board</button>')
        html_parts.append('</div>')
        html_parts.append('</div>')
        html_parts.append('</div>')
    
    html_parts.append(f'<div class="tetris-board" data-board-id="{board_id}"{pieces_attr}{grid_attr}>')
    for row in rows:
        html_parts.append('<div class="tetris-row">')
        # Ensure row is exactly 10 characters wide
        row_padded = row.ljust(10)[:10]
        for ch in row_padded:
            cell_class = "cell-empty"
            ch_lower = ch.lower()
            if ch_lower in {"i", "o", "t", "s", "z", "j", "l"}:
                cell_class = f"cell-{ch_lower}"
            html_parts.append(f'<div class="tetris-cell {cell_class}" data-piece="{ch_lower if ch_lower in {"i", "o", "t", "s", "z", "j", "l"} else ""}"></div>')
        html_parts.append("</div>")  # end tetris-row
    html_parts.append("</div>")  # end tetris-board
    return "".join(html_parts)


def render_boards_row_html(page_path: str, board_filenames: List[str], editor_mode: bool = False) -> str:
    """Render up to three boards as one horizontal row."""
    limited = board_filenames[:3]
    parts: List[str] = ['<div class="tetris-board-row">']
    for filename in limited:
        # Derive a simple caption from filename (without extension)
        stem = Path(filename).stem
        caption = stem.replace("_", " ").title()
        parts.append('<figure class="tetris-board-wrapper">')
        parts.append(render_board_html(page_path, filename, editor_mode=editor_mode))
        parts.append(f'<div class="tetris-board-caption">{caption}</div>')
        parts.append("</figure>")
    parts.append("</div>")
    return "".join(parts)


def extract_headings(html: str) -> List[Dict[str, Any]]:
    """Extract h1, h2, h3 headings from HTML and return list with level, text, and id."""
    import re
    
    headings: List[Dict[str, Any]] = []
    # Match h1, h2, h3 tags
    pattern = re.compile(r'<div class="(h1|h2|h3)">(.*?)</div>', re.IGNORECASE)
    
    for match in pattern.finditer(html):
        level_tag = match.group(1).lower()
        text = match.group(2).strip()
        # Create ID from text (lowercase, replace spaces with hyphens, remove special chars)
        heading_id = re.sub(r'[^a-z0-9\s-]', '', text.lower())
        heading_id = re.sub(r'\s+', '-', heading_id)
        heading_id = heading_id.strip('-')
        
        level = int(level_tag[1])  # Extract number from h1, h2, h3
        headings.append({
            "level": level,
            "text": text,
            "id": heading_id
        })
    
    return headings


def add_heading_ids(html: str, headings: List[Dict[str, Any]]) -> str:
    """Add ID attributes to heading divs in HTML."""
    import re
    
    result = html
    for heading in headings:
        # Replace the heading div with one that has an ID
        pattern = rf'<div class="h{heading["level"]}">({re.escape(heading["text"])})</div>'
        replacement = f'<div class="h{heading["level"]}" id="{heading["id"]}">{heading["text"]}</div>'
        result = re.sub(pattern, replacement, result, count=1)
    
    return result


def build_breadcrumb(page_path: str) -> List[Dict[str, str]]:
    """Build breadcrumb navigation from page path."""
    parts = page_path.split("/")
    breadcrumb: List[Dict[str, str]] = []
    
    # Build cumulative paths
    for i, part in enumerate(parts):
        cumulative_path = "/".join(parts[:i+1])
        # Get pretty name (replace hyphens with spaces, title case)
        pretty_name = part.replace("-", " ").title()
        breadcrumb.append({
            "name": pretty_name,
            "path": cumulative_path
        })
    
    return breadcrumb


def inject_breadcrumb_into_title(html: str, breadcrumb: List[Dict[str, str]]) -> str:
    """Inject breadcrumb into article-title div."""
    import re
    
    if not breadcrumb:
        return html
    
    # Build breadcrumb HTML (directories are not clickable, only shown as text)
    breadcrumb_parts = []
    for crumb in breadcrumb[:-1]:
        breadcrumb_parts.append(f'<span class="breadcrumb-directory">{crumb["name"]}</span>')
        breadcrumb_parts.append('<span class="breadcrumb-separator">→</span>')
    breadcrumb_parts.append(f'<span class="breadcrumb-current">{breadcrumb[-1]["name"]}</span>')
    breadcrumb_html = '<div class="breadcrumb">' + ''.join(breadcrumb_parts) + '</div>'
    
    # Find article-title div and inject breadcrumb before the title text
    pattern = r'(<div class="article-title">)(.*?)(</div>)'
    def repl(match):
        return match.group(1) + breadcrumb_html + match.group(2) + match.group(3)
    
    return re.sub(pattern, repl, html, count=1)


def convert_markdown_formatting(content: str) -> str:
    """
    Convert markdown-style formatting to HTML.
    Supports:
    - **text** or *text* for bold
    - _text_ for italic
    """
    import re
    
    # Convert bold: **text** (double asterisk) first
    content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
    
    # Convert bold: *text* (single asterisk)
    # Process line by line to avoid matching list markers
    lines = content.split('\n')
    result_lines = []
    for line in lines:
        # Check if line starts with list marker (bullet or numbered list)
        if re.match(r'^\s*([-*]|\d+\.)\s', line):
            # It's a list item, don't process asterisks for bold
            result_lines.append(line)
        else:
            # Not a list item, process *text* for bold
            # Match *text* but ensure it's not part of **text** (already processed)
            line = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<strong>\1</strong>', line)
            result_lines.append(line)
    content = '\n'.join(result_lines)
    
    # Convert italic: _text_
    content = re.sub(r'_([^_\n]+?)_', r'<em>\1</em>', content)
    
    return content


def convert_lists_to_html(content: str) -> str:
    """
    Convert markdown-style lists to HTML lists.
    Supports:
    - Bullet lists: lines starting with '- ' or '* '
    - Numbered lists: lines starting with '1. ', '2. ', etc.
    """
    import re
    
    lines = content.split('\n')
    result_lines: List[str] = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check if this line starts a list
        bullet_match = re.match(r'^(\s*)([-*])\s+(.+)$', line)
        numbered_match = re.match(r'^(\s*)(\d+)\.\s+(.+)$', line)
        
        if bullet_match or numbered_match:
            # Start collecting list items
            list_items: List[Tuple[str, str]] = []  # (indent, content)
            is_numbered = numbered_match is not None
            
            # Collect all consecutive list items
            while i < len(lines):
                current_line = lines[i]
                current_stripped = current_line.strip()
                
                if not current_stripped:
                    # Empty line ends the list
                    break
                
                bullet = re.match(r'^(\s*)([-*])\s+(.+)$', current_line)
                numbered = re.match(r'^(\s*)(\d+)\.\s+(.+)$', current_line)
                
                if bullet:
                    if is_numbered:
                        break  # Different list type, end current list
                    indent = bullet.group(1)
                    content = bullet.group(3)
                    list_items.append((indent, content))
                    i += 1
                elif numbered:
                    if not is_numbered:
                        break  # Different list type, end current list
                    indent = numbered.group(1)
                    content = numbered.group(3)
                    list_items.append((indent, content))
                    i += 1
                else:
                    # Not a list item, end the list
                    break
            
            # Convert list items to HTML
            if list_items:
                list_tag = 'ol' if is_numbered else 'ul'
                list_class = 'numbered-list' if is_numbered else 'bullet-list'
                result_lines.append(f'<{list_tag} class="{list_class}">')
                for indent, item_content in list_items:
                    result_lines.append(f'  <li>{item_content}</li>')
                result_lines.append(f'</{list_tag}>')
            continue
        
        # Not a list item, add line as-is
        result_lines.append(line)
        i += 1
    
    return '\n'.join(result_lines)


def parse_page_content(page_path: str, raw: str, breadcrumb: List[Dict[str, str]] = None, editor_mode: bool = False) -> Tuple[str, List[Dict[str, str]], List[Dict[str, Any]]]:
    """
    Convert the raw page text into HTML.

    Rules:
    - Lines that are exactly '---' (ignoring surrounding whitespace) become an <hr>.
    - [[BOARD: filename.txt]] becomes a single board.
    - [[BOARDS: a.txt, b.txt, c.txt]] becomes up to 3 boards in a row.
    - Lines starting with '- ' or '* ' become bullet lists.
    - Lines starting with '1. ', '2. ', etc. become numbered lists.
    - *text* or **text** becomes bold.
    - _text_ becomes italic.
    - Everything else is passed through as-is (treated as HTML).
    
    Returns: (rendered_html, sources, headings)
    """
    import re

    # First, handle lines that are exactly '---' and collect sources.
    processed_lines: List[str] = []
    sources: List[Dict[str, str]] = []

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped == "---":
            processed_lines.append('<hr class="section-separator">')
        elif stripped.upper().startswith("SOURCE:"):
            # SOURCE: Description - https://example.com
            payload = stripped[len("SOURCE:") :].strip()
            if " - " in payload:
                label, url = payload.split(" - ", 1)
                sources.append({"label": label.strip(), "url": url.strip()})
            # Do not include this line in the main rendered content
        else:
            processed_lines.append(line)
    joined = "\n".join(processed_lines)
    
    board_pattern = re.compile(
        r"\[\[\s*(BOARD|BOARDS)\s*:\s*([^\]]+?)\s*\]\]",
        flags=re.IGNORECASE,
    )
    board_placeholders: List[Tuple[str, List[str]]] = []
    
    def extract_boards(match: re.Match) -> str:
        kind = match.group(1).upper()
        payload = match.group(2)
        filenames = [p.strip() for p in payload.split(",") if p.strip()]
        board_placeholders.append((kind, filenames))
        return f"@@BOARDPLACEHOLDER{len(board_placeholders) - 1}@@"
    
    joined = board_pattern.sub(extract_boards, joined)
    
    # Convert markdown formatting (bold/italic)
    joined = convert_markdown_formatting(joined)
    
    # Convert lists to HTML
    joined = convert_lists_to_html(joined)

    def render_placeholder(kind: str, filenames: List[str]) -> str:
        if not filenames:
            return ""
        if kind == "BOARD":
            return render_boards_row_html(page_path, [filenames[0]], editor_mode=editor_mode)
        return render_boards_row_html(page_path, filenames, editor_mode=editor_mode)

    rendered = joined
    for idx, (kind, filenames) in enumerate(board_placeholders):
        placeholder = f"@@BOARDPLACEHOLDER{idx}@@"
        rendered = rendered.replace(placeholder, render_placeholder(kind, filenames))
    
    # Extract headings and add IDs
    headings = extract_headings(rendered)
    rendered = add_heading_ids(rendered, headings)
    
    # Inject breadcrumb into article title if provided
    if breadcrumb:
        rendered = inject_breadcrumb_into_title(rendered, breadcrumb)
    
    return rendered, sources, headings


@app.get("/editor/{page_path:path}", response_class=HTMLResponse)
async def editor_page(page_path: str, request: Request):
    raw = read_page_source(page_path)
    rendered_html, sources, headings = parse_page_content(page_path, raw, editor_mode=True)
    return templates.TemplateResponse(
        "editor.html",
        base_context(
            request=request,
            page_path=page_path,
            raw_content=raw,
            rendered_content=rendered_html,
            sources=sources,
            show_nav_links=True,
        ),
    )


class BoardSaveRequest(BaseModel):
    board_id: str
    grid: List[str]


class PageSaveRequest(BaseModel):
    page_path: str
    content: str


@app.post("/api/board/save", response_class=JSONResponse)
async def save_board(request: BoardSaveRequest):
    """Save a board's grid data back to the file."""
    try:
        # board_id format: "page_path/boards/filename.txt"
        board_path = CONTENT_ROOT / request.board_id
        
        if not board_path.exists():
            raise HTTPException(status_code=404, detail="Board file not found")
        
        # Read existing file to preserve metadata
        existing_content = board_path.read_text(encoding="utf-8")
        lines = existing_content.splitlines()
        
        # Find where the grid starts (after metadata)
        grid_start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                grid_start_idx = i
                break
        
        # Preserve metadata lines
        metadata_lines = lines[:grid_start_idx]
        
        # Write new grid
        new_lines = metadata_lines + request.grid
        
        board_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        
        return {"success": True, "message": "Board saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/page/save", response_class=JSONResponse)
async def save_page(request: PageSaveRequest):
    """Save page.txt content."""
    try:
        page_file = CONTENT_ROOT / request.page_path / "page.txt"
        if not page_file.exists():
            raise HTTPException(status_code=404, detail="Page file not found")
        
        page_file.write_text(request.content, encoding="utf-8")
        return {"success": True, "message": "Page saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    pages = list_pages()
    return templates.TemplateResponse(
        "index.html",
        base_context(
            request=request,
            pages=pages,
            page_path=None,
            show_nav_links=True,
        ),
    )


@app.get("/{page_path:path}", response_class=HTMLResponse)
async def view_page(page_path: str, request: Request):
    raw = read_page_source(page_path)
    breadcrumb = build_breadcrumb(page_path)
    rendered_html, sources, headings = parse_page_content(page_path, raw, breadcrumb)
    return templates.TemplateResponse(
        "page.html",
        base_context(
            request=request,
            page_path=page_path,
            rendered_content=rendered_html,
            sources=sources,
            headings=headings,
            breadcrumb=breadcrumb,
            show_nav_links=False,  # reading view: minimal navbar
        ),
    )
