#!/usr/bin/env python3
"""
Upload trabajos from a Google Sheet into Firestore collection `Trabajo`.

Usage:
  - Ensure `serviceAccountKey.json` (Firebase service account) exists at project root.
  - Ensure the service account has access to the Google Sheet (share the sheet with the service account email).
  - Install dependencies: pip install firebase-admin gspread google-auth

Example:
  source .venv/bin/activate
  pip install firebase-admin gspread google-auth
  python scripts/upload_trabajos_from_sheet.py --sheet-id 1nyvdwnW9lGCZp6zwx_Ny8wwFSPe3jxl2S79uBcWBJ1k --sheet-name SCRIPT

The script supports --dry-run to show what would be written without modifying Firestore.
"""
import argparse
import re
import sys
import csv
from pathlib import Path
from typing import List

try:
    import gspread
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception as e:  # pragma: no cover - helpful error if deps missing
    print("Missing dependency; run: pip install firebase-admin gspread google-auth")
    raise


def parse_resoluciones(raw: str) -> List[str]:
    """Parse the Resolucion cell into a list.

    The sheet shows values like: "16/25 // 17/25 // 236/24" so we split on // and strip.
    """
    if not raw:
        return []
    # replace other separators and split
    parts = re.split(r"//|,|;", str(raw))
    return [p.strip() for p in parts if p and p.strip()]


def slugify(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = re.sub(r"-+", "-", t).strip("-")
    return t or None


def normalize_row(row: dict) -> dict:
    """Normalize spreadsheet row to Firestore document fields.

    Expected columns in sheet (case-insensitive): Grupo, Titulo, Descripcion, Sistema, Resolucion
    """
    # Normalize keys to lowercase without accents/spaces
    keymap = {k.strip().lower(): k for k in row.keys()}

    def get(col_names, default=""):
        for name in col_names:
            k = name.lower()
            if k in keymap:
                return row.get(keymap[k], default)
        return default

    titulo = str(get(["titulo", "title"]).strip())
    grupo = str(get(["grupo", "group"]).strip())
    descripcion = str(get(["descripcion", "description"]).strip())
    # Convert escaped newline sequences (e.g. "\\n" from CSV) into real newlines
    if descripcion:
        descripcion = descripcion.replace('\\n', '\n')
    # Familia (optional column in new CSVs)
    familia = str(get(["familia", "family"]).strip())
    sistema = str(get(["sistema", "system"]).strip())
    resolucion_raw = str(get(["resolucion", "resoluciones", "res"]).strip())

    resoluciones = parse_resoluciones(resolucion_raw)

    doc = {
        "grupo": grupo,
        "titulo": titulo,
        "descripcion": descripcion,
        "familia": familia,
        "sistema": sistema,
        # keep both raw and parsed resolutions
        "resolucion_raw": resolucion_raw,
        "resoluciones": resoluciones,
    }
    return doc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-id", required=False, help="Google Sheet ID (the long id in the sheet URL)")
    parser.add_argument("--csv", dest="csv", required=False, help="Path to a local CSV file export of the worksheet (alternative to --sheet-id)")
    parser.add_argument("--sheet-name", default="SCRIPT", help="Worksheet name (default: SCRIPT)")
    parser.add_argument("--service-account", default="serviceAccountKey.json", help="Path to Firebase/Google service account JSON")
    parser.add_argument("--collection", default="Trabajo", help="Firestore collection name (default: Trabajo)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Firestore; just print actions")
    parser.add_argument("--patch-only", action="store_true", help="Only update the 'familia' field on existing documents (do not create or overwrite full document)")
    args = parser.parse_args()

    sa_path = Path(args.service_account)

    # If CSV provided, read records locally; else use Google Sheets via gspread
    records = []
    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"CSV file not found: {csv_path.resolve()}")
            sys.exit(1)
        # Read CSV with headers
        with csv_path.open(newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            records = list(reader)
        print(f"Loaded {len(records)} rows from CSV {csv_path.name}")
    else:
        # Service account is required to access Google Sheets
        if not sa_path.exists():
            print(f"Service account file not found: {sa_path.resolve()}")
            print("Place your Firebase service account JSON at this path or pass --service-account.")
            sys.exit(1)

        # Authenticate to Google Sheets using service account (same key works if the service account has Sheets access)
        gc = gspread.service_account(filename=str(sa_path))

        try:
            sh = gc.open_by_key(args.sheet_id)
        except Exception as e:
            print(f"Error opening sheet id {args.sheet_id}: {e}")
            sys.exit(1)

        try:
            ws = sh.worksheet(args.sheet_name)
        except Exception as e:
            print(f"Error opening worksheet '{args.sheet_name}': {e}")
            # list available worksheets
            try:
                print("Available sheets:", [s.title for s in sh.worksheets()])
            except Exception:
                pass
            sys.exit(1)

        records = ws.get_all_records()
        print(f"Loaded {len(records)} rows from {args.sheet_name}")

    # Initialize Firebase Admin / Firestore only if we will write (not dry-run)
    db = None
    if not args.dry_run:
        if not sa_path.exists():
            print(f"Service account file not found: {sa_path.resolve()}")
            print("Required to write to Firestore. Pass --service-account or place the file at the default path.")
            sys.exit(1)
        cred = credentials.Certificate(str(sa_path))
        try:
            firebase_admin.initialize_app(cred)
        except Exception:
            # already initialized
            pass
        db = firestore.client()

    collection_ref = None
    written = 0
    if db is not None:
        collection_ref = db.collection(args.collection)

    for i, row in enumerate(records, start=1):
        doc = normalize_row(row)
        titulo = doc.get("titulo")
        if not titulo:
            print(f"Skipping row {i}: empty titulo")
            continue

        # Prepare document id using slugified title to avoid duplicates
        slug = slugify(titulo) or None
        if slug:
            doc_id = slug
        else:
            doc_id = None

        # If patch-only requested, only update the 'familia' field on existing documents
        if args.patch_only:
            # Dry-run: just show the patch proposal
            if args.dry_run:
                print(f"[DRY PATCH] Would patch doc (id={doc_id}) set familia={doc.get('familia')}")
                written += 1
                continue

            # Real patch: require a document id and existing document
            if not doc_id:
                print(f"Skipping row {i}: cannot patch without a slug id for titulo='{titulo}'")
                continue

            try:
                existing = collection_ref.document(doc_id).get()
                if not existing.exists:
                    print(f"Skipping row {i}: document id={doc_id} does not exist, not creating")
                    continue
                # perform a partial update of only the familia field
                collection_ref.document(doc_id).update({"familia": doc.get("familia")})
                print(f"Patched row {i} -> {titulo} (id={doc_id}) familia={doc.get('familia')}")
                written += 1
            except Exception as e:
                print(f"Error patching row {i} ({titulo}): {e}")
            continue

        # Default behavior: write/overwrite full document
        if args.dry_run:
            print(f"[DRY] Would write doc (id={doc_id}): {doc}")
            written += 1
            continue

        try:
            if doc_id:
                collection_ref.document(doc_id).set(doc)
            else:
                collection_ref.add(doc)
            print(f"Wrote row {i} -> {titulo} (id={doc_id})")
            written += 1
        except Exception as e:
            print(f"Error writing row {i} ({titulo}): {e}")

    print(f"Done. Processed {len(records)} rows, written: {written}")


if __name__ == "__main__":
    main()
