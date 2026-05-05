import re
from collections import defaultdict
import os
import sys
from pathlib import Path

import django
from django.conf import settings
from django.urls import get_resolver


def index_to_line(text, index):
    return text.count("\n", 0, index) + 1


def main():
    print("scan_begin", flush=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bmis.settings")
    django.setup()
    base_dir = Path(settings.BASE_DIR)
    reverse_dict = get_resolver().reverse_dict

    url_tag_re = re.compile(r"\{%\s*url\s+(.+?)%\}", re.DOTALL)
    first_literal_re = re.compile(r"^\s*(['\"])(?P<name>.+?)\1")
    py_named_re = re.compile(r"\b(?:redirect|reverse|reverse_lazy)\(\s*(['\"])(?P<name>.+?)\1")

    missing = defaultdict(list)
    scanned_templates = 0
    scanned_python = 0
    template_url_tags = 0
    python_named_routes = 0

    template_files = list(base_dir.rglob("templates/**/*.html"))
    for path in template_files:
        scanned_templates += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in url_tag_re.finditer(text):
            body = m.group(1)
            mm = first_literal_re.match(body)
            if not mm:
                continue
            template_url_tags += 1
            name = mm.group("name")
            if name not in reverse_dict:
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
            scanned_python += 1
            text = path.read_text(encoding="utf-8", errors="ignore")
            for m in py_named_re.finditer(text):
                name = m.group("name")
                if ":" not in name:
                    continue
                python_named_routes += 1
                if name not in reverse_dict:
                    missing[name].append(("python", str(path), index_to_line(text, m.start())))

    print("scan_end", flush=True)
    print(f"templates_scanned={scanned_templates}", flush=True)
    print(f"python_scanned={scanned_python}", flush=True)
    print(f"template_url_tags_with_literal_names={template_url_tags}", flush=True)
    print(f"python_named_route_refs_with_namespace={python_named_routes}", flush=True)
    print(f"missing_named_routes={len(missing)}", flush=True)

    if not missing:
        return 0

    for name in sorted(missing.keys()):
        print(name, flush=True)
        for kind, file_path, line in missing[name]:
            print(f"  {kind}: {file_path}:{line}", flush=True)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
