# wheelpair-diff

Compare what two wheels of the same package **actually do at runtime**, call by call — no pip, no venv, no network.

Why now: `package.version.parse("not-a-version")` returns a `LegacyVersion` object in packaging 20.9 and **raises `InvalidVersion`** in 24.2. Changelogs mention such removals, but nothing tells you which of your calls changed shape until production breaks.

Upstream: https://github.com/pypa/packaging

## What the upstream lacks

`pypa/packaging` documents removals after the fact, in the changelog:

- `CHANGELOG.rst` — "Remove `LegacySpecifier` and `LegacyVersion` (:issue:`407`)" —
  https://github.com/pypa/packaging/blob/main/CHANGELOG.rst#L496

That entry is prose. It does not say which call sites are affected, nor what the new outcome is
(return type, raised exception, message). Neither the changelog, the tests, nor the wheels ship a
call-level behaviour diff, so downstreams only find out by breaking.

Measured with this tool on the two published wheels (real run, see `examples/out/`):

```
A: packaging-20.9  (20.9, 57 symbols, 22 calls)
B: packaging-24.2  (24.2, 84 symbols, 43 calls)
drift: 51  (symbol_added=35, symbol_removed=8, error_message=4, outcome_kind=3, return_value=1)

[error/outcome_kind] packaging.version.parse(*["not-a-version"])
  A: {"kind":"ok","type":"LegacyVersion","value":"not-a-version"}
  B: {"kind":"error","type":"InvalidVersion","value":"Invalid version: 'not-a-version'"}

[error/outcome_kind] packaging.specifiers.SpecifierSet.filter(*["abc", null])
  A: {"kind":"ok","type":"list","value":"[]"}
  B: {"kind":"error","type":"InvalidVersion","value":"Invalid version: 'a'"}
```

## What it does / does not do

Does: unzip each wheel into a temp dir, import it in its **own fresh interpreter**, enumerate the
symbols the module itself defines (plus `__all__`), synthesise deterministic calls from the
signatures, record `(ok/error, type, normalised repr)` per call, and diff the two outcome sets.
Every drift carries a one-line `minimal_repro`.

Does not: install anything, resolve dependencies, judge whether a change is *good*, or compare
packages with different import names. Calls are generated from names/types, not from your code —
pass `--max-calls` to bound the probe.

## Install / usage

Requirements: Python 3.9+, standard library only. Nothing to install.

```bash
git clone <this repo> && cd wheelpair-diff
chmod +x bin/wheelpair-diff

# 1) diff two local wheels (exit 1 = drift found)
python3 bin/wheelpair-diff diff examples/in/demo_lib-1.0.0-py3-none-any.whl \
                                 examples/in/demo_lib-2.0.0-py3-none-any.whl

# 2) machine-readable
python3 bin/wheelpair-diff diff a.whl b.whl --json > report.json

# 3) inspect one wheel
python3 bin/wheelpair-diff probe a.whl --json
```

Fetching wheels is intentionally **not** part of the tool: use whatever you already use
(`pip download --no-deps pkg==ver -d dir/`) and point the CLI at the two files. The core is offline.

### Exit codes

| code | meaning |
| --- | --- |
| 0 | no drift between the two wheels |
| 1 | drift found (at least one entry in `drifts`) |
| 2 | usage error, missing file, or unreadable wheel |

### `--json` shape

```json
{"tool":"wheelpair-diff","tool_version":"1.0.0",
 "a":{"wheel":"...","version":"20.9","symbols":[...]},
 "b":{"wheel":"...","version":"24.2","symbols":[...]},
 "summary":{"symbols_a":57,"symbols_b":84,"calls_a":22,"calls_b":43,"drifts":51,
            "by_kind":{"symbol_removed":8,"symbol_added":35},
            "by_severity":{"error":11,"warning":40}},
 "drifts":[{"symbol":"packaging.version.parse","kind":"outcome_kind","severity":"error",
            "call":"packaging.version.parse(*[\"not-a-version\"])",
            "a":{"kind":"ok","type":"LegacyVersion","value":"not-a-version"},
            "b":{"kind":"error","type":"InvalidVersion","value":"Invalid version: ..."},
            "minimal_repro":"python3 -c \"import packaging.version as m; m.parse(*[...])\""}]}
```

Drift kinds: `symbol_removed`, `symbol_added`, `outcome_kind` (ok↔error), `return_type`,
`return_value`, `exception_type`, `error_message`.

## 本轮创新

First call-level runtime differ over **uninstalled wheels**: both versions are imported in separate
fresh interpreters from unzipped wheel files, so no venv, no pip, no network, and no import
collision. Existing tooling compares declared surfaces (schemas, signatures, changelogs); this
reports what the same call returns or raises before and after, with a minimal repro. The packaging
20.9→24.2 run is the first concrete proof: `version.parse` flips from returning a `LegacyVersion`
object to raising `InvalidVersion`, which no offline declaration diff shows.

## Limitations

- Generated calls are heuristic (parameter name + annotation); exotic APIs are under-sampled.
  22 vs 43 calls on the packaging pair is what the generator reached, not the whole surface.
- Symbols this package *re-exports* from other modules are skipped unless listed in `__all__`;
  symbols without a leading underscore but purely internal (e.g. `packaging.markers.Node` in 20.9)
  are still reported, because a downstream `from packaging.markers import Node` really does break.
- Object reprs that embed a decimal memory address are not normalised yet (hex addresses are).
- Only the installed-import path is exercised; C extensions that need build-time config may fail to
  import and are then reported as `import-error`.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

14 cases: exit codes 0/1/2, JSON parseability, symbol removal, outcome-kind drift, minimal repros,
metadata versions, determinism, probe subcommand.

MIT © 2026 linmoxi33
