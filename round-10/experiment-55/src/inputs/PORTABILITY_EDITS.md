# Portability edits to copied inputs

`inputs/e46/src/tpg.py` is iteration 9's `src/tpg.py` (artifact art_VVA3P0ocZNA2) with one change. Its five unused
default paths (E44, EXP9, EXP2, EXP8, DSET) pointed at absolute locations on the original server. They now point at
sibling folders named by artifact id, so no published file carries a server path. Everything else is byte-identical.

- original sha256: 4b3f883b92e2af03a3980d12aa11ae06d7e068aff91ccf5a8035ffde7bb0d427
- edited sha256: fafab9a7fbf1dfff388318d606184e9095de52057a30763235d01b615eb498d5 (listed in `inputs/SHA256SUMS`)

The same edit is in `src/tpg.py`. None of these five constants is used by the iteration-10 pipeline.
