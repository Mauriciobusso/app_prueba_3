#!/usr/bin/env python3
"""Fix descripcion fields in Firestore by converting literal "\\n" into real newlines.

Usage:
  source .venv/bin/activate
  python scripts/fix_trabajos_newlines.py --service-account app_prueba_3/serviceAccountKey.json --collection Trabajo --dry-run --limit 5

Options:
  --dry-run    Show documents that would be changed but don't write.
  --apply      Apply changes (mutually exclusive with --dry-run).
  --limit N    Stop after N changed docs (useful for testing).
"""
import argparse
from pathlib import Path
import sys

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception:
    print("Missing firebase-admin. Install with: pip install firebase-admin")
    raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-account", default="app_prueba_3/serviceAccountKey.json")
    parser.add_argument("--collection", default="Trabajo")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="Do not write; just show proposed updates")
    group.add_argument("--apply", action="store_true", help="Apply updates to Firestore")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of documents to change (0 = no limit)")
    args = parser.parse_args()

    sa_path = Path(args.service_account)
    if not sa_path.exists():
        print(f"Service account file not found: {sa_path.resolve()}")
        sys.exit(1)

    cred = credentials.Certificate(str(sa_path))
    try:
        firebase_admin.initialize_app(cred)
    except Exception:
        # already initialized
        pass
    db = firestore.client()

    collection_ref = db.collection(args.collection)

    changed = 0
    scanned = 0
    samples = []

    for doc in collection_ref.stream():
        scanned += 1
        data = doc.to_dict() or {}
        # field name 'descripcion' is used in import; accept both
        desc_field = None
        if 'descripcion' in data:
            desc_field = 'descripcion'
        elif 'description' in data:
            desc_field = 'description'

        if not desc_field:
            continue

        desc = data.get(desc_field)
        if not isinstance(desc, str):
            continue

        # Look for the literal backslash + n sequence
        if '\\n' in desc:
            new_desc = desc.replace('\\n', '\n')
            changed += 1
            samples.append((doc.id, desc_field, desc, new_desc))
            print(f"[PROPOSE] doc={doc.id} field={desc_field} -- will replace literal \\n with real newlines")

            if args.apply:
                try:
                    collection_ref.document(doc.id).update({desc_field: new_desc})
                    print(f"[APPLIED] doc={doc.id}")
                except Exception as e:
                    print(f"[ERROR] applying doc={doc.id}: {e}")

            if args.limit and changed >= args.limit:
                break

    print(f"Scanned {scanned} documents; {changed} would be changed.")
    if samples:
        print('\nSample change (first 3):')
        for sid, field, old, new in samples[:3]:
            print(f"- doc: {sid} field: {field}")
            print("  old (snippet):", repr(old[:200]))
            print("  new (snippet):", repr(new[:200]))


if __name__ == '__main__':
    main()
