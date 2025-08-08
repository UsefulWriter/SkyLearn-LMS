#!/usr/bin/env python3
import os
import zipfile
from pathlib import Path

def zipdir(src_dir: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for f in files:
                full = Path(root) / f
                rel = full.relative_to(src_dir)
                zf.write(full, arcname=str(rel))

def main():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    sample_dir = project_root / "samples" / "scorm" / "openai-gpt5"
    if not (sample_dir / "imsmanifest.xml").exists():
        raise SystemExit(f"imsmanifest.xml not found in {sample_dir}. Aborting.")
    dist_dir = project_root / "samples" / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    out_zip = dist_dir / "OpenAI-GPT5_SCORM12.zip"
    zipdir(sample_dir, out_zip)
    print(f"SCORM package created: {out_zip}")

if __name__ == "__main__":
    main()
