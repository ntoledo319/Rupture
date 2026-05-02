"""Allow `python -m al2023_gate ...`."""

from .cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
