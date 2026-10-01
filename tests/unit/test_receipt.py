from pathlib import Path

from vaultin.ledger.receipt import ReceiptData, ReceiptWriter


def test_receipt_lists_actual_changed_paths(tmp_path: Path) -> None:
    data = ReceiptData(
        execution_id="exec_1",
        project="demo",
        objective="Change API validation",
        files_changed=["src/api.py", "tests/test_api.py"],
        validations=["pytest: PASS"],
        git={"project": "abc123", "vaultin": "def456"},
        status="COMPLETED",
        pending=[],
    )
    path = ReceiptWriter(tmp_path).write(data)
    text = path.read_text(encoding="utf-8")
    assert "src/api.py" in text
    assert "tests/test_api.py" in text
    assert "abc123" in text


def test_receipt_explicitly_says_when_no_files_changed(tmp_path: Path) -> None:
    data = ReceiptData(
        execution_id="exec_2",
        project=None,
        objective="Inspect configuration",
        files_changed=[],
        validations=[],
        git={},
        status="COMPLETED",
        pending=[],
    )
    path = ReceiptWriter(tmp_path).write(data)
    assert "nenhum arquivo alterado" in path.read_text(encoding="utf-8").lower()
