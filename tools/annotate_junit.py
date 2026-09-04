import argparse
import xml.etree.ElementTree as ElementTree
from pathlib import Path


def _escape_command_value(value: str) -> str:
    """Maskiert Text fuer GitHub-Workflow-Kommandos."""
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def build_annotations(report_path: Path) -> list[str]:
    """Erzeugt GitHub-Annotationen aus fehlgeschlagenen JUnit-Testfaellen."""
    root = ElementTree.parse(report_path).getroot()
    annotations = []
    for test_case in root.iter("testcase"):
        failure = test_case.find("failure")
        if failure is None:
            failure = test_case.find("error")
        if failure is None:
            continue

        test_name = test_case.get("name", "Unbekannter Test")
        class_name = test_case.get("classname", "")
        title = ".".join(part for part in (class_name, test_name) if part)
        message = (
            failure.text or failure.get("message") or "Test fehlgeschlagen"
        ).strip()
        metadata = [
            f"title={_escape_command_value(title)}",
        ]
        file_path = test_case.get("file")
        if file_path:
            metadata.insert(0, f"file={_escape_command_value(file_path)}")
        line = test_case.get("line")
        if line and line.isdigit():
            metadata.append(f"line={int(line) + 1}")

        annotations.append(
            f"::error {','.join(metadata)}::{_escape_command_value(message[:8000])}"
        )
    return annotations


def main() -> int:
    """Gibt alle Testfehler eines JUnit-Berichts als Workflow-Kommandos aus."""
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    for annotation in build_annotations(args.report):
        print(annotation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
