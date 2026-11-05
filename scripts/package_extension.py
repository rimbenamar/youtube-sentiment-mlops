"""Empaquette l'extension Chrome dans dist/ (livrable « Extension packagée »).

    python scripts/package_extension.py
    python scripts/package_extension.py --api-url https://<nom>-7860.app.github.dev

Avec --api-url, l'URL de production est écrite dans config.js de la copie empaquetée
(le dossier chrome-extension/ d'origine n'est pas modifié).
"""
import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chrome-extension"
DIST = ROOT / "dist"
REQUIRED = ["manifest.json", "popup.html", "popup.css", "popup.js", "content.js", "background.js",
            "lib.js", "config.js", "icons/icon16.png", "icons/icon32.png", "icons/icon48.png", "icons/icon128.png"]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api-url", help="URL de l'API à inscrire comme valeur par défaut")
    args = p.parse_args()

    missing = [f for f in REQUIRED if not (SRC / f).exists()]
    if missing:
        raise SystemExit(f"Fichiers manquants dans chrome-extension/ : {missing}")
    manifest = json.loads((SRC / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]

    out_dir = DIST / "echo-extension"
    shutil.rmtree(out_dir, ignore_errors=True)
    shutil.copytree(SRC, out_dir, ignore=shutil.ignore_patterns("*.map", ".DS_Store", "Thumbs.db"))

    if args.api_url:
        url = args.api_url.strip().rstrip("/")
        if not re.match(r"^https?://", url):
            raise SystemExit("--api-url doit commencer par http:// ou https://")
        cfg = out_dir / "config.js"
        text = cfg.read_text(encoding="utf-8")
        text, n = re.subn(r'var DEFAULT_API_URL = "[^"]*";', f'var DEFAULT_API_URL = "{url}";', text)
        if n != 1:
            raise SystemExit("DEFAULT_API_URL introuvable dans config.js")
        cfg.write_text(text, encoding="utf-8")

    zip_path = DIST / f"echo-extension-v{version}.zip"
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out_dir.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(out_dir))  # manifest.json à la racine du zip
    size = zip_path.stat().st_size / 1024
    print(f"Extension v{version} -> {zip_path} ({size:.0f} Ko)")
    print(f"Dossier à charger dans chrome://extensions -> {out_dir}")
    if args.api_url:
        print(f"URL de l'API par défaut : {args.api_url}")


if __name__ == "__main__":
    main()
