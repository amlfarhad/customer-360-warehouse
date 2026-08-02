"""CLI for the Customer 360 analytics warehouse."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.build_warehouse import build_warehouse
from src.generate_data import generate_source_data
from src.run_quality_checks import run_quality_audit
from src.write_readout import write_dashboard_html, write_quality_report, write_readout
from src.write_workspace import write_decision_workspace


def paths(workspace: str | Path) -> dict[str, Path]:
    root = Path(workspace)
    return {
        "root": root,
        "raw": root / "data" / "raw",
        "warehouse": root / "data" / "warehouse",
        "db": root / "data" / "warehouse" / "customer360.duckdb",
        "reports": root / "reports",
    }


def command_generate(args: argparse.Namespace) -> None:
    p = paths(args.workspace)
    manifest = generate_source_data(p["raw"], seed=args.seed, accounts=args.accounts)
    print(f"Generated source data: {len(manifest.files)} files in {p['raw']}")


def command_build(args: argparse.Namespace) -> None:
    p = paths(args.workspace)
    result = build_warehouse(p["raw"], p["db"])
    print(f"Built warehouse: {len(result.tables_built)} models in {p['db']}")


def command_quality(args: argparse.Namespace):
    p = paths(args.workspace)
    audit = run_quality_audit(p["raw"], p["db"])
    p["reports"].mkdir(parents=True, exist_ok=True)
    (p["reports"] / "data_quality_audit.json").write_text(json.dumps(audit.to_dict(), indent=2))
    write_quality_report(audit, p["reports"] / "data_quality_audit.md")
    print(f"Quality audit: {audit.summary.passed} passed, {audit.summary.warnings} warnings, {audit.summary.failed} failed")
    return audit


def command_readout(args: argparse.Namespace, audit=None) -> None:
    p = paths(args.workspace)
    if audit is None:
        audit = run_quality_audit(p["raw"], p["db"])
    write_readout(p["db"], audit, p["reports"] / "customer_health_readout.md")
    write_dashboard_html(p["db"], p["reports"] / "dashboard.html")
    write_decision_workspace(p["db"], audit, p["root"] / "app" / "data" / "workspace.json", seed=args.seed)
    print(f"Wrote readout: {p['reports']}")
    print(f"Wrote decision workspace: {p['root'] / 'app' / 'data' / 'workspace.json'}")


def command_workspace(args: argparse.Namespace) -> None:
    """Export only the static decision-workspace payload."""

    p = paths(args.workspace)
    audit = run_quality_audit(p["raw"], p["db"])
    output = p["root"] / "app" / "data" / "workspace.json"
    write_decision_workspace(p["db"], audit, output, seed=args.seed)
    print(f"Wrote decision workspace: {output}")


def command_demo(args: argparse.Namespace) -> None:
    command_generate(args)
    command_build(args)
    audit = command_quality(args)
    command_readout(args, audit=audit)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Customer 360 analytics warehouse")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ["generate-data", "build-warehouse", "quality-audit", "write-readout", "write-workspace", "demo"]:
        sub = subparsers.add_parser(name)
        sub.add_argument("--workspace", default=".", help="Workspace root for artifacts")
        sub.add_argument("--accounts", type=int, default=500, help="Number of synthetic accounts")
        sub.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    subparsers.choices["generate-data"].set_defaults(func=command_generate)
    subparsers.choices["build-warehouse"].set_defaults(func=command_build)
    subparsers.choices["quality-audit"].set_defaults(func=command_quality)
    subparsers.choices["write-readout"].set_defaults(func=command_readout)
    subparsers.choices["write-workspace"].set_defaults(func=command_workspace)
    subparsers.choices["demo"].set_defaults(func=command_demo)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
