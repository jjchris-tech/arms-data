# Reference data

Small, openly licensed files committed to the repo (unlike SIPRI data, which is downloaded at build time).

| File | Source | Licence | Rebuild with |
|---|---|---|---|
| `factbook_equipment.csv` | CIA World Factbook, final edition (2025), field "Military equipment inventories and acquisitions", via [factbook/factbook.json](https://github.com/factbook/factbook.json) | Public domain (CC0) | `pipeline/build_factbook_reference.py` |
| `legacy_holdings.csv` | Wikipedia equipment lists for successor states of the USSR and Yugoslavia; each row records the page title and revision id | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) — this derived file is shared under the same licence, attribution to Wikipedia contributors | `pipeline/build_legacy_reference.py` (needs `lxml`) |
| `un_votes_es11.csv` | Per-country votes on UN General Assembly resolutions ES-11/1 to ES-11/9, from Wikipedia's resolution pages, each checked against the official tally (`matches_tally`) | CC BY-SA 4.0 | `pipeline/build_research_reference.py` |
| `ideal_points.csv` | Voeten, Strezhnev & Bailey UN General Assembly ideal points, 2015–2025 ([Harvard Dataverse hdl:1902.1/12379](https://dataverse.harvard.edu/dataset.xhtml?persistentId=hdl:1902.1/12379)) | CC0 | same |
| `democracy.csv` | V-Dem electoral democracy index and region, 2015–2025, via Our World in Data | CC BY 4.0 | same |

Wikipedia's lists mostly cite the IISS *Military Balance*; quantities are as of each page revision.
