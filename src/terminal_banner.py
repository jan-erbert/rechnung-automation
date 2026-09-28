from rich.console import Console
from rich.text import Text

BANNER_ROWS = (
    ("   ██╗          ██╗", "     ██╗███████╗", "   ██╗   "),
    (" ██╔╝        ██╔╝  ", "     ██║██╔════╝", "    ╚██╗ "),
    ("██╔╝       ██╔╝    ", "     ██║█████╗  ", "     ╚██╗"),
    ("╚██╗     ██╔╝      ", "██   ██║██╔══╝  ", "     ██╔╝"),
    (" ╚██╗  ██╔╝        ", "╚█████╔╝███████╗", "    ██╔╝ "),
    ("  ╚══╝╚═╝          ", " ╚════╝ ╚══════╝", "   ╚═╝   "),
)
BANNER_WIDTH = max(sum(len(segment) for segment in row) for row in BANNER_ROWS)


def show_startup_banner(
    non_interactive: bool = False,
    console: Console | None = None,
) -> None:
    """Zeigt das Startbanner ausschliesslich in einem interaktiven Terminal."""
    if non_interactive:
        return
    console = console if console is not None else Console(highlight=False)
    if not console.is_terminal:
        return

    console.print()
    if console.width >= BANNER_WIDTH and _supports_banner(console.encoding):
        for left, center, right in BANNER_ROWS:
            row = Text()
            row.append(left, style="bright_blue")
            row.append(center, style="white")
            row.append(right, style="bright_blue")
            console.print(row, no_wrap=True)
    console.print("Rechnung-Automation", style="bold bright_blue", markup=False)
    console.print()


def _supports_banner(encoding: str) -> bool:
    """Prueft, ob die Ausgabe die Blockzeichen des Logos darstellen kann."""
    try:
        "██╗╔╝╚═║".encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True
