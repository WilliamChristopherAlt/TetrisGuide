## V2 Plan – Directory-Based Pages & Playable Boards

This document sketches the **next iteration** of the Tetris blog system before we touch any code.

### High-level concepts (using your terminology)

- A **directory** is like a folder on a computer: it can contain **other directories** and/or **page folders**.
- A **page** is a **folder** (leaf) that contains:
  - One main editor text file.
  - Its own `boards/` subfolder.
- Boards for a page live under that page’s **`boards/`** subfolder.
- Sidebar becomes **collapsible** and reflects the actual **directory tree**, not the internals of any single page.
- Each board can optionally define a **restricted piece set** (`i, o, l, j, s, z, t`).
- On the end-user view, each board gets a **3-dots menu**:
  - **Play with defined pieces**
  - **Play with free pieces** (standard modern Tetris bag)
- Clicking a menu option opens a **modal** with a small Tetris game.

The goal: **keep your authoring simple**, while the UI becomes much richer.

---

## 1. Directory Structure vs Page Folders

New content layout under `content/`:

- `content/` **(directory root)**
  - `openers/` **(directory)**
    - `t-spin-basics/` **(page folder)**
      - `page.txt` – main article content (same syntax as now: HTML blocks, `---`, `[[BOARD: ...]]`, `[[BOARDS: ...]]`, `SOURCE:` lines).
      - `boards/`
        - `intro_shape.txt`
        - `quiz_1.txt`
    - `t-spin-triple/` **(page folder)**
      - `page.txt`
      - `boards/`
        - `starter.txt`
    - `c-spin/` **(page folder)**
      - `page.txt`
      - `boards/`
        - `c_core.txt`
    - `dt-cannon/` **(page folder)**
      - `page.txt`
      - `boards/`
        - `dt_setup_1.txt`
  - `misc/` **(another directory)**
    - `demo/` **(page folder)**
      - `page.txt`
      - `boards/`
        - `opener_a.txt`
        - `opener_b.txt`

Notes:

- **Directories** can contain:
  - More directories (e.g. `openers/advanced/`).
  - **Page folders** (leaf nodes like `t-spin-basics/`).
- Routing:
  - A page folder path like `openers/t-spin-basics` maps to a URL like `/openers/t-spin-basics`.
  - A shallow page like `demo` at root would map to `/demo`.
- Inside a given **page folder’s** `page.txt`, `[[BOARD: intro_shape.txt]]` will be resolved **relative to that page folder’s own `boards/` directory**.

---

## 2. Board Files with Optional Piece Sets

We keep the **visual grid** format compatible with your current generator, but allow an optional **header section** at the top of the board file.

### 2.1. Basic Format

Each board file:

```text
# Optional metadata lines at the top
# PIECES: i, o, t

__________
__________
... (20 lines total, 10 chars each) ...
```

Rules:

- Lines starting with `#` are **metadata**, not part of the grid.
- Recognized metadata key:
  - `PIECES:` – list of piece types used for “play with defined pieces”.
- After the metadata lines, we expect the **20×10 character grid** like now:
  - `i, o, t, s, z, j, l` – tetromino types.
  - `_` – empty.

Example:

```text
# PIECES: i, o, t

__________
__________
__________
__________
__________
____ttt___
_____t____
__________
... (rest of the 20 rows) ...
```

If `PIECES:` is missing, “play with defined pieces” will still be available but fall back to a **default small set** (or we can disable the option – up to you; initial plan is to fall back).

---

## 3. Sidebar as a Real Directory Tree

The sidebar reflects the **directory structure**, not the internals of a single page.

Behavior:

- Show a **tree** starting at `content/`:
  - `openers/`
    - `t-spin-basics/` (page folder)
    - `t-spin-triple/` (page folder)
    - `c-spin/` (page folder)
    - `dt-cannon/` (page folder)
  - `misc/`
    - `demo/` (page folder)
- Directories have a **caret icon** and can be **collapsed/expanded**.
- Page folders are **leaf nodes** in the tree:
  - Clicking a page folder navigates to its URL (e.g. `/openers/t-spin-basics`).

Implementation notes:

- We’ll scan `content/` recursively:
  - **Directories** become tree nodes that can contain:
    - Other directories.
    - Page folders.
  - **Page folders** are detected by the presence of a `page.txt` inside them.
- Sidebar expansion state is local UI state in JS:
  - Clicking the caret toggles `expanded` class.

---

## 4. 3-Dot Menu & Modal Gameplay per Board

Each rendered board should have:

- A small **3-dots “more” button** in the top-right corner of the board card.
- On click, show a small menu:
  - **Play with defined pieces**
  - **Play with free pieces**

Clicking either opens a **modal** containing a Tetris game:

- **Play with defined pieces**:
  - If `PIECES:` is provided in the board file, feed that list into the game’s piece generator.
  - Otherwise, use a fallback: maybe all 7 tetrominoes or a smaller subset.
- **Play with free pieces**:
  - Use the **standard modern Tetris 7-bag** randomizer (all pieces available).

The modal:

- Covers the center of the screen with a dimmed backdrop.
- Shows:
  - Main playfield.
  - Hold piece area.
  - Next queue.
  - Basic score / lines labels if the library supports it.
- Has a **close button** (X) or clicking the backdrop closes it.

Keybindings (wired to the game instance):

- **Up Arrow** – hard drop.
- **Down Arrow** – soft drop.
- **Left/Right Arrow** – move piece left/right.
- **A** – rotate piece 180°.
- **Z** – rotate 90° counter-clockwise.
- **X** – rotate 90° clockwise.
- **C** – hold/swap current piece (no double-hold with no lock, respecting library rules where possible).

---

## 5. Tetris Frontend Library Choice

Requirements:

- Pure front-end JS/TS library that:
  - Is free and open-source.
  - Allows us to:
    - Control **piece queue** (so we can override with defined pieces).
    - Provide custom keybindings.
    - Embed the game in a **div** (for the modal).

Candidate direction:

- Use a known OSS project that exposes:
  - A constructor taking configuration (keymap, randomizer hook, mount element).
  - Or at least something we can **wrap** with minimal glue code.

Implementation approach:

- Host the library either:
  - From a CDN (easiest for now).
  - Or copy a minified bundle into `static/js/` (if license allows).
- On board render, attach a small JS handler to:
  - Open the modal.
  - Initialize / destroy the Tetris instance inside the modal’s root element.

---

## 6. Dummy Data Plan

To showcase the new structure, we’ll create:

- Under `content/`:
  - `demo/`, `t-spin-basics/`, `t-spin-triple/`, `c-spin/`, `dt-cannon/` (migrating the existing pages).
  - Each with:
    - `page.txt` that uses:
      - `<div class="article-title">...</div>`
      - Headings, text, `---`, `[[BOARD: ...]]`, `[[BOARDS: ...]]`.
      - `SOURCE:` lines.
    - `boards/` with:
      - 1–3 board files per page.
      - At least one board using `# PIECES: ...` metadata.

Boards:

- Example names:
  - `t-spin-basics/boards/intro_shape.txt` (with a simple T-Spin cavity).
  - `t-spin-triple/boards/starter.txt`.
  - `c-spin/boards/c_core.txt`.
  - `dt-cannon/boards/dt_setup_1.txt`.
  - Each built from existing demo boards or simple handmade patterns.

---

## 7. Backend Changes (Conceptual)

We will **not code this yet**; this section just describes what will need to change.

### 7.1. Content Resolution

- Replace:
  - `content/pages/{page_name}.txt`
- With:
  - `content/{page_name}/page.txt`
- Boards will be loaded from:
  - `content/{page_name}/boards/{board_file}`

The `[[BOARD: ...]]` and `[[BOARDS: ...]]` parser will need the **current page name** so it can resolve boards relative to that directory.

### 7.2. Board Parser

- When reading a board file:
  - Strip off leading lines starting with `#` and parse metadata.
  - Capture:
    - `pieces` (list of piece IDs) from `PIECES:`.
    - `grid` (20×10).
- Return something like:

```python
{
  "rows": [... grid rows ...],
  "pieces": ["i", "o", "t"],  # optional
}
```

The HTML renderer for boards will embed data attributes for JS:

```html
<div
  class="tetris-board"
  data-board-id="t-spin-basics/intro_shape"
  data-pieces="i,o,t"
>
  ...
</div>
```

The 3-dots button next to the board will read these attributes.

### 7.3. Sidebar Data

- Instead of `list_pages()` reading `content/pages/*.txt`, we’ll:
  - Scan `content/*/page.txt`.
  - Build a structure like:

```python
[
  {"slug": "demo", "title": "Demo"},
  {"slug": "t-spin-basics", "title": "T-Spin Basics"},
  ...
]
```

The sidebar template will:

- Show each top-level as a collapsible item (with a dummy submenu in V2).

---

## 8. Modal & Frontend Wiring (Conceptual)

Frontend responsibilities:

- Listen for clicks on each board’s **3-dots button**.
- Open a shared **modal root** (one per page).
- Create a Tetris game instance inside the modal when opened, configured with:
  - **Mode**:
    - `defined` – use `data-pieces` for the piece generator.
    - `free` – use default 7-bag.
  - **Keymap** matching the required bindings.
- On modal close:
  - Destroy/unmount the game instance.

We’ll add:

- A small JS module under `static/js/boards.js` that exports an `initBoardInteractions()` function and call it from the templates.

---

## 9. TODO List (Implementation Steps)

1. **Refactor content structure**
   - Move existing `content/pages/*.txt` into `content/{slug}/page.txt`.
   - Create `boards/` subfolders and move / copy board `.txt` files.
   - Update README to show the new layout as the “blessed” structure.

2. **Update backend path resolution**
   - Change `read_page_source` to load `content/{page_name}/page.txt`.
   - Pass `page_name` into the parser so board references can be resolved relative to `content/{page_name}/boards/`.

3. **Enhance board parser**
   - Support `#` metadata lines at top of board files.
   - Parse `PIECES:` into a list of piece IDs.
   - Return structured data and have the HTML renderer:
     - Add `data-pieces` attributes.
     - Keep the current visual rendering.

4. **Sidebar refactor**
   - Replace old `SIDEBAR_LINKS` with dynamic directory scan (`content/*/page.txt`).
   - Render a collapsible sidebar:
     - Top-level for each page.
     - Dummy sub-items (`Overview`, `Patterns`, `Exercises`) linking to anchors.

5. **Add 3-dots UI and modal markup**
   - Wrap each board in a container that includes:
     - Board display.
     - 3-dots menu button.
     - Hidden menu with:
       - “Play with defined pieces”
       - “Play with free pieces”.
   - Add a modal root to the page template.

6. **Integrate Tetris frontend library**
   - Choose a suitable OSS library and include it (CDN or static file).
   - Write glue JS (`static/js/boards.js`) to:
     - Initialize a game in the modal with custom keybindings.
     - Accept an optional `pieces` list.
     - Tear down on close.

7. **Dummy content**
   - Populate each page directory with:
     - A `page.txt` demonstrating at least:
       - Text blocks.
       - `[[BOARD: ...]]` and `[[BOARDS: ...]]`.
       - Some boards with `PIECES:` metadata.
   - Verify sidebar, parsing, and search still work.

Once this V2 design feels right, we can start executing these TODOs in the actual codebase.


