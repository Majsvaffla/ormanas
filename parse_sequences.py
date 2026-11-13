from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sequence_text import SequenceSyntaxError, parse_sequences


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile sequences.txt to JSON.")
    parser.add_argument("source_path", type=Path)
    arguments = parser.parse_args()

    try:
        library = parse_sequences(arguments.source_path.read_text(encoding="utf-8"))
    except SequenceSyntaxError as error:
        raise SystemExit(str(error))

    print("compiled {} sequences".format(len(library)), file=sys.stderr)
    sys.stdout.write(json.dumps(library))

if __name__ == "__main__":
    main()
