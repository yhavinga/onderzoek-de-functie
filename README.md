# Onderzoek de Functie

Wiskundige functie analyse web applicatie. Analyseert functies symbolisch met afgeleiden, extrema, buigpunten en stap-voor-stap uitleg.

## Quickstart

```bash
# Installeer dependencies
pip install -r requirements.txt

# Start de server
uvicorn backend.main:app --reload

# Open http://localhost:8000
```

## Docker

```bash
docker build -t functie .
docker run -p 8000:8000 functie
```

## Features

- Symbolische berekening van f', f'', f'''
- Automatische detectie van nulpunten, extrema en buigpunten
- Interactieve grafiek met optionele afgeleiden overlay
- Stap-voor-stap uitleg in het Nederlands
- Ondersteunt: polynomen, trigonometrische functies, exponentiële functies

## API

```
POST /api/analyseer
{
    "functie": "x^4 - 30x^2",
    "x_min": -10,
    "x_max": 10,
    "toon_afgeleiden": ["f'", "f''"]
}
```
