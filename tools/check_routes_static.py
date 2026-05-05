import re
from collections import defaultdict
from pathlib import Path


URL_TAG_RE = re.compile(r"\{%\s*url\s+(.+?)%\}", re.DOTALL)
FIRST_LITERAL_RE = re.compile(r"^\s*(['\"])(?P<name>.+?)\1")
APP_NAME_RE = re.compile(r"^\s*app_name\s*=\s*(['\"])(?P<name>.+?)\1", re.MULTILINE)
URL_NAME_RE = re.compile(r"\bname\s*=\s*(['\"])(?P<name>.+?)\1")

PY_NAMED_ROUTE_RE = re.compile(r"\b(?:redirect|reverse|reverse_lazy)\(\s*(['\"])(?P<name>.+?)\1")


def index_to_line(text, index):
    return text.count("\n", 0, index) + 1


def extract_named_routes_from_urls_py(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = APP_NAME_RE.search(text)
    namespace = m.group("name") if m else None

    names = set()
    for mm in URL_NAME_RE.finditer(text):
        name = mm.group("name")
        if namespace:
            names.add(f"{namespace}:{name}")
        else:
            names.add(name)
    return names


def main():
    base_dir = Path(__file__).resolve().parents[1]

    url_files = [
        base_dir / "bmis" / "urls.py",
        base_dir / "users" / "urls.py",
        base_dir / "residents" / "urls.py",
        base_dir / "analytics" / "urls.py",
        base_dir / "gis_mapping" / "urls.py",
    ]

    known_routes = set()
    for p in url_files:
        if p.exists():
            known_routes |= extract_named_routes_from_urls_py(p)

    missing = defaultdict(list)
    template_files = list(base_dir.rglob("templates/**/*.html"))
    for path in template_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in URL_TAG_RE.finditer(text):
            body = m.group(1)
            mm = FIRST_LITERAL_RE.match(body)
            if not mm:
                continue
            name = mm.group("name")
            if name not in known_routes:
                missing[name].append(("template", str(path), index_to_line(text, m.start())))

    python_roots = [
        base_dir / "bmis",
        base_dir / "users",
        base_dir / "residents",
        base_dir / "analytics",
        base_dir / "gis_mapping",
    ]
    for root in python_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for m in PY_NAMED_ROUTE_RE.finditer(text):
                name = m.group("name")
                if ":" not in name:
                    continue
                if name not in known_routes:
                    missing[name].append(("python", str(path), index_to_line(text, m.start())))

    print(f"known_named_routes={len(known_routes)}")
    print(f"templates_scanned={len(template_files)}")
    print(f"missing_named_routes={len(missing)}")

    for name in sorted(missing.keys()):
        print(name)
        for kind, file_path, line in missing[name]:
            print(f"  {kind}: {file_path}:{line}")

    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())

