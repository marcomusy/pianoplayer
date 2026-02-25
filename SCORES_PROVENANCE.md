# Scores Provenance

This document tracks provenance and copyright risk for files in `scores/`.

Policy used for this repository:
- Keep only files with clear provenance and low redistribution risk.
- Treat third-party engravings/arrangements from community sites as restricted unless explicit reuse rights are documented.

## Inventory

| File | Provenance signal in file | Risk | Recommendation |
|---|---|---:|---|
| `scores/test_scales.xml` | Generic test title; no third-party source URL | Low | Keep |
| `scores/test_chords.xml` | Generic test title; no third-party source URL | Low | Keep |
| `scores/test_octaves.xml` | Test title; composer field is `Music21` | Low | Keep |
| `scores/bach_invention4.xml` | Generated from Mutopia BWV 775 MIDI (`Mutopia-2008/06/15-67`, listed Public Domain) on 2026-02-25 | Low | Keep |
| `scores/bach_airgstring.xml` | Generated from Mutopia BWV 1068 MIDI (`Mutopia-2008/10/28-1534`, listed Public Domain) on 2026-02-25 | Low | Keep |
| `scores/bach_prelude.xml` | Generated from Mutopia BWV 846 MIDI (`Mutopia-2011/09/12-5`, listed Public Domain) on 2026-02-25 | Low | Keep |
| `scores/bach_joy.xml` | Generated from Mutopia BWV 610 MIDI (`Mutopia-2006/03/27-706`, listed Public Domain) on 2026-02-25 | Low | Keep |
| `scores/mozart_sonfacile.xml` | Generated from Mutopia K.545 MIDI (`Mutopia-2013/09/01-998`, licensed CC BY-SA 3.0) on 2026-02-25 | Low (attribution/share-alike obligations) | Keep |
| `scores/pachelbel_canon.xml` | Generated from Mutopia Canon in D MIDI (`Mutopia-2009/09/07-1700`, licensed CC BY 3.0) on 2026-02-25 | Low (attribution required) | Keep |

## Notes

- Public-domain composers (e.g., Bach, Mozart, Pachelbel, Couperin) do not automatically make a specific modern engraving/arrangement public-domain.
- A file being available on MuseScore does not by itself grant redistribution rights in this repository.
- If a score is retained, add explicit proof of license/permission (source URL + license terms + date checked).

## Removed Files

These files were removed from `scores/` on 2026-02-25 due to redistribution risk:
- `scores/clayderman_ladyd.xml`
- `scores/couperin_baricades.xml`
