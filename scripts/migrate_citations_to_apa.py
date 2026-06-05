"""Convert plain-text APA-style citations in reports/final_report.md to Pandoc
cite-key syntax that resolves via references.bib + apa.csl at compile time.

Strategy:
- Mapping table below pairs every (author surface, year) pattern observed in
  the report with its citation key in references.bib.
- Two forms detected:
  * Narrative ("Hines et al. (2024) showed...") -> @hines2024Defending
  * Parenthetical ("(Hines et al., 2024)") -> [@hines2024Defending]
- Year discrepancies between report text and bib entry are noted as TODO in
  the mapping (e.g., D'Amour 2022 vs damour2020 key; Toyer 2024 vs toyer2023).
  After conversion, Pandoc renders whatever year is in the bib entry.

Usage:
  Dry run (shows diff, makes no changes):
    python scripts/migrate_citations_to_apa.py

  Apply changes:
    python scripts/migrate_citations_to_apa.py --apply

  Unmatched patterns are reported at the end. Add to MAPPING and re-run.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "reports" / "final_report.md"


# (author_pattern, year) -> cite key
# Patterns are matched case-sensitively. Use the exact surface form that
# appears in the report text. Year is a string for safe regex compositing.
MAPPING: dict[tuple[str, str], str] = {
    # Direct prompt-injection literature
    ("Perez and Ribeiro", "2022"): "perez2022Ignore",
    ("Perez & Ribeiro", "2022"): "perez2022Ignore",
    ("Greshake et al.", "2023"): "greshake2023Not",
    ("Yi et al.", "2025"): "yi2025Benchmarking",
    ("Toyer et al.", "2024"): "toyer2023Tensor",  # bib has year=2023; ICLR 2024 publication
    ("Shen et al.", "2024"): "shen2024Anything",
    ("Russinovich, Salem and Eldan", "2024"): "russinovich2024Great",
    ("Hines et al.", "2024"): "hines2024Defending",
    ("Carlini et al.", "2023"): "carlini2023Are",
    ("Apruzzese et al.", "2022/2023"): "apruzzese2022Real",
    ("Apruzzese et al.", "2022"): "apruzzese2022Real",
    ("Boucher et al.", "2021"): "boucher2021Bad",
    ("Zhan et al.", "2024"): "zhan2024InjecAgent",
    ("Debenedetti et al.", "2024"): "debenedetti2024AgentDojo",

    # OWASP (multiple surface forms)
    ("OWASP", "2025"): "owasp2025LLM01",
    ("OWASP GenAI Project", "2025"): "owasp2025LLM01",

    # LLM-as-judge
    ("Zheng et al.", "2023"): "zheng2023Judging",
    ("Nguyen et al.", "2025"): "nguyen2025Reliably",

    # Generic Artificial Analysis (table rows preserve their per-model descriptor)
    ("Artificial Analysis", "2026"): "artificialanalysis2026Llama",  # generic mention; specific rows in §7.4 table keep descriptors

    # Statistical methodology (narrative form: "and" or "&")
    ("Artstein and Poesio", "2008"): "artstein2008InterCoder",
    ("Artstein & Poesio", "2008"): "artstein2008InterCoder",
    ("Northcutt et al.", "2021"): "northcutt2021Pervasive",
    ("Landis and Koch", "1977"): "landis1977Measurement",
    ("Landis & Koch", "1977"): "landis1977Measurement",
    ("McNemar", "1947"): "mcnemar1947Note",
    ("Efron", "1979"): "efron1979Bootstrap",
    ("Holm", "1979"): "holm1979Simple",
    ("Brown, Cai and DasGupta", "2001"): "brown2001Interval",
    ("Hesterberg", "2015"): "hesterberg2015What",
    ("Demšar", "2006"): "JMLR:v7:demsar06a",
    ("Demsar", "2006"): "JMLR:v7:demsar06a",
    ("Sälevä et al.", "2025"): "saleva2025Statistical",
    ("Saleva et al.", "2025"): "saleva2025Statistical",

    # ML methodology
    ("D'Amour et al.", "2022"): "damour2020Underspecification",  # bib has year=2020; JMLR 2022
    ("Guo et al.", "2017"): "guo2017Calibration",
    ("Guo et al.", "2021"): "guo2021Overview",
    ("Chidambaram et al.", "2024"): "chidambaram2024How",
    ("Oakden-Rayner et al.", "2020"): "oakden-rayner2020Hidden",
    ("Hu et al.", "2021"): "hu2021LoRA",
    ("Dettmers et al.", "2023"): "dettmers2023QLoRA",
    ("Lin et al.", "2018"): "lin2018Focal",
    ("Hassan et al.", "2026"): "hassan2026Efficient",

    # Provider references (note: artificialanalysis has per-model keys)
    ("Anthropic", "2026"): "anthropic2026Pricing",
}


def _build_patterns() -> list[tuple[re.Pattern, str, str]]:
    """Compile regex patterns for every mapping entry.

    Returns list of (pattern, replacement_when_narrative, replacement_when_parenthetical)
    """
    patterns: list[tuple[re.Pattern, str, str]] = []
    for (author, year), key in MAPPING.items():
        # Escape special regex characters in the author surface
        author_esc = re.escape(author)
        year_esc = re.escape(year)

        # Narrative pattern: "Hines et al. (2024)" or "Perez and Ribeiro (2022)"
        # Replaces with bare @key; Pandoc + citeproc renders "Hines et al. (2024)" automatically.
        narrative = re.compile(rf"{author_esc} \({year_esc}\)")
        patterns.append((narrative, f"@{key}", "narrative"))

        # Parenthetical pattern: "(Hines et al., 2024)" with optional spaces; also "and" -> "&" variants
        paren = re.compile(rf"\({author_esc},\s*{year_esc}\)")
        patterns.append((paren, f"[@{key}]", "parenthetical"))

        # Semicolon-joined parenthetical group, second author position:
        # "(Foo, 2024; Bar, 2025)" -> need to handle the "Bar, 2025" part inside the group
        # This is handled by the post-pass below, not per-key here.

    return patterns


def _apply_mappings(text: str) -> tuple[str, list[str], list[str]]:
    """Apply citation replacements. Returns (new_text, applied_changes, warnings)."""
    new_text = text
    applied: list[str] = []
    warnings: list[str] = []

    for pattern, replacement, kind in _build_patterns():
        matches = list(pattern.finditer(new_text))
        if matches:
            applied.append(f"  [{kind}] {pattern.pattern} -> {replacement} ({len(matches)} occurrences)")
            # For narrative form, keep "(year)" after the @key so APA renders as
            # "Hines et al. (2024)". For parenthetical, [@key] renders as "(Hines et al., 2024)".
            new_text = pattern.sub(replacement, new_text)

    # Flag remaining citation-like patterns that weren't matched
    unmatched_pat = re.compile(
        r"(?<![@\w])([A-Z][\w'-]+(?: et al\.| and [A-Z][\w'-]+| & [A-Z][\w'-]+| , [A-Z][\w'-]+ and [A-Z][\w'-]+)?)\s+\((\d{4})\)"
    )
    for m in unmatched_pat.finditer(new_text):
        warnings.append(f"  Unmapped narrative-style: {m.group(0)!r}")

    paren_unmatched_pat = re.compile(
        r"(?<!\[@)\(([A-Z][\w'-]+(?: et al\.| and [A-Z][\w'-]+| & [A-Z][\w'-]+| , [A-Z][\w'-]+ and [A-Z][\w'-]+)?),\s*(\d{4})\)"
    )
    for m in paren_unmatched_pat.finditer(new_text):
        warnings.append(f"  Unmapped parenthetical-style: {m.group(0)!r}")

    # Multi-citation parens like "(Foo, 2022; Bar, 2023)" need manual handling
    # because pandoc-citeproc syntax differs ([@k1; @k2] not (key1; key2)).
    multi_pat = re.compile(r"\([A-Z][\w'-]+(?:[\s&,]+[A-Za-z'\.\s-]+)*,\s*\d{4};[^)]+\d{4}[^)]*\)")
    for m in multi_pat.finditer(new_text):
        warnings.append(f"  MULTI-CITATION (manual edit needed): {m.group(0)!r}")

    # Mixed parens like "(Efron, 1979; `src/metrics.py::bootstrap_ci`)" — citation + code path
    # Pandoc-citeproc cannot resolve these as multi-cite groups; convert inner citation
    # to `@key` narrative form which renders correctly inside arbitrary parens.
    mixed_pat = re.compile(r"\(([A-Z][\w'-]+(?:[\s,&]+[A-Z][\w'.-]+)*,\s*\d{4});\s*`[^`]+`\)")
    for m in mixed_pat.finditer(new_text):
        warnings.append(f"  MIXED PARENS (citation + code): {m.group(0)!r}")

    return new_text, applied, list(set(warnings))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Write changes to the file. Without this flag, dry-run only.")
    args = parser.parse_args()

    original = TARGET.read_text(encoding="utf-8")
    new_text, applied, warnings = _apply_mappings(original)

    print(f"=== Citation migration on {TARGET.relative_to(REPO)} ===")
    print(f"Original length: {len(original):,} chars")
    print(f"New length:      {len(new_text):,} chars")
    print(f"\n=== Replacements applied ({len(applied)} rules fired) ===")
    for line in applied:
        print(line)

    if warnings:
        print(f"\n=== Unmatched citation-like patterns ({len(warnings)} unique) ===")
        print("Review these and add to MAPPING if they should be converted:")
        for w in sorted(warnings):
            print(w)

    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=str(TARGET.relative_to(REPO)) + " (current)",
        tofile=str(TARGET.relative_to(REPO)) + " (after migration)",
        n=1,
    ))

    if args.apply:
        TARGET.write_text(new_text, encoding="utf-8")
        print(f"\n=== APPLIED ({len(diff)} diff lines written to {TARGET.relative_to(REPO)}) ===")
    else:
        print(f"\n=== Diff preview (first 60 lines; pass --apply to write) ===")
        for line in diff[:60]:
            print(line.rstrip())
        if len(diff) > 60:
            print(f"... (and {len(diff) - 60} more diff lines; pass --apply to apply all)")


if __name__ == "__main__":
    main()
