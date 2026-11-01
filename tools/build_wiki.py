"""Erzeugt eine lokale Wiki-Vorschau aus docs/, ohne Netzwerk oder Veröffentlichung."""

import argparse
import posixpath
import re
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit

PAGES = {
    "docs/index.md": "Home",
    "docs/installation.md": "Installation",
    "docs/konfiguration.md": "Konfiguration",
    "docs/kunden.md": "Kunden",
    "docs/betrieb.md": "Betrieb",
    "docs/zugferd.md": "ZUGFeRD",
    "docs/windmill.md": "Windmill",
    "docs/entwicklung.md": "Entwicklung",
}
LEGACY_PAGES = {
    "Archivierung": "Betrieb",
    "Betrieb-Cron-Logging": "Betrieb",
    "Fehlerbehandlung": "Betrieb",
    "Konfigurationsdateien": "Konfiguration",
    "Lizenz-&-Mitwirkende": "Entwicklung",
    "Mailversand": "Konfiguration",
    "PDF-Layout-&-Gestaltung": "Konfiguration",
    "Rechnungsgenerierung": "Betrieb",
    "Setup-&-Installation": "Installation",
    "Update-Tool": "Entwicklung",
}
INLINE_LINK = re.compile(
    r"(?P<image>!?)\[(?P<label>[^\]\n]*)\]"
    r"\((?P<target><[^>\n]+>|[^\s)]+)"
    r"(?P<title>\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\)"
)
REFERENCE_LINK = re.compile(r"^(\s*\[[^\]\n]+\]:\s*)(<[^>\n]+>|\S+)(.*)$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")


def repository_base(
    repository_url: str,
    source_ref: str,
    ref_type: str = "branch",
) -> tuple[str, str]:
    """Prüft den gewählten Repository-Link und den Ref ohne Zugangsdaten."""
    parsed = urlsplit(repository_url)
    if ref_type not in {"branch", "tag", "commit"}:
        raise ValueError("Der Ref-Typ muss branch, tag oder commit sein.")
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not parsed.path.strip("/")
    ):
        raise ValueError("Eine Repository-URL ohne Zugangsdaten oder Zusätze angeben.")
    if (
        not source_ref
        or any(character.isspace() for character in source_ref)
        or any(part in {"", ".", ".."} for part in source_ref.split("/"))
    ):
        raise ValueError("Einen gültigen Branch, Tag oder Commit als Ref angeben.")
    base = repository_url.rstrip("/")
    if base.endswith(".git"):
        base = base[:-4]
    provider = "github" if parsed.hostname == "github.com" else "forgejo"
    return base, provider


def rewrite_target(
    target: str,
    source_path: str,
    source_root: Path,
    repository_url: str,
    source_ref: str,
    *,
    ref_type: str = "branch",
    image: bool = False,
) -> str:
    """Ordnet relative Links einer Wiki-Seite oder der gewählten Repo-Version zu."""
    target = target.removeprefix("<").removesuffix(">")
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
        return target

    relative = posixpath.normpath(
        posixpath.join(str(PurePosixPath(source_path).parent), unquote(parsed.path))
    )
    if relative == ".." or relative.startswith("../"):
        raise ValueError(f"Link verlässt das Repository: {source_path}")
    local_target = source_root / relative
    if not local_target.exists():
        raise ValueError(f"Linkziel fehlt: {relative}")

    base, provider = repository_base(repository_url, source_ref, ref_type)
    if relative in PAGES and not image:
        rewritten = PAGES[relative]
    else:
        if provider == "github":
            route = "raw" if image else "tree" if local_target.is_dir() else "blob"
        else:
            route = f"raw/{ref_type}" if image else f"src/{ref_type}"
        rewritten = (
            f"{base}/{route}/{quote(source_ref, safe='')}/"
            f"{quote(relative, safe='/')}"
        )
    if parsed.query:
        rewritten += "?" + parsed.query
    if parsed.fragment:
        rewritten += "#" + quote(unquote(parsed.fragment), safe="-._~:")
    return rewritten


def rewrite_markdown(
    text: str,
    source_path: str,
    source_root: Path,
    repository_url: str,
    source_ref: str,
    *,
    ref_type: str = "branch",
) -> str:
    """Passt Markdown-Links an und lässt Codebeispiele unverändert."""

    def target(value: str, *, image: bool = False) -> str:
        """Bindet die Quelldatei an die gemeinsame Linkumsetzung."""
        return rewrite_target(
            value,
            source_path,
            source_root,
            repository_url,
            source_ref,
            ref_type=ref_type,
            image=image,
        )

    def inline(match: re.Match) -> str:
        """Erhält Linkbeschriftung und optionalen Titel."""
        destination = target(match["target"], image=bool(match["image"]))
        return (
            f"{match['image']}[{match['label']}]"
            f"({destination}{match['title'] or ''})"
        )

    output = []
    fence = ""
    for line in text.splitlines(keepends=True):
        marker = FENCE.match(line)
        if fence:
            output.append(line)
            if (
                marker
                and marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                fence = ""
            continue
        if marker:
            fence = marker[1]
            output.append(line)
            continue
        if line.startswith(("    ", "\t")):
            output.append(line)
            continue
        reference = REFERENCE_LINK.match(line.rstrip("\n"))
        if reference:
            ending = "\n" if line.endswith("\n") else ""
            output.append(reference[1] + target(reference[2]) + reference[3] + ending)
            continue
        parts = re.split(r"(`+[^`]*`+)", line)
        output.append(
            "".join(
                part if part.startswith("`") else INLINE_LINK.sub(inline, part)
                for part in parts
            )
        )
    return "".join(output)


def build_wiki(
    source_root: Path,
    output_dir: Path,
    repository_url: str,
    source_ref: str = "main",
    *,
    ref_type: str = "branch",
) -> list[str]:
    """Erzeugt Markdown nur in einem neuen oder vollständig leeren Zielordner."""
    repository_base(repository_url, source_ref, ref_type)
    source_root = source_root.resolve()
    if output_dir.is_symlink() or (
        output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir()))
    ):
        raise FileExistsError("Der Ausgabeordner muss neu oder vollständig leer sein.")

    pages = {}
    for source, page in PAGES.items():
        path = source_root / source
        if (
            not path.is_file()
            or path.is_symlink()
            or not path.resolve().is_relative_to(source_root)
        ):
            raise ValueError(
                f"Dokumentationsquelle fehlt oder ist ein Symlink: {source}"
            )
        text = rewrite_markdown(
            path.read_text(encoding="utf-8"),
            source,
            source_root,
            repository_url,
            source_ref,
            ref_type=ref_type,
        )
        pages[page + ".md"] = (
            f"<!-- Quelle: {source}; lokal mit tools/build_wiki.py erzeugt. -->\n\n"
            + text
        )
    for old_page, destination in LEGACY_PAGES.items():
        pages[old_page + ".md"] = (
            f"# {old_page.replace('-', ' ')}\n\n"
            f"Die aktuelle Anleitung steht unter [{destination}]({destination}).\n"
        )
    pages["_Sidebar.md"] = (
        "\n".join(f"- [{page}]({page})" for page in PAGES.values()) + "\n"
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in pages.items():
        with (output_dir / name).open("x", encoding="utf-8") as stream:
            stream.write(content)
    return sorted(pages)


def main() -> None:
    """Erstellt ausschließlich eine Vorschau; der Ref betrifft nur Quellverweise."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--repository-url", required=True)
    parser.add_argument(
        "--ref",
        default="main",
        help="Branch, Tag oder Commit für Repository-Links (kein Checkout).",
    )
    parser.add_argument(
        "--ref-type",
        choices=["branch", "tag", "commit"],
        default="branch",
        help="Typ des gewählten Ref, insbesondere für Forgejo-Links.",
    )
    arguments = parser.parse_args()
    try:
        pages = build_wiki(
            Path(__file__).resolve().parents[1],
            arguments.output_dir,
            arguments.repository_url,
            arguments.ref,
            ref_type=arguments.ref_type,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"{len(pages)} Wiki-Seiten lokal erzeugt: {arguments.output_dir}")
    print("Keine Veröffentlichung und kein Git-Push ausgeführt.")


if __name__ == "__main__":
    main()
