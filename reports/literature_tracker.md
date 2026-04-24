# Literature Tracker

Capture file for references encountered during the project. Canonical store is Zotero; this file holds quick notes plus a scope decision (main / appendix / future / skip).

## How to use

When a paper or resource lands on your desk:

1. Add it to Zotero (via browser extension or "Add Item by Identifier" with arXiv ID or DOI).
2. Tag it in Zotero: scope tag (`capstone-main`, `capstone-appendix`, `capstone-future-work`), threat-vector tag, content-type tag.
3. Append a block to the relevant section below, following the format:

```
## YYYY-MM-DD — Short title
- Zotero key: @AuthorYearKeyword
- Threat vector: (prompt injection | text-to-sql | excessive agency | indirect injection | ...)
- Scope: (capstone-main | capstone-appendix | capstone-future-work | skip)
- Why captured: one sentence
- Use: where in the report it slots (related work, methods, appendix section, future work)
- Follow-up: yes/no (any read-in-full or verify-benchmark action)
```

Keep each entry under a minute to write. Curate and expand at write-up time.

---

## Prompt injection (direct and indirect) — main study lit review

### 2026-04-24 — BAGEL: ensemble classifier for malicious prompt detection
- Zotero key: `@hassan2026Efficient`
- Threat vector: prompt injection (defense, input classifier, ensemble)
- Scope: capstone-main (related work) + capstone-future-work
- Why captured: recent (Feb 2026) ensemble-of-classifiers approach using 86M-param fine-tuned specialists with random-forest routing. Distinct design philosophy from our single-classifier Defense A.
- Use: 1-2 sentences in related work contextualizing our single-classifier choice; 1 sentence in future work as "ensemble approaches are a natural extension."
- Follow-up: no. Not worth expanding scope to evaluate directly (would require new wrappers, contamination check, comparison columns).

---

## Text-to-SQL injection — appendix

(no entries yet)

---

## Excessive agency — appendix

(no entries yet)

---

## Additional indirect-injection vectors beyond BIPIA — appendix

(no entries yet)

---

## Future work / deferred

(no entries yet)

---

## Skipped / rejected

Entries that looked plausible but are not useful. Keeping a record prevents re-evaluation if the same paper resurfaces.

(no entries yet)
