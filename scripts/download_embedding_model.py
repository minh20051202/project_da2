#!/usr/bin/env python3
"""Download the pinned public E5 ONNX model; no dossier data is uploaded."""
import argparse
import hashlib
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
FILES = {"onnx/model_qint8_avx512_vnni.onnx": "model.onnx", "onnx/tokenizer.json": "tokenizer.json",
         "README.md": "MODEL_CARD.md"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "models/multilingual-e5-small")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for remote, local in FILES.items():
        target = args.output / local
        if not target.exists():
            temp = target.with_suffix(target.suffix + ".download")
            url = f"https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{remote}"
            print(f"Downloading {remote}", flush=True)
            with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            os.replace(temp, target)
        print(local, target.stat().st_size, hashlib.sha256(target.read_bytes()).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
