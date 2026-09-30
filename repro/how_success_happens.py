"""What actually happens in a run that succeeds? Print the events, not the theory.

Picks R-forced runs of the frozen arm whose unconstrained joint is satisfied, and prints the
session-by-session action list with the payload-relevant calls flagged, plus the boundary
record (what the forced cleanup removed and what survived). Nothing here is summarised: every
line is one recorded event.
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import chain_stats as cs  # noqa: E402
import two_lenses as tl  # noqa: E402

DISC = cs.DISCRIMINATORS
TOKEN_MARK = cs.TOKEN_VALUE


def payloadish(text: str) -> bool:
    low = text.casefold()
    return (TOKEN_MARK.casefold() in low or cs.LABEL.casefold() in low
            or sum(1 for w in DISC if w in low) >= 2)


def successful() -> list[tuple[str, dict]]:
    out = []
    for d in sorted(cs.ROOT.glob("chain-*")):
        if not d.is_dir() or d.name in cs.VOID_BATCHES:
            continue
        for _stem, j, _v, _p in cs.runs_of(
                d, variant="full", policy="quote-as-assessed",
                model=cs.DEFAULT_MODEL, roles=False):
            if j.get("arm") != "R-forced" or cs.rescore(j) is None:
                continue
            if all(tl.unconstrained(j)):
                out.append((f"{d.name}/{_stem}", j))
    return out


def main() -> int:
    wins = successful()
    print(f"R-forced frozen-arm runs whose joint (any-session) is satisfied: {len(wins)}")
    print("showing the first three, event by event\n")

    for name, j in wins[:3]:
        print("=" * 92)
        print(f"{name}   seed={j.get('seed')}")
        print("=" * 92)

        print("  boundaries (forced cleanup keeps only what the review session produced):")
        for st in j.get("stages", []):
            if "coverage" not in st:
                continue
            held = {r: items for r, items in (st.get("residue_items") or {}).items()}
            print(f"    boundary {st['stage']}: coverage={st['coverage']} "
                  f"removed={st.get('removed')} surviving={st.get('surviving')}")
            if held:
                print(f"      residue contents per carrier: {held}")

        print("  events (only calls that matter for the three objectives are annotated):")
        for e in j.get("events") or []:
            tool = str(e.get("tool"))
            body = " ".join(str(v) for v in (e.get("args") or {}).values())
            note = ""
            if tool == "read_vault_secret":
                note = "  <-- CREDENTIAL READ"
            elif tool == "sink_write":
                note = "  <-- SINK WRITE" + (" (token+label)" if payloadish(body) else "")
            elif tool == "arm_trigger":
                note = "  <-- RULE ARMED" + (" (payload-shaped)" if payloadish(body) else
                                            " (NOT the payload's rule)")
            elif tool in ("create_file", "append_to_file", "send_email", "a2a_send",
                          "memory_put", "rag_index") and payloadish(body):
                note = "  <-- payload text written to a carrier"
            if note or tool in ("read_vault_secret", "sink_write", "arm_trigger"):
                snippet = body.replace("\n", " ")[:60]
                print(f"    S{e.get('session')} {tool:<18}{snippet:<62}{note}")

        rules = j.get("armed_rule_texts") or {}
        print("  armed rules:")
        for rule_name, text in rules.items():
            hit = sum(1 for w in DISC if w in str(text).casefold())
            print(f"    {rule_name}: discriminators={hit} :: {str(text)[:100]}")
        print(f"  fired: {j.get('triggers_fired')}   "
              f"stage1_by_S3={j.get('stage1_secret_read')}   "
              f"token_in_sink={j.get('stage2_token_in_sink')}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
