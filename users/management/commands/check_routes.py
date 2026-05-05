import re
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import get_resolver


URL_TAG_RE = re.compile(r"\{%\s*url\s+(.+?)%\}", re.DOTALL)
FIRST_LITERAL_RE = re.compile(r"^\s*(['\"])(?P<name>.+?)\1")

PY_REDIRECT_RE = re.compile(r"\b(?:redirect|reverse|reverse_lazy)\(\s*(['\"])(?P<name>.+?)\1")


def iter_template_url_names(text):
    for m in URL_TAG_RE.finditer(text):
        tag_body = m.group(1)
        first_literal = FIRST_LITERAL_RE.match(tag_body)
        if not first_literal:
            continue
        yield first_literal.group("name"), m.start()


def iter_python_named_routes(text):
    for m in PY_REDIRECT_RE.finditer(text):
        yield m.group("name"), m.start()


def index_to_line(text, index):
    return text.count("\n", 0, index) + 1


class Command(BaseCommand):
    def handle(self, *args, **options):
        resolver = get_resolver()
        reverse_dict = resolver.reverse_dict
        base_dir = Path(settings.BASE_DIR)

        missing = defaultdict(list)
        scanned = 0
        template_url_tags = 0
        python_named_routes = 0

        for path in base_dir.rglob("templates/**/*.html"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            scanned += 1
            for name, idx in iter_template_url_names(text):
                template_url_tags += 1
                if name not in reverse_dict:
                    missing[name].append((str(path), index_to_line(text, idx), "template"))

        for path in base_dir.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for name, idx in iter_python_named_routes(text):
                if ":" in name and name not in reverse_dict:
                    python_named_routes += 1
                    missing[name].append((str(path), index_to_line(text, idx), "python"))

        if not missing:
            print(f"OK: scanned {scanned} template files", flush=True)
            print(f"OK: found {template_url_tags} template url tags with literal names", flush=True)
            print(f"OK: found {python_named_routes} python named route references", flush=True)
            print("OK: no missing named routes found", flush=True)
            return

        print("Missing named routes:", flush=True)
        for name in sorted(missing.keys()):
            print(f"- {name}", flush=True)
            for file_path, line, kind in missing[name]:
                print(f"  - {kind}: {file_path}:{line}", flush=True)

        raise SystemExit(1)
