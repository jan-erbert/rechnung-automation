"""Prüft lokale Wiki-Vorschauen mit fiktiven Dokumenten, ohne Netzwerk."""

import pytest

from tools.build_wiki import LEGACY_PAGES, PAGES, build_wiki, rewrite_markdown


@pytest.fixture
def source(tmp_path):
    """Erstellt nur die erwarteten Markdown-Quellen im temporären Verzeichnis."""
    root = tmp_path / "source"
    for name in PAGES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {PAGES[name]}\n", encoding="utf-8")
    return root


def test_relative_links_preserve_anchors_titles_and_code(source):
    """Wiki-Navigation wird umgesetzt, während Code und externe Links bleiben."""
    content = (
        '[Setup](installation.md#linux "Einrichtung")\n'
        "[Start](index.md) und [nur Anker](#lokal)\n"
        "[extern](https://example.invalid/help#x)\n"
        "`[Code](installation.md)`\n"
        "```markdown\n[Beispiel](installation.md)\n```\n"
        '[referenz]: kunden.md#kontakt "Kunde"\n'
    )

    result = rewrite_markdown(
        content, "docs/index.md", source, "https://github.com/example/tool", "main"
    )

    assert '[Setup](Installation#linux "Einrichtung")' in result
    assert "[Start](Home) und [nur Anker](#lokal)" in result
    assert "[extern](https://example.invalid/help#x)" in result
    assert "`[Code](installation.md)`" in result
    assert "```markdown\n[Beispiel](installation.md)\n```" in result
    assert '[referenz]: Kunden#kontakt "Kunde"' in result


@pytest.mark.parametrize(
    ("repository", "route"),
    [
        ("https://github.com/example/tool.git", "blob"),
        ("https://forgejo.example.invalid/example/tool", "src/branch"),
    ],
)
def test_source_links_encode_ref_and_path(source, repository, route):
    """Nicht-Wiki-Dateien verweisen auf den gewählten Branch und sichere URL-Pfade."""
    (source / "Lizenz & Hinweise.md").write_text("# Hinweise\n", encoding="utf-8")

    result = rewrite_markdown(
        "[Hinweise](<../Lizenz & Hinweise.md#abschnitt>)\n",
        "docs/index.md",
        source,
        repository,
        "docs/release-handbook",
    )

    assert (
        f"{repository.removesuffix('.git')}/{route}/docs%2Frelease-handbook/"
        "Lizenz%20%26%20Hinweise.md#abschnitt"
    ) in result


@pytest.mark.parametrize("existing", [False, True])
def test_build_preserves_old_wiki_page_addresses(source, tmp_path, existing):
    """Alte Seitennamen bleiben als Verweise auf die neuen kanonischen Seiten."""
    output = tmp_path / "wiki"
    if existing:
        output.mkdir()

    names = build_wiki(source, output, "https://github.com/example/tool")

    assert set(names) == {
        *(page + ".md" for page in PAGES.values()),
        *(page + ".md" for page in LEGACY_PAGES),
        "_Sidebar.md",
    }
    assert "[Konfiguration](Konfiguration)" in (
        output / "PDF-Layout-&-Gestaltung.md"
    ).read_text(encoding="utf-8")
    assert "[Windmill](Windmill)" in (output / "_Sidebar.md").read_text(
        encoding="utf-8"
    )


def test_nonempty_output_is_never_overwritten(source, tmp_path):
    """Auch eine versteckte vorhandene Datei sperrt die Ausgabe vollständig."""
    output = tmp_path / "wiki"
    output.mkdir()
    sentinel = output / ".keep"
    sentinel.write_text("unverändert", encoding="utf-8")

    with pytest.raises(FileExistsError, match="leer"):
        build_wiki(source, output, "https://github.com/example/tool")

    assert list(output.iterdir()) == [sentinel]
    assert sentinel.read_text(encoding="utf-8") == "unverändert"


def test_invalid_source_does_not_create_partial_output(source, tmp_path):
    """Fehlende Quellen und aus dem Repo führende Links scheitern vor dem Schreiben."""
    output = tmp_path / "wiki"
    (source / "docs/index.md").write_text("[falsch](../../outside.md)\n")
    with pytest.raises(ValueError, match="verlässt"):
        build_wiki(source, output, "https://github.com/example/tool")
    assert not output.exists()

    (source / "docs/index.md").write_text("# Home\n")
    (source / "docs/kunden.md").unlink()
    with pytest.raises(ValueError, match="Dokumentationsquelle"):
        build_wiki(source, output, "https://github.com/example/tool")
    assert not output.exists()


def test_repository_credentials_are_rejected(source, tmp_path):
    """Ein Vorschau-Link darf keine Zugangsdaten in veröffentlichte Seiten kopieren."""
    with pytest.raises(ValueError, match="Zugangsdaten"):
        build_wiki(
            source, tmp_path / "wiki", "https://user:dummy@forgejo.example.invalid/tool"
        )


def test_images_and_directory_links_use_repository_routes(source):
    """Bilder bleiben abrufbare Dateien; Verzeichnisse erhalten keine Blob-URL."""
    assets = source / "assets"
    assets.mkdir()
    (assets / "sample image.png").write_bytes(b"fictional")
    result = rewrite_markdown(
        "![Bild](<../assets/sample image.png>)\n[Assets](../assets/)\n",
        "docs/index.md",
        source,
        "https://github.com/example/tool",
        "main",
    )
    assert (
        "https://github.com/example/tool/raw/main/assets/sample%20image.png" in result
    )
    assert "https://github.com/example/tool/tree/main/assets" in result


@pytest.mark.parametrize(
    ("ref_type", "source_ref"),
    [("tag", "v1.5.0"), ("commit", "1234567890abcdef" * 2 + "12345678")],
)
def test_forgejo_source_routes_follow_explicit_ref_type(
    source,
    tmp_path,
    ref_type,
    source_ref,
):
    """Auch unveränderliche Tags und Commits erhalten passende Forgejo-Dateilinks."""
    (source / "LICENSE.md").write_text("# Lizenz\n", encoding="utf-8")
    (source / "logo.png").write_bytes(b"fictional")
    (source / "docs/index.md").write_text(
        "[Lizenz](../LICENSE.md)\n![Logo](../logo.png)\n", encoding="utf-8"
    )
    output = tmp_path / "wiki"

    build_wiki(
        source,
        output,
        "https://forgejo.example.invalid/example/tool",
        source_ref,
        ref_type=ref_type,
    )

    home = (output / "Home.md").read_text(encoding="utf-8")
    assert f"/src/{ref_type}/{source_ref}/LICENSE.md" in home
    assert f"/raw/{ref_type}/{source_ref}/logo.png" in home


def test_unknown_ref_type_is_rejected_before_writing(source, tmp_path):
    """Unbekannte Ref-Typen werden nicht still als Branch interpretiert."""
    output = tmp_path / "wiki"
    with pytest.raises(ValueError, match="Ref-Typ"):
        build_wiki(
            source,
            output,
            "https://github.com/example/tool",
            ref_type="release",
        )
    assert not output.exists()
