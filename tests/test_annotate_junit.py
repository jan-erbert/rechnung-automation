from tools.annotate_junit import build_annotations


def test_junit_failures_become_github_annotations(tmp_path):
    """JUnit-Fehler enthalten Testpfad, Zeile und maskierte Fehlermeldung."""
    report = tmp_path / "pytest-results.xml"
    report.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite>
    <testcase classname="tests.test_example" name="test_value" file="tests/test_example.py" line="4">
      <failure message="assert 1 == 2">assert 1 == 2\nmehr</failure>
    </testcase>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )

    assert build_annotations(report) == [
        "::error file=tests/test_example.py,title=tests.test_example.test_value,line=5::"
        "assert 1 == 2%0Amehr"
    ]


def test_successful_junit_report_creates_no_annotations(tmp_path):
    """Ein erfolgreicher JUnit-Bericht erzeugt keine Fehlerannotation."""
    report = tmp_path / "pytest-results.xml"
    report.write_text(
        "<testsuite><testcase name=\"test_ok\" /></testsuite>", encoding="utf-8"
    )

    assert build_annotations(report) == []
