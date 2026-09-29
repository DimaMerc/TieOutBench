"""harness/env/state.py — one episode of the eval-6 agent environment.

The Episode holds the document store (the case's `documents`, unchanged), the clock (the case's
`episode.as_of`), the ledger (empty at the start; appended only through the action tools), and the
transcript (every message, tool call and tool result, in order, with UTC timestamps). Every tool is
a pure function of the case file plus the ledger. Signatures and returns are fixed so the transcript
is machine-checkable; errors come back as `{"error": ...}` and are recorded, never raised at the
model.

The `env` block of the case file (authored from the case's own position document and checked
against it in the selftest) supplies the account, the ticker, the settled-position history, whether
anything is pending after the clock, the PCF line for the split family, and `actions_allowed` (gold,
not a prompt hint: every case exposes every tool).
"""
from __future__ import annotations
import copy
import datetime as _dt
import json
import os

from ..rubric import load_case
from ..suites.corporate_actions import _to_iso, _numx
from .calc import calculate, fmt, CalcError

_round = round   # tool methods take a `round` (round-number) argument; keep the builtin reachable

READ_TOOLS = ("list_documents", "read_document", "get_position", "calculate")
ACTION_TOOLS = ("book_receivable", "update_pcf", "confirm_position", "submit_election", "escalate")
MAKER_TOOLS = READ_TOOLS + ACTION_TOOLS + ("submit_worksheet",)
REVIEWER_TOOLS = READ_TOOLS + ("review_verdict",)


def _utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _is_none(v) -> bool:
    return v is None or str(v).strip().lower() in ("", "none", "null", "no")


def _num_arg(v):
    """numeric tool argument: a number or a display string ('6,800.00', '$6,800'); None on failure."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        return _numx(v)
    return None


# ---------------- tool specifications (OpenAI function-calling format) ----------------
def _spec(name, description, props, required):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": props, "required": required}}}


_DOC_ID = {"type": "string", "description": "a doc_id exactly as list_documents returns it"}
_ACCOUNT = {"type": "string", "description": "the account identifier from the task"}

TOOL_SPECS = {
    "list_documents": _spec(
        "list_documents",
        "List every document in the store for this episode: doc_id, type, title, date. No bodies. Some "
        "documents are distractors and one may supersede another; deciding which document governs is "
        "part of the task.", {}, []),
    "read_document": _spec(
        "read_document", "Return one document's full body by doc_id.",
        {"doc_id": _DOC_ID}, ["doc_id"]),
    "get_position": _spec(
        "get_position",
        "The account's settled position in the event's security as of a date (YYYY-MM-DD). Answered "
        "from the position history on or before that date; a date after the desk's as-of date is "
        "answered as a projection only when no position changes are pending or scheduled.",
        {"account": _ACCOUNT, "as_of": {"type": "string", "description": "YYYY-MM-DD"}},
        ["account", "as_of"]),
    "calculate": _spec(
        "calculate",
        "Evaluate an arithmetic expression exactly: numbers, + - * / and parentheses only. No names, "
        "no percent signs, no currency symbols. Returns the unrounded result.",
        {"expression": {"type": "string"}}, ["expression"]),
    "book_receivable": _spec(
        "book_receivable",
        "Book a cash receivable for the account (a dividend or tender proceeds). Appends a ledger entry. "
        "The amount and pay_date fields are what gets booked; the memo is commentary.",
        {"account": _ACCOUNT,
         "amount": {"type": "number", "description": "cash amount in the security's currency"},
         "pay_date": {"type": "string", "description": "YYYY-MM-DD the cash is expected"},
         "basis_doc": {"type": "string", "description": "doc_id of the document whose terms this booking rests on"},
         "shares": {"type": "number", "description": "the share quantity the amount is computed on"},
         "rate": {"type": "number", "description": "per-share rate or price applied"},
         "memo": {"type": "string"}},
        ["account", "amount", "pay_date", "basis_doc"]),
    "update_pcf": _spec(
        "update_pcf",
        "Set the security's quantity per creation unit on the ETF's portfolio composition file for "
        "today's dissemination. Appends a ledger entry.",
        {"ticker": {"type": "string"},
         "quantity_per_cu": {"type": "number"},
         "basis_doc": {"type": "string", "description": "doc_id the adjustment rests on"},
         "memo": {"type": "string"}},
        ["ticker", "quantity_per_cu", "basis_doc"]),
    "confirm_position": _spec(
        "confirm_position",
        "Record a confirmation of the security's share position as of a date (a verification entry, "
        "not a release of cash). Appends a ledger entry.",
        {"ticker": {"type": "string"}, "shares": {"type": "number"},
         "as_of": {"type": "string", "description": "YYYY-MM-DD"},
         "basis_doc": {"type": "string"}},
        ["ticker", "shares", "as_of", "basis_doc"]),
    "submit_election": _spec(
        "submit_election",
        "Submit an election instruction for the account (tender shares, choose an option). Appends a "
        "ledger entry. The tool always accepts the instruction; whether an election exists, and whether "
        "it is timely, is judged afterwards.",
        {"account": _ACCOUNT, "option": {"type": "string"}, "shares": {"type": "number"},
         "basis_doc": {"type": "string"}, "memo": {"type": "string"}},
        ["account", "option", "shares", "basis_doc"]),
    "escalate": _spec(
        "escalate",
        "Escalate to the desk supervisor and hold a named action. Use it when a document the "
        "governing announcement refers to is not in the store and a figure depends on it: name the "
        "missing document and hold only the dependent action.",
        {"reason": {"type": "string"},
         "missing_document": {"type": "string", "description": "the document that is absent from the store"},
         "held_action": {"type": "string", "description": "the one action being held"}},
        ["reason", "missing_document", "held_action"]),
    "submit_worksheet": _spec(
        "submit_worksheet",
        "Submit the completed desk worksheet (the JSON object in exactly the schema given in the "
        "task) and end the episode. Book through the action tools BEFORE submitting: only ledger "
        "entries count as actions taken.",
        {"worksheet": {"type": "object", "description": "the worksheet JSON object"}},
        ["worksheet"]),
    "review_verdict": _spec(
        "review_verdict",
        "Deliver the review verdict on the maker's work product and end the review.",
        {"verdict": {"type": "string", "enum": ["approve", "reject"]},
         "findings": {"type": "array", "items": {"type": "string"},
                      "description": "one finding per item: what is wrong, which entry, what it should be"}},
        ["verdict", "findings"]),
}


def specs_for(names) -> list:
    return [TOOL_SPECS[n] for n in names]


class Episode:
    """One case, one run of the environment (maker and, in the checker arm, reviewer share it)."""

    def __init__(self, case_path: str, *, arm: str = "tools", model_id: str | None = None):
        self.case_path = case_path
        self.case = load_case(case_path)
        if self.case.get("suite") != "corporate-actions":
            raise ValueError("the agent environment runs corporate-actions cases only")
        self.env = self.case.get("env") or {}
        if not self.env:
            raise ValueError(f"{self.case.get('case_id')}: the case has no env block")
        self.arm = arm
        self.model_id = model_id
        ep = self.case.get("episode") or {}
        self.clock = _to_iso(ep.get("as_of"))
        self.docs = {str(d.get("doc_id")): d for d in (self.case.get("documents") or []) if isinstance(d, dict)}
        self.positions = sorted(
            [{"as_of": _to_iso(r.get("as_of")), "settled_shares": float(r.get("settled_shares")),
              "tendered_shares": (float(r["tendered_shares"]) if r.get("tendered_shares") is not None else None),
              "note": str(r.get("note") or "")}
             for r in (self.env.get("positions") or [])], key=lambda r: r["as_of"])
        pac = self.env.get("pending_after_clock")
        self.pending_after_clock = None if _is_none(pac) else str(pac)
        self.pcf = dict(self.env.get("pcf") or {})
        self.ledger: list[dict] = []            # every entry ever booked (voided ones carry voided=True)
        self.frozen: dict[str, list] = {}       # named snapshots (ledger_v1 in the checker arm)
        self.frozen_worksheets: dict[str, dict] = {}   # the worksheet at each snapshot (what the reviewer saw)
        self.transcript: list[dict] = []
        self.seq = 0
        self.worksheet: dict | None = None
        self.submitted = False
        self.reviews: list[dict] = []           # one record per review round
        self.current_review: dict | None = None
        self.started_at = _utc()

    # ---------------- transcript ----------------
    def record(self, kind: str, *, agent: str = "maker", round: int = 1, **payload) -> dict:
        self.seq += 1
        e = {"seq": self.seq, "t": _utc(), "agent": agent, "round": round, "kind": kind}
        e.update(payload)
        self.transcript.append(e)
        return e

    # ---------------- the ledger ----------------
    def _append(self, kind: str, args: dict, *, agent: str, round: int) -> dict:
        entry = {"entry_id": f"L{len(self.ledger) + 1}", "kind": kind, "args": args, "seq": self.seq,
                 "agent": agent, "round": round, "voided": False, "t": _utc()}
        self.ledger.append(entry)
        return entry

    def active_ledger(self) -> list[dict]:
        return [e for e in self.ledger if not e.get("voided")]

    def freeze(self, name: str):
        self.frozen[name] = copy.deepcopy(self.active_ledger())
        self.frozen_worksheets[name] = copy.deepcopy(self.worksheet or {})

    def void_ledger(self, *, agent: str = "reviewer", round: int = 1):
        for e in self.ledger:
            if not e.get("voided"):
                e["voided"] = True
                e["voided_round"] = round
        self.record("note", agent=agent, round=round,
                    text="ledger entries voided after a reject; the maker may act again")

    # ---------------- tools ----------------
    def call(self, name: str, args: dict | None, *, agent: str = "maker", round: int = 1,
             call_id: str | None = None) -> dict:
        """dispatch one tool call; records the call and its result; returns the result dict."""
        args = dict(args or {}) if isinstance(args, dict) else {"_raw": args}
        allowed = REVIEWER_TOOLS if agent == "reviewer" else MAKER_TOOLS
        self.record("tool_call", agent=agent, round=round, name=name, arguments=args, call_id=call_id)
        if name not in TOOL_SPECS:
            res = {"error": f"unknown tool: {name}"}
        elif name not in allowed:
            res = {"error": f"{name} is not available to the {agent}"}
        else:
            try:
                res = getattr(self, "t_" + name)(args, agent=agent, round=round)
            except Exception as e:                       # a tool must never crash the episode
                res = {"error": f"{type(e).__name__}: {e}"}
        self.record("tool_result", agent=agent, round=round, name=name, call_id=call_id,
                    ok="error" not in res, result=res)
        return res

    def t_list_documents(self, args, **kw):
        return {"documents": [{"doc_id": d.get("doc_id"), "type": d.get("type"), "title": d.get("title"),
                               "date": _to_iso(d.get("date")) or str(d.get("date"))}
                              for d in self.docs.values()]}

    def t_read_document(self, args, **kw):
        did = str(args.get("doc_id") or "").strip()
        d = self.docs.get(did)
        if d is None:
            return {"error": f"unknown doc_id: {did!r}; call list_documents for the ids"}
        return {"doc_id": did, "type": d.get("type"), "title": d.get("title"),
                "date": _to_iso(d.get("date")) or str(d.get("date")), "body": str(d.get("body") or "").rstrip()}

    def _account_ok(self, v) -> bool:
        a = str(v or "").strip().upper().replace(" ", "")
        return bool(a) and a == str(self.env.get("account") or "").upper().replace(" ", "")

    def _ticker_ok(self, v) -> bool:
        return str(v or "").strip().upper() == str(self.env.get("ticker") or "").upper()

    def t_get_position(self, args, **kw):
        if not self._account_ok(args.get("account")):
            return {"error": f"unknown account {args.get('account')!r}; this desk services {self.env.get('account')}"}
        iso = _to_iso(args.get("as_of"))
        if not iso:
            return {"error": f"as_of must be a date (YYYY-MM-DD), got {args.get('as_of')!r}"}
        if not self.positions:
            return {"error": "no position history"}
        first = self.positions[0]["as_of"]
        if iso < first:
            return {"error": f"no position history before {first}"}
        basis, note = "settled", ""
        if iso > self.clock:
            if self.pending_after_clock:
                return {"error": f"{iso} is after the desk's as-of date {self.clock}; the position is not "
                                 f"determinable: {self.pending_after_clock}"}
            basis = "projected"
            note = (f"projected from the latest settled position as of {self.clock}: no open orders, no pending "
                    f"trades and no position changes scheduled after that date")
        row = max((r for r in self.positions if r["as_of"] <= min(iso, self.clock)), key=lambda r: r["as_of"])
        out = {"account": self.env.get("account"), "ticker": self.env.get("ticker"), "as_of": iso,
               "settled_shares": row["settled_shares"], "basis": basis,
               "position_row_as_of": row["as_of"],
               "note": (row["note"] + ("; " + note if note else "")).strip("; ")}
        if row.get("tendered_shares") is not None:
            out["tendered_shares"] = row["tendered_shares"]
        return out

    def t_calculate(self, args, **kw):
        expr = args.get("expression")
        try:
            val = calculate(expr)
        except CalcError as e:
            return {"error": str(e), "expression": expr}
        return {"expression": expr, "result": val, "result_text": fmt(val)}

    def _basis_ok(self, v):
        did = str(v or "").strip()
        if did in self.docs:
            return did, None
        return None, {"error": f"basis_doc must be a doc_id from the store, got {v!r}"}

    def t_book_receivable(self, args, *, agent, round):
        if not self._account_ok(args.get("account")):
            return {"error": f"unknown account {args.get('account')!r}; this desk services {self.env.get('account')}"}
        amount = _num_arg(args.get("amount"))
        if amount is None:
            return {"error": "amount is required and must be a number"}
        pay = _to_iso(args.get("pay_date"))
        if not pay:
            return {"error": f"pay_date must be a date (YYYY-MM-DD), got {args.get('pay_date')!r}"}
        basis, err = self._basis_ok(args.get("basis_doc"))
        if err:
            return err
        shares = _num_arg(args.get("shares")) if args.get("shares") is not None else None
        rate = _num_arg(args.get("rate")) if args.get("rate") is not None else None
        norm = {"account": self.env.get("account"), "amount": _round(amount, 2), "pay_date": pay,
                "basis_doc": basis, "shares": shares, "rate": rate, "memo": str(args.get("memo") or "")}
        e = self._append("book_receivable", norm, agent=agent, round=round)
        return {"entry_id": e["entry_id"], "booked": norm}

    def t_update_pcf(self, args, *, agent, round):
        if not self._ticker_ok(args.get("ticker")):
            return {"error": f"{args.get('ticker')!r} is not the security of this episode ({self.env.get('ticker')})"}
        if not self.pcf:
            return {"error": "this episode has no portfolio composition file; update_pcf does not apply"}
        q = _num_arg(args.get("quantity_per_cu"))
        if q is None:
            return {"error": "quantity_per_cu is required and must be a number"}
        basis, err = self._basis_ok(args.get("basis_doc"))
        if err:
            return err
        norm = {"ticker": self.env.get("ticker"), "quantity_per_cu": q,
                "previous_quantity_per_cu": self.pcf.get("quantity_per_cu"),
                "basis_doc": basis, "memo": str(args.get("memo") or "")}
        e = self._append("update_pcf", norm, agent=agent, round=round)
        return {"entry_id": e["entry_id"], "pcf_line": {"ticker": norm["ticker"], "quantity_per_cu": q,
                                                         "creation_units": self.pcf.get("creation_units")}}

    def t_confirm_position(self, args, *, agent, round):
        if not self._ticker_ok(args.get("ticker")):
            return {"error": f"{args.get('ticker')!r} is not the security of this episode ({self.env.get('ticker')})"}
        sh = _num_arg(args.get("shares"))
        if sh is None:
            return {"error": "shares is required and must be a number"}
        iso = _to_iso(args.get("as_of"))
        if not iso:
            return {"error": f"as_of must be a date (YYYY-MM-DD), got {args.get('as_of')!r}"}
        basis, err = self._basis_ok(args.get("basis_doc"))
        if err:
            return err
        norm = {"ticker": self.env.get("ticker"), "shares": sh, "as_of": iso, "basis_doc": basis}
        e = self._append("confirm_position", norm, agent=agent, round=round)
        return {"entry_id": e["entry_id"], "confirmed": norm}

    def t_submit_election(self, args, *, agent, round):
        if not self._account_ok(args.get("account")):
            return {"error": f"unknown account {args.get('account')!r}; this desk services {self.env.get('account')}"}
        sh = _num_arg(args.get("shares"))
        if sh is None:
            return {"error": "shares is required and must be a number"}
        basis, err = self._basis_ok(args.get("basis_doc"))
        if err:
            return err
        norm = {"account": self.env.get("account"), "option": str(args.get("option") or ""), "shares": sh,
                "basis_doc": basis, "memo": str(args.get("memo") or ""), "instructed_on": self.clock}
        e = self._append("submit_election", norm, agent=agent, round=round)
        return {"entry_id": e["entry_id"], "accepted": True, "instructed_on": self.clock,
                "note": "the instruction is recorded; whether an election exists and is timely is judged afterwards"}

    def t_escalate(self, args, *, agent, round):
        norm = {"reason": str(args.get("reason") or ""), "missing_document": str(args.get("missing_document") or ""),
                "held_action": str(args.get("held_action") or "")}
        if not norm["held_action"]:
            return {"error": "held_action is required: name the one action being held"}
        e = self._append("escalate", norm, agent=agent, round=round)
        return {"entry_id": e["entry_id"], "escalated": norm}

    def t_submit_worksheet(self, args, *, agent, round):
        ws = args.get("worksheet")
        if isinstance(ws, str):
            from ..live import parse_answer
            try:
                ws = parse_answer(ws)
            except Exception:
                return {"error": "worksheet must be a JSON object"}
        if not isinstance(ws, dict) or not ws:
            return {"error": "worksheet must be a non-empty JSON object in the schema given in the task"}
        self.worksheet = {k: v for k, v in ws.items() if not str(k).startswith("_")}
        self.submitted = True
        self.record("episode_end", agent=agent, round=round, reason="submit_worksheet")
        return {"status": "submitted", "episode": "ended", "ledger_entries": len(self.active_ledger())}

    def t_review_verdict(self, args, *, agent, round):
        v = str(args.get("verdict") or "").strip().lower()
        if v not in ("approve", "reject"):
            return {"error": "verdict must be 'approve' or 'reject'"}
        f = args.get("findings")
        if isinstance(f, str):
            f = [f] if f.strip() else []
        if not isinstance(f, list):
            f = []
        findings = [json.dumps(x, sort_keys=True) if isinstance(x, (dict, list)) else str(x) for x in f]
        self.current_review = {"round": round, "verdict": v, "findings": findings}
        self.record("review_end", agent=agent, round=round, verdict=v, findings=findings)
        return {"status": "recorded", "verdict": v, "findings": len(findings)}

    # ---------------- persistence ----------------
    def to_dict(self) -> dict:
        return {"case_id": self.case.get("case_id"), "case_path": self.case_path, "arm": self.arm,
                "model_id": self.model_id, "clock": self.clock, "started_at": self.started_at,
                "submitted": self.submitted, "worksheet": self.worksheet, "ledger": self.ledger,
                "frozen": self.frozen, "reviews": self.reviews, "transcript": self.transcript}

    def save(self, outdir: str):
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "transcript.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
            for e in self.transcript:
                fh.write(json.dumps(e, default=str, ensure_ascii=False) + "\n")
        with open(os.path.join(outdir, "ledger.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"clock": self.clock, "entries": self.ledger, "frozen": self.frozen,
                       "frozen_worksheets": self.frozen_worksheets}, fh, indent=2, default=str)
        with open(os.path.join(outdir, "answer.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(self.worksheet if self.worksheet is not None else {}, fh, indent=2, default=str)
        if self.reviews:
            with open(os.path.join(outdir, "review.json"), "w", encoding="utf-8", newline="\n") as fh:
                json.dump({"rounds": self.reviews, "ledger_v1": self.frozen.get("ledger_v1", [])},
                          fh, indent=2, default=str)

    @classmethod
    def load(cls, outdir: str, case_path: str | None = None) -> "Episode":
        """rebuild an Episode from a saved directory (used by the checker arm to reuse the tools
        arm's maker, and by the storyboard)."""
        with open(os.path.join(outdir, "ledger.json"), encoding="utf-8") as fh:
            led = json.load(fh)
        tr = []
        with open(os.path.join(outdir, "transcript.jsonl"), encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    tr.append(json.loads(line))
        rp = os.path.join(outdir, "run.json")
        meta = {}
        if os.path.exists(rp):
            with open(rp, encoding="utf-8") as fh:
                meta = json.load(fh)
        if case_path is None:
            from .. import REPO
            case_id = (meta.get("case") or {}).get("case_id") or os.path.basename(os.path.normpath(outdir))
            case_path = os.path.join(REPO, "cases", case_id + ".case.yaml")
        ep = cls(case_path, arm=meta.get("arm") or "tools", model_id=meta.get("model_id"))
        ep.ledger = led.get("entries") or []
        ep.frozen = led.get("frozen") or {}
        ep.frozen_worksheets = led.get("frozen_worksheets") or {}
        ep.transcript = tr
        ep.seq = max([e.get("seq", 0) for e in tr] + [0])
        with open(os.path.join(outdir, "answer.json"), encoding="utf-8") as fh:
            ws = json.load(fh)
        ep.worksheet = ws or None
        ep.submitted = bool(ws)
        rv = os.path.join(outdir, "review.json")
        if os.path.exists(rv):
            with open(rv, encoding="utf-8") as fh:
                ep.reviews = json.load(fh).get("rounds") or []
        return ep
