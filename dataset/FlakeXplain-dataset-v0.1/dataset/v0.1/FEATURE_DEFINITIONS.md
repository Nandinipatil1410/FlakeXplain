# Static feature definitions

Only the numeric columns allowlisted in schema.json are predictors. All counts are computed from source ASTs without importing subjects. No execution result is read by the feature functions.

The body tree contains the function's statements, excluding its decorators and signature. Nested function/class bodies and docstring expression nodes are included by ast.walk. `lines` is the inclusive span from the def line to the final function line, including the signature and any intervening blank/comment lines. This span is a size proxy.

| Feature suffix | Definition |
|---|---|
| lines | Inclusive function span described above |
| statements | ast.stmt nodes, including nested statements |
| calls | ast.Call nodes |
| asserts | ast.Assert statements; unittest assertion method calls are calls, not ast.Assert |
| branches | ast.If and ast.IfExp nodes |
| loops | ast.For, ast.AsyncFor, ast.While nodes |
| try_blocks | ast.Try nodes |
| raises | ast.Raise nodes |
| with_blocks | ast.With and ast.AsyncWith nodes |
| awaits | ast.Await nodes |
| yields | ast.Yield and ast.YieldFrom nodes |
| imports | ast.Import and ast.ImportFrom statements |
| globals | ast.Global and ast.Nonlocal statements |
| mutable_literals | ast.List, ast.Dict, ast.Set nodes |
| comprehensions | ListComp, SetComp, DictComp, GeneratorExp nodes |

The seven call categories count calls whose syntactic dotted name contains at least one listed exact token after lowercasing. Each call counts at most once in each category; categories can overlap. This is a lexical proxy, not semantic type inference. Unnamed/subscripted callables are not reliably identified.

| Category | Tokens |
|---|---|
| time_calls | time, sleep, datetime, monotonic, perf_counter, now, utcnow |
| random_calls | random, randint, choice, shuffle, seed, uuid4 |
| filesystem_calls | open, mkdir, unlink, remove, write_text, read_text, chdir, mkstemp |
| network_calls | socket, requests, urlopen, connect, httpx, getaddrinfo |
| mock_calls | patch, monkeypatch, mock, magicmock, setattr, setenv |
| process_calls | subprocess, popen, multiprocessing, thread, start, system |
| finalizer_calls | addfinalizer |

`body_` prefixes denote test-body measurements. `context_` prefixes sum the same 22 measurements over unique selected context functions. A selected function is counted once per context, even if multiple references reach it. The original test function is excluded from its context.

Additional context columns count unique fixture/helper/lifecycle nodes, statically autouse-decorated selected fixtures, selected fixtures by declared scope (function/class/module/package/session/other), and distinct fixture dependency edges whose parent is not the test body. Scope `other` includes dynamic/nonstandard declarations. No effective runtime execution count, runtime seed value, fixture timing, failure subtype or outcome is used.

The definitions intentionally omit parameter values, test-name tokens, project identifiers, source hashes, unresolved-count flags and bound flags from predictors. Those fields remain audit metadata. Both planned ablations use the same case join and project splits.
