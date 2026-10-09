# Pillow extra TIFF fixtures

The pinned Pillow commit `92933b86574b9c80764bf52c357ed29e1ef53382`
expects these images under `Tests/images`, but deliberately excludes them
from its checkout. Its `.ci/install.sh` invokes
[`depends/install_extra_test_images.sh`](https://github.com/python-pillow/Pillow/blob/92933b86574b9c80764bf52c357ed29e1ef53382/depends/install_extra_test_images.sh)
to install extra images from `python-pillow/pillow-depends`.

These three TIFF files are copied byte-for-byte from that repository at
`1c6d24bde58dda66cdc2e37ffbad50ab267ab732` (2021-06-16), predating
the pinned Pillow commit (2021-07-06). They restore the separate upstream
TIFF fixtures without changing test code or disabling CI missing-file checks.
This is a TIFF fixture supplement, not a copy of the entire optional image suite.

`remaining-configs.json` records each immutable source URL, destination, and
SHA-256 checksum. Setup verifies the bytes and preserves the fixture data and
provenance in experiment logs using the existing fixture preparation mechanism.
