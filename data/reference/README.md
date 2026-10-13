# Reference data

Small, openly licensed files committed to the repo (unlike SIPRI data, which is downloaded at build time).

| File | Source | Licence | Rebuild with |
|---|---|---|---|
| `factbook_equipment.csv` | CIA World Factbook, final edition (2025), field "Military equipment inventories and acquisitions", via [factbook/factbook.json](https://github.com/factbook/factbook.json) | Public domain (CC0) | `pipeline/build_factbook_reference.py` |
| `legacy_holdings.csv` | Wikipedia equipment lists for successor states of the USSR and Yugoslavia; each row records the page title and revision id | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) — this derived file is shared under the same licence, attribution to Wikipedia contributors | `pipeline/build_legacy_reference.py` (needs `lxml`) |

Wikipedia's lists mostly cite the IISS *Military Balance*; quantities are as of each page revision.
