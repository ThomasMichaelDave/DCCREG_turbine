"""The correction log: validate it, find an entry, add one, or bump a known one's count.

    python3 .claude/corrections.py validate             # every line against corrections.schema.json
    python3 .claude/corrections.py find <word> ...      # entries whose text holds every word
    python3 .claude/corrections.py add '<json>'         # domain, wrong, rule, source, tag, origin
    python3 .claude/corrections.py bump <id>            # a known correction seen again: count + 1

The validator reads its rules from corrections.schema.json (the subset of JSON Schema that file uses), so the
schema stays the one definition; it needs nothing outside the standard library.
"""
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "corrections.jsonl"
SCHEMA = json.loads((HERE / "corrections.schema.json").read_text(encoding="utf-8"))
TYPES = {"object": dict, "string": str, "integer": int}


def _check(value, schema, where):
    errs = []
    t = schema.get("type")
    if t and not (isinstance(value, TYPES[t]) and not (t == "integer" and isinstance(value, bool))):
        return [f"{where}: not {t}"]
    if "const" in schema and value != schema["const"]:
        errs.append(f"{where}: not {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{where}: {value!r} not in {schema['enum']}")
    if "pattern" in schema and not re.search(schema["pattern"], value):
        errs.append(f"{where}: {value!r} does not match {schema['pattern']}")
    if "minLength" in schema and len(value) < schema["minLength"]:
        errs.append(f"{where}: shorter than {schema['minLength']}")
    if "maxLength" in schema and len(value) > schema["maxLength"]:
        errs.append(f"{where}: longer than {schema['maxLength']}")
    if "minimum" in schema and value < schema["minimum"]:
        errs.append(f"{where}: below {schema['minimum']}")
    if "maximum" in schema and value > schema["maximum"]:
        errs.append(f"{where}: above {schema['maximum']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        errs += [f"{where}: missing {k}" for k in schema.get("required", []) if k not in value]
        if schema.get("additionalProperties") is False:
            errs += [f"{where}: unknown field {k}" for k in value if k not in props]
        errs += [e for k, s in props.items() if k in value for e in _check(value[k], s, f"{where}.{k}")]
        if "if" in schema:
            branch = "then" if not _check(value, schema["if"], where) else "else"
            if branch in schema:
                errs += _check(value, schema[branch], where)
    return errs


def load():
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate():
    errs, ids = [], set()
    for n, line in enumerate(LOG.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            errs.append(f"line {n}: not JSON ({e})")
            continue
        errs += _check(entry, SCHEMA, f"line {n}")
        if entry.get("id") in ids:
            errs.append(f"line {n}: duplicate id {entry['id']}")
        ids.add(entry.get("id"))
    return errs


def save(entries):
    LOG.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8",
                   newline="\n")


def main(argv):
    cmd, args = (argv[0], argv[1:]) if argv else ("validate", [])
    if cmd == "validate":
        errs = validate()
        print("\n".join(errs) or f"{len(load())} entries, 0 schema errors")
        return 1 if errs else 0
    entries = load()
    if cmd == "find":
        words = [w.lower() for w in args]
        for e in entries:
            text = " ".join(str(e[k]) for k in ("domain", "wrong", "rule", "source")).lower()
            if all(w in text for w in words):
                print(json.dumps(e, ensure_ascii=False))
        return 0
    if cmd == "bump":
        hit = [e for e in entries if e["id"] == args[0]]
        if not hit:
            print(f"no entry {args[0]}")
            return 1
        hit[0]["count"] += 1
        save(entries)
        print(json.dumps(hit[0], ensure_ascii=False))
        return 0
    if cmd == "add":
        new = json.loads(args[0])
        last = max((int(e["id"][2:]) for e in entries), default=0)
        entry = {"id": f"C-{last + 1:03d}", "date": datetime.date.today().isoformat(), **new}
        for k, v in (("count", 1), ("rung", 0), ("enforced_by", ""), ("fixture", "")):
            entry.setdefault(k, v)
        entry = {k: entry[k] for k in SCHEMA["required"] if k in entry} | entry
        errs = _check(entry, SCHEMA, "new entry")
        if errs:
            print("\n".join(errs))
            return 1
        save(entries + [entry])
        print(json.dumps(entry, ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
