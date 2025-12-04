## Tetris Guide Blog – Project Design

This project is a small FastAPI-based site that lets you:

- **Write blog pages in simple text files** (with minimal HTML that you control).
- **Render those pages for end users** at routes like `/<pagename>`.
- **View an “editor” version** of each page (raw text + preview) separately from the end-user view.
- **Embed Tetris boards** (20×10 grids) in your pages, up to **3 boards per row**.

The goal is: **you can be creative with content, without needing to hand-craft full HTML pages**.

---

## Tech Stack

- **Backend**: Python + FastAPI
- **Templating**: Jinja2 (FastAPI `Jinja2Templates`)
- **Frontend**: Plain HTML + CSS (no framework, very light JS only if needed)
- **Content format**: Custom text files with:
  - Normal HTML snippets you write (simple `div`s, headings, etc.).
  - Special markers for **Tetris boards** and **horizontal separators**.

---

## Project Structure

All paths are relative to the `tetris_guide` folder.

- `main.py`  
  **FastAPI app** with routes:
  - `GET /` – list available pages.
  - `GET /{page_name}` – **end-user view** of a page.
  - `GET /editor/{page_name}` – **editor view** (shows raw text + rendered preview).

- `content/`
  - `pages/`
    - `demo.txt` – example blog page using the custom syntax.
  - `boards/`
    - `demo_board_1.txt`
    - `demo_board_2.txt`
    - `demo_board_3.txt`

- `templates/`
  - `base.html` – shared layout with **navbar, left sidebar, footer**.
  - `page.html` – end-user page view (injects rendered content into `base.html`).
  - `editor.html` – editor view with raw text and preview in the same layout.

- `static/`
  - `styles.css` – global styling, including:
    - Navbar, sidebar, footer layout.
    - Article typography and styles (titles, headers, normal text, bold/italic).
    - Tetris board grid styling.

- `requirements.txt` – Python dependencies (FastAPI, Uvicorn, Jinja2, etc.).

You already have `png_to_txt.py` which can generate board `.txt` files from `.png`. Those generated files will live under `content/boards/`.

---

## Authoring Format for Pages

Each blog page is a **plain text file** in `content/pages/`, e.g. `content/pages/demo.txt`.

### 1. Normal Text Content

- The **text content is treated as HTML**, so you can write basic HTML directly.
- To keep things simple, you can think in terms of individual `div` blocks.
- You should only use **very simple structures** (no crazy nested layouts).

Recommended CSS classes you can use:

- **Article title**:  
  ```html
  <div class="article-title">My Awesome Tetris Article</div>
  ```

- **Header 1 / 2 / 3**:  
  ```html
  <div class="h1">Big Section Title</div>
  <div class="h2">Subsection Title</div>
  <div class="h3">Smaller Subsection</div>
  ```

- **Normal text**:  
  ```html
  <div class="text">
    This is some normal paragraph text about Tetris strategy.
  </div>
  ```

- **Bold / italic / bold-italic inside text**:  
  ```html
  <div class="text">
    <b>Bold text</b>, <i>italic text</i>, and <b><i>bold italic</i></b>.
  </div>
  ```

You can combine these however you like, as long as you keep the structure fairly simple.

---

### 2. Horizontal Separator (`---`)

If a line in your editor file contains only:

```text
---
```

that will turn into a **slightly dark horizontal separator line** in the final HTML:

```html
<hr class="section-separator">
```

You can use this to visually split major sections of your article.

---

### 3. Embedding Tetris Boards

Tetris boards are stored as **20×10 grid text files** in `content/boards/`, using the same format as produced by `png_to_txt.py`:

- Each board file has **20 lines**.
- Each line has **10 characters**.
- Each character is one of:
  - `i, o, t, s, z, j, l` – standard Tetris tetromino types.
  - `_` – empty cell.

#### 3.1. Single Board

In your page file, you can embed a **single board** like this:

```text
[[BOARD: demo_board_1.txt]]
```

- `demo_board_1.txt` must be located in `content/boards/demo_board_1.txt`.
- This will render as one vertical 20×10 board.

#### 3.2. Up to 3 Boards in a Row

To show multiple boards in one horizontal row (max 3 per row), you can use:

```text
[[BOARDS: demo_board_1.txt, demo_board_2.txt, demo_board_3.txt]]
```

Rules:

- File names are **comma-separated**.
- You can specify **1, 2, or 3 boards** (extra ones are ignored).
- All board files must exist under `content/boards/`.

The renderer will output a block like:

- A row container.
- Inside, up to 3 Tetris boards side-by-side.

---

### 4. Putting It All Together – Example `demo.txt`

An example page file (simplified):

```html
<div class="article-title">Tetris Openers – A Short Guide</div>

<div class="h1">Introduction</div>
<div class="text">
  This page demonstrates how to use the custom syntax for Tetris boards.
</div>

---

<div class="h2">Single Board Example</div>
<div class="text">
  Below is a single Tetris board:
</div>

[[BOARD: demo_board_1.txt]]

---

<div class="h2">Three Boards in a Row</div>
<div class="text">
  Here we compare three different configurations side by side:
</div>

[[BOARDS: demo_board_1.txt, demo_board_2.txt, demo_board_3.txt]]
```

You only write this **one file**; the backend will convert it into full HTML inside the standard layout.

---

## How the Conversion Works

1. **Read raw page text** from `content/pages/{page_name}.txt`.
2. **Process special markers**:
   - Any line that is exactly `---` becomes `<hr class="section-separator">`.
   - Any `[[BOARD: filename.txt]]` is replaced by HTML for **one Tetris board**.
   - Any `[[BOARDS: a.txt, b.txt, c.txt]]` is replaced by HTML for **up to three boards in a row**.
3. **Leave all other text as-is**, treating it as HTML that you wrote.
4. Pass the resulting HTML string into a Jinja2 template (`page.html`) that plugs it into:
   - Navbar
   - Left sidebar
   - Footer

This means you get:

- **Full control** of article text and structure.
- **Minimal need to understand HTML layouts** (only small `div` blocks and some inline tags).

---

## Views / Routes

### 1. End-User View – `GET /{page_name}`

- Example: `GET /demo`
- Looks for `content/pages/demo.txt`.
- If found:
  - Parses the file using the above rules.
  - Renders `page.html` with:
    - `page_name` – for the title.
    - `rendered_content` – the parsed HTML (safe).
  - Uses `base.html` layout with navbar, sidebar, footer.

If the page does not exist, returns a 404.

### 2. Editor View – `GET /editor/{page_name}`

- Example: `GET /editor/demo`
- Loads the same `content/pages/demo.txt`.
- Renders `editor.html` which shows:
  - A **read-only `<textarea>` or preformatted block** containing the raw text.
  - A **live preview area** that shows the rendered HTML (same parser as end-user).
- Uses the same global layout (navbar, sidebar, footer), but with editor-specific content area.

> You can later extend this to support saving edits via POST/PUT, but initially it is a **viewer + preview**.

### 3. Index – `GET /`

- Lists all `.txt` files found under `content/pages/`.
- Each entry links to:
  - `/pagename` – end-user view
  - `/editor/pagename` – editor view

---

## Layout & Styling

### Base Layout (`base.html`)

Structure:

- **Navbar** (top)
  - Site title (“Tetris Guide”)
  - Link to home (`/`)
  - Optional link to a default editor page.
- **Main area**: a flex layout
  - **Left sidebar**
    - Small navigation list (e.g. links to some known pages).
  - **Content area**
    - Where `page.html` or `editor.html` injects the actual page.
- **Footer**
  - Small footer text / credits / copyright.

### CSS Highlights (`static/styles.css`)

- **Typography & article styles**
  - `.article-title` – larger, bold, centered.
  - `.h1`, `.h2`, `.h3` – decreasing font sizes, margin above.
  - `.text` – normal paragraph styling with comfortable line height.
  - `b`, `i`, `b i` – basic bold/italic formatting.
- **Layout**
  - `body` with neutral background color.
  - Navbar, sidebar, footer with subtle colors, borders or shadows.
  - Responsive behavior so the layout doesn’t break on small screens.
- **Tetris boards**
  - `.tetris-board-row` – flex container for up to 3 boards.
  - `.tetris-board` – fixed aspect ratio grid area.
  - `.tetris-row` + `.tetris-cell` – 20×10 grid of divs.
  - Color classes (examples):
    - `.cell-i` – cyan
    - `.cell-o` – yellow
    - `.cell-t` – purple
    - `.cell-s` – green
    - `.cell-z` – red
    - `.cell-j` – blue
    - `.cell-l` – orange
    - `.cell-empty` – dark/neutral background

---

## Running the Project

### 1. Install Dependencies

From inside `tetris_guide`:

```bash
pip install -r requirements.txt
```

### 2. Run FastAPI with Uvicorn

```bash
uvicorn main:app --reload
```

Then open in your browser:

- `http://127.0.0.1:8000/` – page index.
- `http://127.0.0.1:8000/demo` – example article for end users.
- `http://127.0.0.1:8000/editor/demo` – editor view for that article.

---

## Next Steps / Extensibility

Once the basics are running, you can:

- Add more pages as new `.txt` files in `content/pages/`.
- Generate more Tetris boards using `png_to_txt.py` and save them into `content/boards/`.
- Add more CSS for fancier article styling.
- Add a **save endpoint** to allow editing content directly in the browser rather than editing files manually.

This README is the blueprint; the next step is to scaffold the actual code, templates, CSS, and demo content to match this design.


