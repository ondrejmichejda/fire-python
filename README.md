# Fire Separation API

Lokální HTTP API pro deterministické výpočty odstupových vzdáleností. Výpočetní logika je zakódovaná v Pythonu podle podkladů v `rules/`, takže chatbot nedělá numerické rozhodování sám. Pošle JSON vstup a převezme hotový výsledek.

## Co API umí

- výpočet odstupové vzdálenosti pro jedno okno nebo dveře,
- výpočet obalového obdélníku skupiny otvorů a automatický výpočet `p0`,
- výpočet procenta požárně otevřené plochy skupiny otvorů,
- kontrolu rozestupů pro samostatné posuzování otvorů podle čl. 10.4.8.1,
- posouzení střechy podle výjimek v `8.15.4`,
- posouzení ETICS podle `3.1.3`,
- orientační práci s tabulkou 15 pro střechy,
- složený endpoint `full-assessment`.

## Spuštění

```bash
python3 app.py --host 127.0.0.1 --port 8000
```

API poběží na `http://127.0.0.1:8000`.

Na Renderu lze aplikaci spustit přímo příkazem:

```bash
python app.py
```

Pokud je v prostředí dostupný `PORT`, aplikace se sama přepne na `0.0.0.0:$PORT`.

Na macOS lze pro ne-IT uživatele spustit API dvojklikem na [start_api.command](/Users/ondra/source/fire-python/start_api.command:1). Otevře se Terminál, server poběží po celou dobu otevřeného okna a zavřením okna se API ukončí.

## Endpointy

- `GET /health`
- `GET /schema`
- `POST /v1/opening-distance`
- `POST /v1/opening-group`
- `POST /v1/opening-percentage`
- `POST /v1/spacing-check`
- `POST /v1/roof-assessment`
- `POST /v1/roof-distance-table15`
- `POST /v1/etics-assessment`
- `POST /v1/full-assessment`

## Příklad: jedno okno

```bash
curl -s http://127.0.0.1:8000/v1/opening-distance \
  -H 'Content-Type: application/json' \
  -d '{
    "opening_id": "W1",
    "width_m": 1.2,
    "height_m": 1.5,
    "pv_kg_m2": 45,
    "structural_system": "mixed"
  }'
```

## Příklad: plný výpočet pro chatbota

```json
{
  "pv_kg_m2": 45,
  "structural_system": "mixed",
  "roof": {
    "pv_kg_m2": 30,
    "fire_safety_level": "II",
    "roof_requirement_status": "splňuje 8.15.1 a)"
  },
  "etics": {
    "insulation_thickness_mm": 180,
    "insulation_reaction_class": "B"
  },
  "openings": [
    { "opening_id": "W1", "width_m": 1.2, "height_m": 1.5 },
    { "opening_id": "D1", "width_m": 1.0, "height_m": 2.1 }
  ],
  "layout": "horizontal",
  "gaps_m": [0.5],
  "spacing_checks": [
    {
      "openings_edge_distance_m": 2.1,
      "distance_opening_1_m": 2.3,
      "distance_opening_2_m": 2.0
    }
  ]
}
```

## Příklad: skupina otvorů bez ručního dopočtu `p0`

```bash
curl -s http://127.0.0.1:8000/v1/opening-group \
  -H 'Content-Type: application/json' \
  -d '{
    "openings": [
      { "id": "O1", "width_m": 1.0, "height_m": 2.0 },
      { "id": "O2", "width_m": 1.0, "height_m": 2.0 }
    ],
    "layout": "horizontal",
    "gaps_m": [0.5]
  }'
```

Stejnou geometrii lze poslat i na `POST /v1/opening-percentage`; endpoint si obalový obdélník spočítá sám. Pro starší integrace dál funguje i varianta s ručně zadaným `bounding_width_m` a `bounding_height_m`.

## Poznámky k návrhu

- API nepoužívá externí knihovny. Běží na standardní knihovně Pythonu.
- `rules/` jsou zdroj znalostí. Runtime je neparsuje; pravidla jsou přepsaná do deterministické logiky.
- Pro střechy mimo rozsah tabulky 15 API vrátí chybu a je potřeba jiný postup.

## Testy

```bash
python3 -m unittest discover -s tests -v
```

## Deploy na Render

Pro ruční založení `Web Service` vyplň:

- `Language`: `Python 3`
- `Branch`: `main`
- `Region`: podle potřeby, pro ČR klidně `Frankfurt (EU Central)`
- `Root Directory`: nechat prázdné
- `Build Command`: `pip install -r requirements.txt`
- `Start Command`: `python app.py`

Alternativně může Render použít blueprint z `render.yaml`.
