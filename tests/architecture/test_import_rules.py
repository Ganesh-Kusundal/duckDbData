"""
Architecture guardrail tests.

These are lightweight checks to prevent common boundary leaks:
- No `duckdb` imports under application strategies.
- No `src.infrastructure` imports under domain.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _py_files_under(path: Path):
    return [p for p in path.rglob("*.py") if p.is_file()]


def test_no_duckdb_in_application_strategies():
    strategies_dir = PROJECT_ROOT / "src" / "application" / "scanners" / "strategies"
    assert strategies_dir.exists(), f"Missing strategies dir: {strategies_dir}"

    violations = []
    for f in _py_files_under(strategies_dir):
        text = read_text(f)
        if "import duckdb" in text or "from duckdb" in text:
            violations.append(str(f))

    assert not violations, f"duckdb import(s) found in strategies: {violations}"


def test_domain_does_not_import_infrastructure():
    domain_dir = PROJECT_ROOT / "src" / "domain"
    assert domain_dir.exists(), f"Missing domain dir: {domain_dir}"

    violations = []
    for f in _py_files_under(domain_dir):
        text = read_text(f)
        if "from src.infrastructure" in text or "import src.infrastructure" in text:
            violations.append(str(f))

    assert not violations, f"Domain imports infrastructure: {violations}"


def test_application_strategies_do_not_import_infrastructure():
    strategies_dir = PROJECT_ROOT / "src" / "application" / "scanners" / "strategies"
    assert strategies_dir.exists(), f"Missing strategies dir: {strategies_dir}"

    violations = []
    for f in _py_files_under(strategies_dir):
        text = read_text(f)

        # Check for infrastructure imports outside of CLI entry points (main functions)
        if "from src.infrastructure" in text or "import src.infrastructure" in text:
            # Allow infrastructure imports in CLI entry points (main functions)
            # Extract the main function content
            lines = text.split('\n')
            in_main_function = False
            main_function_lines = []

            for i, line in enumerate(lines):
                if line.strip().startswith('def main('):
                    in_main_function = True
                elif in_main_function and line.strip().startswith('def ') and 'main' not in line:
                    # End of main function when we hit another function definition
                    break
                elif in_main_function:
                    main_function_lines.append(line)

            main_function_text = '\n'.join(main_function_lines)

            # Check if the infrastructure import is outside the main function
            if ("from src.infrastructure" in text.replace(main_function_text, "") or
                "import src.infrastructure" in text.replace(main_function_text, "")):
                violations.append(str(f))

    assert not violations, f"Strategies import infrastructure outside CLI entry points: {violations}"
