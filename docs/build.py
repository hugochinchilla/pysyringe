#!/usr/bin/env python3
"""Build the PySyringe documentation site from Markdown source."""

import re
from html import escape
from pathlib import Path

import markdown
from markdown.extensions.admonition import AdmonitionExtension
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension

DOCS_DIR = Path(__file__).parent
PACKAGE_DIR = DOCS_DIR.parent / "pysyringe"

# Ordered newest-first.  The first entry is treated as "current" and built
# into docs/index.html.  Older entries are static snapshots that already
# live under docs/<path>/.
DOC_VERSIONS = [
    {"label": "2.0", "path": ".", "current": True},
    {"label": "1.5", "path": "1.5"},
]

NAV_SECTIONS = [
    ("Getting Started", ["introduction", "installation", "quick-start"]),
    (
        "Core Concepts",
        ["container", "resolution", "factories", "container-aware-factories", "inference", "aliases"],
    ),
    ("Dependency Injection", ["inject-decorator", "provide"]),
    ("Singletons", ["singleton", "thread-local-singleton"]),
    ("Testing", ["mocks", "override-context", "legacy-mocks"]),
    (
        "Advanced",
        ["thread-safety", "resolution-cache", "optional-types", "errors"],
    ),
    ("Reference", ["api-container", "api-singleton", "api-exceptions"]),
]


def read_version():
    """Read __version__ from pysyringe/__init__.py and return major.minor."""
    text = (PACKAGE_DIR / "__init__.py").read_text()
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not match:
        msg = "Could not find __version__ in pysyringe/__init__.py"
        raise RuntimeError(msg)
    full = match.group(1)
    # Extract major.minor from versions like "1.4.0", "1.3.1.dev13+g..."
    parts = re.match(r"(\d+\.\d+)", full)
    return parts.group(1) if parts else full


def build_version_options():
    """Generate <option> elements for the version switcher."""
    options = []
    for v in DOC_VERSIONS:
        href = "index.html" if v.get("current") else f"{v['path']}/index.html"
        selected = " selected" if v.get("current") else ""
        options.append(f'      <option value="{href}"{selected}>v{v["label"]}</option>')
    return "\n".join(options)


def extract_headings(md_source):
    """Extract {#id} -> heading text mapping from Markdown source."""
    heading_map = {}
    pattern = re.compile(r"^#{2,3}\s+(.+?)\s*\{#([a-z0-9-]+)\}\s*$", re.MULTILINE)
    for match in pattern.finditer(md_source):
        text, anchor_id = match.group(1), match.group(2)
        heading_map[anchor_id] = escape(text)
    return heading_map


def build_sidebar(heading_map):
    """Generate sidebar HTML from nav structure and heading text."""
    parts = []
    for section_title, anchor_ids in NAV_SECTIONS:
        parts.append('    <div class="nav-section">')
        parts.append(f'      <div class="nav-section-title">{section_title}</div>')
        for anchor_id in anchor_ids:
            text = heading_map.get(anchor_id, anchor_id)
            parts.append(f'      <a href="#{anchor_id}">{text}</a>')
        parts.append("    </div>")
    return "\n".join(parts)


def postprocess(html):
    """Post-process rendered HTML for CSS compatibility."""
    # Remap admonition classes to callout classes
    html = html.replace('class="admonition ', 'class="callout ')
    html = html.replace('class="admonition"', 'class="callout"')

    # Remap admonition-title to strong block
    html = re.sub(
        r'<p class="admonition-title">(\w+)</p>',
        r"<strong>\1</strong>",
        html,
    )

    # Add section-anchor class to h2 and h3 with ids
    html = re.sub(
        r'<h([23]) id="([^"]+)">',
        r'<h\1 id="\2" class="section-anchor">',
        html,
    )

    return html


def build():
    content_md = (DOCS_DIR / "content.md").read_text()
    template = (DOCS_DIR / "template.html").read_text()

    heading_map = extract_headings(content_md)

    md = markdown.Markdown(
        extensions=[
            FencedCodeExtension(),
            CodeHiliteExtension(
                css_class="highlight",
                use_classes=True,
                guess_lang=False,
            ),
            TableExtension(),
            TocExtension(permalink=False),
            AttrListExtension(),
            AdmonitionExtension(),
            "smarty",
        ]
    )

    content_html = md.convert(content_md)
    content_html = postprocess(content_html)

    sidebar_html = build_sidebar(heading_map)

    version = read_version()
    version_options = build_version_options()

    output = template.replace("{{VERSION}}", version)
    output = output.replace("{{VERSION_OPTIONS}}", version_options)
    output = output.replace("{{CONTENT}}", content_html)
    output = output.replace("{{SIDEBAR}}", sidebar_html)

    (DOCS_DIR / "index.html").write_text(output)
    print("Built docs/index.html")


if __name__ == "__main__":
    build()
