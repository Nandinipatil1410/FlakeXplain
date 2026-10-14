# Development revision v0.2: feature provenance

This is a development representation revision after inspecting the original pilot.
The original v0.1 cases, labels, source contexts, exclusions and project folds are unchanged.

The historical `body` file/model identifier now means **revised core**, not strictly
test-body-only. Its 30 columns comprise the original 22 body counts, six new body
operation counts, and two scoped-read indicators. The latter consult module/class
declarations. Therefore the v2 core-versus-full comparison measures incremental
context beyond an already scope-aware core. The v1 22-versus-55 comparisons retain
the strict original test-body/context distinction.

New counts are assertion-like call names beginning with `assert`, attribute and
subscript nodes in assignment targets, mutable-operation calls, cleanup calls,
blocking calls, module-assigned names read by the function, and class-assigned
attributes read by the function. Scoped-name matches are proxies: shadowing and
runtime types are not proved. Assignment-target counts are structural AST counts,
not an exact count of changed heap objects.

The 66 added context columns comprise 17 mean-per-function measurements for each
of fixture/helper/lifecycle functions (51), their three node counts, four collected
class-initialization measurements, and eight existing fixture scope/autouse/edge
measurements. Means reduce dependence on the total amount of selected context.
Class initialization is potential static state; runtime branches and inherited or
dynamically generated state are not fully resolved.

Text baselines use AST node/name tokens. Comments, docstrings, literal values,
function/class signatures and names, import paths, source paths, test IDs and direct
flaky/xfail marker words are excluded. Variable/attribute identifiers can still
encode domain vocabulary. The training protocol restricts inputs to 512 body and
1,024 additional context tokens. Hashing is stateless; IDF and linear classifiers
are fitted within training partitions only.

No new plugin-registry expansion, same-name override resolution, dynamic parameter
binding or upstream execution was performed. Existing unresolved references and
bounds remain audit metadata and are excluded from predictors. Predictor names and
the precise source implementation are frozen in schema.json and manifest.json.
