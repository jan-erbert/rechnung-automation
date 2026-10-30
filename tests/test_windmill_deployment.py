"""Prueft generierte Windmill-Definitionen ohne Anwendung oder Worker auszufuehren."""

import ast
import json

import pytest

from integrations.windmill import deployment


def test_generated_wrappers_compile_without_executing_application(tmp_path):
    """Alle portablen Einstiegsskripte lassen sich als Python kompilieren."""
    project = str(tmp_path / "project's root")
    definitions = deployment.script_definitions(project, ["allowed.invalid"])

    assert len(definitions) == len(deployment.FUNCTIONS)
    json.dumps(definitions)
    for definition in definitions:
        compile(definition["content"], definition["path"], "exec")
        tree = ast.parse(definition["content"])
        project_assignment = next(
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "PROJECT"
                for target in node.targets
            )
        )
        assert ast.literal_eval(project_assignment.value.args[0]) == project


def test_private_deployment_parameters_never_become_form_inputs(tmp_path):
    """Mailgrenzen und Ressourcen-Loader werden durch den Deployer festgelegt."""
    definitions = deployment.script_definitions(str(tmp_path), ["allowed.invalid"])
    for definition in definitions:
        properties = definition["schema"]["properties"]
        assert "allowed_domains" not in properties
        assert "resource_loader" not in properties
        tree = ast.parse(definition["content"])
        entry = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        names = {argument.arg for argument in entry.args.args}
        assert "allowed_domains" not in names
        assert "resource_loader" not in names
        call = entry.body[-1].value
        payload = call.args[1]
        keywords = {
            key.value: value for key, value in zip(payload.keys, payload.values)
        }
        if definition["path"].endswith(
            ("run_native", "customer_create", "customer_edit")
        ):
            assert ast.literal_eval(keywords["allowed_domains"]) == ["allowed.invalid"]
        assert "resource_loader" not in keywords


@pytest.mark.parametrize("path", ["relative/project", "", "."])
def test_deployment_requires_absolute_worker_project_path(path):
    """Ein relativer Workerpfad darf keinen anderen Checkout auswaehlen."""
    with pytest.raises(ValueError, match="absolut"):
        deployment.script_definitions(path)


@pytest.mark.parametrize(
    ("status", "expected"),
    [(None, None), ("unchanged", None), ("active", True), ("inactive", False)],
)
def test_customer_form_requires_explicit_status_choice(tmp_path, status, expected):
    """Ein unangetastetes Formular darf einen Kunden nicht deaktivieren."""
    definition = next(
        item
        for item in deployment.script_definitions(str(tmp_path))
        if item["path"] == "f/rechnung/customer_edit"
    )
    field = definition["schema"]["properties"]["active"]
    assert field["type"] == "string"
    assert field["default"] == "unchanged"
    assert field["enum"] == ["unchanged", "active", "inactive"]
    namespace = {}
    exec(definition["content"], namespace)
    captured = {}

    def capture(action, arguments):
        """Erfasst nur die erzeugten Argumente ohne Projekt- oder Dateizugriff."""
        captured.update(arguments)
        return action

    namespace["invoke"] = capture
    arguments = {"customer_id": "fixture"}
    if status is not None:
        arguments["active"] = status
    assert namespace["main"](**arguments) == "customer_edit"
    assert captured["active"] is expected
    assert captured["apply"] is False


def test_flow_has_three_steps_without_retry_and_defaults_to_dry_run():
    """Der Flow prueft zuerst, fuehrt einmal aus und zeigt danach sein Ergebnis."""
    flow = deployment.invoice_flow()
    modules = flow["value"]["modules"]

    assert [module["id"] for module in modules] == ["validate", "execute", "result"]
    assert flow["schema"]["properties"]["mode"]["default"] == "dry-run"
    assert all("retry" not in module for module in modules)
    assert all("retry" not in module["value"] for module in modules)
    assert "retry" not in flow["value"]
    assert modules[0]["value"]["input_transforms"] == {}
    execution = modules[1]["value"]["input_transforms"]
    assert execution["mode"]["expr"] == "flow_input.mode || 'dry-run'"
    assert "smtp_resource" in execution
    assert "smtp_resource" not in modules[2]["value"]["input_transforms"]
    result_transform = modules[2]["value"]["input_transforms"]["result"]
    assert result_transform["expr"] == "results.execute"
    assert modules[1]["value"]["path"] == "f/rechnung/run_native"
    json.dumps(flow)


def test_creation_form_requires_explicit_structured_identity(tmp_path):
    """Die Anlage fragt einzelne Namen und eine ausdrueckliche Briefanrede ab."""
    definition = next(
        item
        for item in deployment.script_definitions(str(tmp_path))
        if item["path"] == "f/rechnung/customer_create"
    )
    schema = definition["schema"]
    assert {"first_name", "last_name", "salutation"} <= set(schema["required"])
    assert schema["properties"]["salutation"]["enum"] == [
        "frau",
        "herr",
        "neutral",
        "organisation",
    ]
    assert "contact_name" not in schema["properties"]


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        (None, None),
        ("unchanged", None),
        ("frau", "frau"),
        ("organisation", "organisation"),
    ],
)
def test_edit_form_preserves_or_explicitly_changes_salutation(
    tmp_path, selection, expected
):
    """Ein unangetastetes Anredefeld behaelt den bestehenden Kontakt bei."""
    definition = next(
        item
        for item in deployment.script_definitions(str(tmp_path))
        if item["path"] == "f/rechnung/customer_edit"
    )
    field = definition["schema"]["properties"]["salutation"]
    assert field["default"] == "unchanged"
    assert field["enum"] == ["unchanged", "frau", "herr", "neutral", "organisation"]
    namespace = {}
    exec(definition["content"], namespace)
    captured = {}

    def capture(action, arguments):
        """Erfasst nur den Formularpayload, ohne einen Worker aufzurufen."""
        captured.update(arguments)
        return action

    namespace["invoke"] = capture
    arguments = {"customer_id": "fixture", "first_name": "", "last_name": ""}
    if selection is not None:
        arguments["salutation"] = selection
    assert namespace["main"](**arguments) == "customer_edit"
    assert captured["salutation"] == expected
    assert captured["first_name"] == captured["last_name"] == ""
    assert captured["apply"] is False


def test_invoice_flow_has_one_explicit_notification_owner(tmp_path):
    """Flowfehler nutzen denselben repo-eigenen Bridge-Einstieg ohne Doppelmeldung."""
    flow = deployment.invoice_flow()["value"]
    execute = flow["modules"][1]["value"]["input_transforms"]
    assert execute["notify_errors"] == {"type": "static", "value": False}
    handler = flow["failure_module"]["value"]
    assert handler["path"] == "f/rechnung/report_failure"
    assert handler["input_transforms"]["mode"]["expr"] == "flow_input.mode || 'dry-run'"
    definitions = deployment.script_definitions(str(tmp_path))
    handler_script = next(
        item for item in definitions if item["path"] == "f/rechnung/report_failure"
    )
    assert "integrations/windmill/bridge.py" in handler_script["content"]
    assert "return invoke('report_failure'" in handler_script["content"]
    assert "error" not in handler_script["schema"]["properties"]
