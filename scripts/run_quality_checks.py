"""Run the same repository quality gates used before submission."""
import subprocess
import sys


COMMANDS = [
    [sys.executable, "-m", "compileall", "-q", "app", "tests", "migrations"],
    [sys.executable, "-m", "pytest", "-q"],
    [sys.executable, "-m", "ruff", "check", "app", "tests", "migrations"],
]


def main() -> None:
    for command in COMMANDS:
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
