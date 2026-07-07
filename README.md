# Astrologica — Local Astrology Engine

**Teljesen lokális asztrológiai számítási rendszer**, ami az AstroWay API-t hivatott helyettesíteni. Nem függ külső szolgáltatásoktól — minden számítás a saját gépeden fut.

## Gyors indítás

```bash
cd ~/Projects/astrologica
source .venv/bin/activate
python -m pytest tests/ -v          # tesztek futtatása
```

## Modulok

| Modul | Funkció | Státusz |
|-------|---------|---------|
| `core.py` | Swiss Ephemeris wrapper, bolygók, házak, ayanamsa | ✅ |
| `western.py` | Western natal, aspektusok, dignities, tranzitok, synastry, returns, progressions | ✅ |
| `vedic.py` | Vedic nakshatra, Vimshottari/Ashtottari Dasha, varga chartok, yogák, doshák, panchang | ✅ |
| `bazi.py` | BaZi Four Pillars, Day Master, Ten Gods, Luck Pillars, element balance | ✅ |
| `numerology.py` | Pythagorean, Chaldean, Kabbalistic, Vedic numerológia | ✅ |
| `destiny.py` | Destiny Matrix (Ladini) | ✅ |
| `mayan.py` | Tzolkin, Haab, Long Count, Dreamspell | ✅ |
| `hd.py` | Human Design (BodyGraph, gates, channels, type/authority/profile) | ⚠️ |
| `divination.py` | Tarot (3 deck), I Ching, Runes, Geomancy | 🔄 |
| `config.py` | Custom endpoint, AstroWay backup, LLM provider | ✅ |

## Használat példa

```python
from astrologica.core import BirthData, compute_positions, compute_houses
from astrologica.western import natal_chart
from astrologica.vedic import nakshatra, vimshottari_dasha
from astrologica.bazi import four_pillars

# Születési adatok
birth = BirthData("1991-02-15", "17:45:00", 48.2264, 22.0847,
                   tz="Europe/Budapest", place="Kisvárda")

# Western natal chart (trópusi)
chart = natal_chart(birth)

# Vedic nakshatra (sziderikus)
positions = compute_positions(birth, sidereal=True, ayanamsa="lahiri")
moon_nak = nakshatra(positions["Moon"].longitude)

# BaZi Four Pillars
pillars = four_pillars(birth)
```

## AstroWay kompatibilitás

Az AstroWay API backup-ként megmarad. A `config.yaml`-ban beállítható:

```yaml
api_base_url: "https://api.astroway.info/v1"
api_key: "aw_test_..."
api_user_agent: "Mozilla/5.0 ..."  # Cloudflare WAF workaround
```

## Verifikáció

A számítások az Astro Seek-kel vannak ellenőrizve (±30 ívmásodperc pontosság):
- Ayanamsa Lahiri: 23°44' (1991-02-15)
- 10 bolygó sziderikus pozíciója: 10/10 egyezik
- BaZi Four Pillars: Xin Wei / Geng Yin / Bing Chen / Ding You

## Fejlesztés

```bash
cd ~/Projects/astrologica
source .venv/bin/activate
uv pip install pyswisseph pytest ruff   # ha hiányzik
python -m pytest tests/ -v              # tesztek
ruff check astrologica/                  # lint
```
