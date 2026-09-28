from io import StringIO

import pytest
from rich.console import Console

from terminal_banner import show_startup_banner


def test_banner_renders_logo_and_colors_in_terminal():
    """Ein breites Farbterminal zeigt das vollstaendige blau-weisse Logo."""
    output = StringIO()
    console = Console(
        file=output,
        force_terminal=True,
        width=80,
        height=25,
        color_system="standard",
        no_color=False,
    )

    show_startup_banner(console=console)

    rendered = output.getvalue()
    assert "██╗" in rendered
    assert "Rechnung-Automation" in rendered
    assert "\x1b[94m" in rendered
    assert "\x1b[37m" in rendered


@pytest.mark.parametrize("non_interactive,terminal", [(True, True), (False, False)])
def test_banner_is_silent_for_cron_and_redirected_output(non_interactive, terminal):
    """Cron und Ausgabeumleitung erhalten weder Logo noch Farbcodes."""
    output = StringIO()
    console = Console(file=output, force_terminal=terminal, width=80)

    show_startup_banner(non_interactive=non_interactive, console=console)

    assert output.getvalue() == ""


def test_narrow_terminal_uses_compact_title():
    """Schmale Terminals erhalten einen lesbaren Titel statt umgebrochenem Logo."""
    output = StringIO()
    console = Console(
        file=output, force_terminal=True, width=25, height=25, no_color=True
    )

    show_startup_banner(console=console)

    assert "Rechnung-Automation" in output.getvalue()
    assert "██" not in output.getvalue()
