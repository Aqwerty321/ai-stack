#!/usr/bin/env python3
"""Enable extra SearXNG engines in /etc/searxng/settings.yml (run as root).

Upstream SearXNG ships bing, google, openalex and crossref with `disabled: true`, so
listing them in keep_only is not enough: each needs an `engines:` entry with
`disabled: false`. Startpage, Qwant and Google Scholar are left out because they
answered with CAPTCHA/access-denied from this machine (2026-10-18).

Idempotent: running twice changes nothing. Text edit (not a YAML dump) so the rest of
the file, including secret_key, is untouched. Usage:
  sudo python3 searxng_enable_engines.py [/etc/searxng/settings.yml]
"""
import sys

ENABLE = ["google", "bing", "mojeek", "wikipedia", "semantic scholar", "openalex", "crossref"]


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/etc/searxng/settings.yml"
    lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
    stripped = [l.strip() for l in lines]

    keep = [i for i, s in enumerate(stripped) if s == "keep_only:"]
    auto = [i for i, s in enumerate(stripped) if s.startswith("autocomplete:")]
    eng = [i for i, l in enumerate(lines) if l.rstrip() == "engines:"]  # top-level only
    assert len(keep) == 1 and len(auto) == 1 and len(eng) == 1, ("unexpected layout", keep, auto, eng)

    # Existing keep_only items are the '- x' lines directly under keep_only:.
    k = keep[0] + 1
    kept = []
    while k < len(lines) and stripped[k].startswith("- "):
        kept.append(stripped[k][2:].strip())
        k += 1
    configured = {s.split(":", 1)[1].strip() for s in stripped if s.startswith("- name:")}

    # Apply bottom-up so earlier indices stay valid.
    edits = []
    new_entries = [e for e in ENABLE if e not in configured]
    entry_text = "".join(f"  - name: {e}\n    disabled: false\n" for e in new_entries)
    for e in ENABLE:  # existing entries (e.g. google) need an explicit disabled: false
        if e in configured:
            idx = next(i for i, s in enumerate(stripped) if s == f"- name: {e}")
            block = range(idx + 1, len(lines))
            has = any(stripped[j].startswith("disabled:") for j in block
                      if j < len(lines) and not stripped[j].startswith("- name:")
                      and all(not stripped[x].startswith("- name:") for x in range(idx + 1, j + 1)))
            if not has:
                edits.append((idx + 1, "    disabled: false\n"))
    if entry_text:
        edits.append((eng[0] + 1, entry_text))
    if not any(s.startswith("suspended_times:") for s in stripped):
        edits.append((auto[0] + 1, "  suspended_times:\n    SearxEngineTooManyRequests: 600\n"))
    missing = [e for e in ENABLE if e not in kept]
    if missing:
        edits.append((k, "".join(f"      - {e}\n" for e in missing)))

    for idx, text in sorted(edits, key=lambda x: x[0], reverse=True):
        lines.insert(idx, text)
    open(path, "w", encoding="utf-8").write("".join(lines))
    print(f"EDITED: {len(edits)} insertions; keep_only += {missing}; new engine entries {new_entries}")


if __name__ == "__main__":
    main()
