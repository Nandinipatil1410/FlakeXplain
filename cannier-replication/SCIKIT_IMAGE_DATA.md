# Historical scikit-image datasets

The pinned scikit-image revision `8fbbb5169b8da6fb26b107a0a8c6de46a93f37cc`
registers exact SHA-256 checksums but downloads external datasets from mutable
GitLab `master` URLs. The current `eagle.png` does not match its expected hash.

Setup now supplies every registered file locally before the baseline gate:

- Existing checkout files must match the upstream registry.
- External GitLab files come from immutable revision
  `f7d93a21a2642aa9ea3b6e40d3c2638fc2e40cf1`, using the file API.
- Other missing files come from the pinned scikit-image commit.
- Every download is verified against the original registry before publication.
  Failed downloads are retried; incorrect bytes stop setup.
- Verified files are reused without network access and rechecked on setup reuse.

Files live under the checkout's `skimage/` directory, where the unmodified
upstream `_fetch` function already looks before attempting network downloads.
Tests, registry hashes, and data-fetching source code remain unchanged.
`logs/dataset_provenance.json` records the registry checksum, source revisions,
and each dataset path, SHA-256, and URL, and is included in evidence packaging.
The configured dataset revision also participates in the environment fingerprint.

This removes mutable dataset downloads from baseline and detection execution.
Initial setup still needs access to the pinned upstream files. A new workflow
run supplies a fresh execution directory; existing detection evidence must be
preserved rather than reused with a changed setup recipe.
