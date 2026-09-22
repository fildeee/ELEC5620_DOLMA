#!/usr/bin/env python
"""
Run the backend test suite without needing pytest installed.

    python tests/run_tests.py          # from the backend directory

Every `test_*` function in every `test_*.py` file beside this one is run.
pytest works too, if you have it: `python -m pytest tests`.
"""

import importlib
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
for path in (BACKEND, HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def main() -> int:
    modules = sorted(
        f[:-3] for f in os.listdir(HERE)
        if f.startswith("test_") and f.endswith(".py")
    )
    passed, failures = 0, []

    for module_name in modules:
        module = importlib.import_module(module_name)
        print(f"\n{DIM}{module_name}{RESET}")
        for name in sorted(n for n in dir(module) if n.startswith("test_")):
            test = getattr(module, name)
            if not callable(test):
                continue
            try:
                test()
            except Exception:
                failures.append((module_name, name, traceback.format_exc()))
                print(f"  {RED}FAIL{RESET}  {name}")
            else:
                passed += 1
                print(f"  {GREEN}pass{RESET}  {name}")

    print()
    for module_name, name, tb in failures:
        print(f"{RED}{'=' * 70}{RESET}\n{module_name}.{name}\n{tb}")

    total = passed + len(failures)
    if failures:
        print(f"{RED}{len(failures)} of {total} tests failed{RESET}")
        return 1
    print(f"{GREEN}all {total} tests passed{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
