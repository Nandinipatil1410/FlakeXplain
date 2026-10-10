# SunPy execution provenance

The original CANNIER SunPy commit `7c6e51e85410f3647af81e601a4bb4c9073a50c8`
failed the strict baseline in workflow run 38035734159. The heliocentric example
uses a HeliographicStonyhurst 1.1 observer, but its enclosing schema only accepts
version 1.0, which rejects the observer's `rsun` attribute.

The executable configuration now pins upstream SunPy **v3.0.3**, commit
`b071259098e9ff1dbd9e66071999f60fdf9b0fd7`. This release includes the
[upstream schema fix](https://github.com/sunpy/sunpy/commit/61da21263b834b02642fbd5e66f4d8e9c2b4a21b).
No local source, test assertion, or schema patch is applied. The strict baseline
gate and 12 original / 12 random / 1 reverse detection plan remain in place.

This is an **updated-source experiment**, not an exact replication of the
original CANNIER source revision. The original commit remains recorded in the
inventory and setup recipe. The original dependency snapshot remains unchanged;
existing explicit bootstrap tools are retained. The effective setup recipe,
source commit, environment snapshot, baseline logs, and round evidence are
packaged by the workflow.

Run `FlakeXplain CANNIER sunpy` with `mode=full`. Successful execution is not
claimed until the strict baseline and all detection rounds finish successfully.
