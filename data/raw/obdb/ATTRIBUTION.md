# OpenBeerDB Attribution

This directory contains a snapshot of the [OpenBeerDB][obdb] public beer
catalog, mirrored at <https://github.com/jpargudo/pgOpenBeerDB>.

[obdb]: https://openbeerdb.com

## License

- **Database structure:** [Open Database License (ODbL)][odbl]
- **Database contents:** [Database Contents License (DbCL)][dbcl]
- Full license text: see `LICENCE.txt` in this directory.

[odbl]: https://opendatacommons.org/licenses/odbl/
[dbcl]: https://opendatacommons.org/licenses/dbcl/

## Required notice

> Contains information from OpenBeerDB (https://openbeerdb.com),
> which is made available here under the Open Database License (ODbL).

## Derivative

Files in `data/raw/obdb/` are an unmodified snapshot. The downstream
file `data/raw/curated_beers.csv` is a derivative produced by
`scripts/build_catalog.py` (joining, cleaning, style-normalizing, and
sampling). As a derivative it is shared under the same ODbL/DbCL terms.

## Snapshot

- Source repo: `jpargudo/pgOpenBeerDB`
- Pinned commit: `ef7e103861f2299e65fbcfab074a891d85333d65`
- Fetched: 2026-05-22
