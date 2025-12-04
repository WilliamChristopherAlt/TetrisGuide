from PIL import Image
import math

# --- Standard Guideline Tetromino Colors ---
TETROMINO_COLORS = {
    "i": (0, 255, 255),
    "o": (255, 255, 0),
    "t": (128, 0, 128),
    "s": (0, 255, 0),
    "z": (255, 0, 0),
    "j": (0, 0, 255),
    "l": (255, 165, 0),
}

def nearest_tetromino_color(pixel):
    r, g, b = pixel[:3]
    best_key = "_"
    best_dist = float("inf")

    for key, (cr, cg, cb) in TETROMINO_COLORS.items():
        dist = (r - cr)**2 + (g - cg)**2 + (b - cb)**2
        if dist < best_dist:
            best_key = key
            best_dist = dist

    # If the pixel looks "empty"
    if best_dist > 60_000:  # tweak threshold if needed
        return "_"

    return best_key


def png_to_tetris_txt(png_path, txt_path, board_width, board_height):
    # Load image
    img = Image.open(png_path).convert("RGB")

    # Resize image to board resolution
    img = img.resize((board_width, board_height), Image.NEAREST)

    # Construct rows top → bottom
    lines = []
    for y in range(board_height):
        row_chars = ""
        for x in range(board_width):
            pixel = img.getpixel((x, y))
            row_chars += nearest_tetromino_color(pixel)
        lines.append(row_chars)

    # Write out the text file
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Saved output to {txt_path}")


# --- Example usage ---
if __name__ == "__main__":
    png_to_tetris_txt(
        png_path="board.png",
        txt_path="board.txt",
        board_width=10,     # standard Tetris width
        board_height=20     # standard Tetris height
    )
