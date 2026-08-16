# astrologica

Local astrology computation engine — fully offline, no external APIs.

## What It Does

Replaces cloud astrology APIs (AstroWay 716+ endpoints) with local Swiss Ephemeris calculations. Covers:

- **Western**: natal charts, aspects, dignities, transits, synastry, returns, progressions, midpoints, antiscia, harmonics, draconic, heliocentric, composite, davison, fixed stars, moon phase, sun times, planetary hours, void-of-course moon, Gauquelin sectors, element balance
- **Timing**: profections, firdaria, primary/symbolic/tertiary/minor directions, lunar/solar/planetary returns, ingress search, retrograde periods, eclipses, transit calendar, forecast calendar
- **Astrogeography**: ACG lines, local space, geodetic, parans, relocation charts
- **Vedic**: nakshatra, dashas (Vimshottari/Ashtottari), panchang, varga charts (D1-D60), yogas, doshas, ashtakoota compatibility, muhurat engine, ashtakavarga
- **Chinese**: BaZi four pillars, day master, ten gods, luck pillars, Zi Wei Dou Shu
- **Human Design**: bodygraph, gates, channels, type/authority/profile, transits, compatibility, incarnation cross
- **Other**: Destiny Matrix, Mayan calendar, numerology (4 systems), tarot, I Ching, runes, geomancy
- **Hellenistic**: Hermetic lots, Egyptian bounds, zodiacal releasing

## Stack

- Python 3.11 + pyswisseph 2.10.3.2 (Swiss Ephemeris)
- JPL DE431 ephemeris data (1800–2400)
- Fixed star catalog (sefstars.txt)

## Quick Start

```bash
cd ~/Projects/astrologica
source .venv/bin/activate
python -c "
from astrologica.core import BirthData, compute_positions
birth = BirthData('1991-02-15', '18:45:00', 48.2264, 22.0847, tz='Europe/Budapest')
pos = compute_positions(birth, sidereal=True)
for name, p in pos.items():
    print(f'{name:8s} {p.sign_name:12s} {p.degree_in_sign:6.2f}°')
"
```

## Modules

| Module | Contents |
|--------|----------|
| `core.py` | BirthData, compute_positions, compute_houses |
| `western.py` | natal_chart, aspects, transits, synastry, solar_return, progressions |
| `western_ext.py` | midpoints, antiscia, harmonics, draconic, fixed stars, moon phase, etc. |
| `timing.py` | profections, firdaria, returns, eclipses, transit calendar |
| `astrogeo.py` | ACG lines, local space, geodetic, parans, relocation |
| `vedic.py` | nakshatra, dashas, panchang, varga, yogas, doshas |
| `vedic_ext.py` | ashtakoota, muhurat, ashtakavarga |
| `bazi.py` | four pillars, day master, ten gods, luck pillars |
| `hd.py` | Human Design bodygraph |
| `hd_ext.py` | HD transits, compatibility, incarnation cross |
| `ziwei.py` | Zi Wei Dou Shu |
| `destiny.py` | Destiny Matrix (Ladini) |
| `mayan.py` | Tzolkin, Haab, Long Count, Dreamspell |
| `numerology.py` | Pythagorean, Chaldean, Kabbalistic, Vedic |
| `divination.py` | Tarot, I Ching, Runes, Geomancy |
| `hellenistic.py` | Hermetic lots, Egyptian bounds, zodiacal releasing |
| `render.py` | SVG wheels, aspect grid, transit calendar markdown |

## Tests

```bash
python -m pytest tests/ -q  # 261 passed
```

## Version History

- **0.2.0** (2026-08-16): Full AstroWay replacement. Added timing engine, astrogeo/ACG, vedic_ext (muhurat, ashtakoota, ashtakavarga), ziwei, hd_ext, hellenistic. 261 tests.
- **0.1.0** (2026-07-07): Initial release. 11 modules, 146 tests.
