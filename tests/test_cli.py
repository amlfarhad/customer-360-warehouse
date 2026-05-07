import subprocess
import sys


def test_demo_cli_builds_complete_project_artifacts(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli",
            "demo",
            "--workspace",
            str(tmp_path),
            "--accounts",
            "250",
            "--seed",
            "42",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "generated source data" in result.stdout.lower()
    assert "built warehouse" in result.stdout.lower()
    assert "quality audit" in result.stdout.lower()
    assert "wrote readout" in result.stdout.lower()

    assert (tmp_path / "data" / "raw" / "crm_accounts.csv").exists()
    assert (tmp_path / "data" / "warehouse" / "customer360.duckdb").exists()
    assert (tmp_path / "reports" / "customer_health_readout.md").exists()
    assert (tmp_path / "reports" / "dashboard.html").exists()
