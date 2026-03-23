from functools import lru_cache
from pathlib import Path

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe


register = template.Library()


def _static_source_dirs():
    static_dirs = getattr(settings, "STATICFILES_DIRS", None) or []
    if static_dirs:
        return [Path(directory).resolve() for directory in static_dirs]
    return [(Path(settings.BASE_DIR) / "static_src").resolve()]


@lru_cache(maxsize=16)
def _read_static_source(relative_path):
    normalized = Path(relative_path).as_posix().lstrip("/")

    for base_dir in _static_source_dirs():
        candidate = (base_dir / normalized).resolve()
        try:
            candidate.relative_to(base_dir)
        except ValueError:
            continue

        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Static asset not found: {relative_path}")


@register.simple_tag
def inline_css(relative_path):
    return mark_safe(f"<style>{_read_static_source(relative_path)}</style>")


@register.simple_tag
def inline_js(relative_path):
    return mark_safe(f"<script>{_read_static_source(relative_path)}</script>")
