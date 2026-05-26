# Workflow posouzení odstupových vzdáleností

## 1. Sběr vstupních údajů

Chatbot vyžádá:

- název objektu,
- požární úsek,
- konstrukční systém,
- výpočtové požární zatížení pv,
- rozměry požárně otevřené plochy,
- vzdálenost k hranici pozemku,
- vzdálenost k sousedním objektům,
- údaje o střešním plášti,
- údaje o ETICS.

## 2. Posouzení střešního pláště

Chatbot ověří,
zda je střešní plášť požárně otevřenou plochou
podle čl. 8.15.4 ČSN 73 0802.

## 3. Posouzení ETICS

Chatbot ověří tloušťku ETICS
podle čl. 3.1.3 ČSN 73 0810.

## 4. Posouzení požárně otevřených ploch

Okna a dveře objektu jsou standardně posuzovány
jako požárně otevřené plochy.

Pokud uživatel zadá skupinu otvorů,
chatbot vypočte procento požárně otevřené plochy p₀.

## 5. Úprava požárního zatížení

Výpočtové požární zatížení pv se upraví podle konstrukčního systému:

- nehořlavý: bez navýšení,
- smíšený: +5,
- hořlavý D2: +10,
- hořlavý D3: +15.

## 6. Výpočet teploty požáru

TN = 20 + 345 × log10(8 × pv + 1)

## 7. Výpočet zdrojové hustoty tepelného toku

I = ε × (TN + 273)^4 × 5.67 × 10^-11

ε = 1.0

## 8. Zohlednění procenta sálání

Pokud je posuzována jednotlivá požárně otevřená plocha:

p₀ = 100 %

Pokud je posuzována skupina otvorů:

p₀ = plocha otvorů / plocha obalového obdélníku × 100

Efektivní hustota tepelného toku:

I_eff = I × (p₀ / 100)

kde:

- I = zdrojová hustota tepelného toku při 100 % sálání,
- p₀ = procento požárně otevřené / sálající plochy,
- I_eff = efektivní hustota tepelného toku.

Se snižujícím se p₀
se snižuje I_eff
a výsledná odstupová vzdálenost má obecně klesat.

## 9. Výpočet požadovaného polohového faktoru

φ = 18.5 / I_eff

kde:

- 18.5 kW/m² je kritická hustota tepelného toku.

## 10. Stanovení základní odstupové vzdálenosti

Odstupová vzdálenost d se stanoví iterací ze vztahu:

φ(d,b,h) = 18.5 / I_eff

Pro obdélníkovou požárně otevřenou plochu
se použije vztah pro polohový faktor obdélníku
uvedený ve znalostním souboru.

U skupiny otvorů se pro b a h použije
obalový rozměr skupiny otvorů.

Výsledná odstupová vzdálenost je hodnota d,
při které tepelný tok v posuzovaném bodě
dosáhne kritické hodnoty 18,5 kW/m².

## 11. Posouzení skupiny otvorů podle čl. 10.4.8.1

Pokud p₀ < 40 %,
chatbot se zeptá uživatele,
zda chce ověřit možnost samostatného posouzení jednotlivých otvorů.

Pokud uživatel odpoví ano,
chatbot ověří podmínku:

gap > 0.6 × (d1 + d2)

kde:

- gap = vzdálenost mezi okraji otvorů,
- d1 = odstupová vzdálenost prvního otvoru,
- d2 = odstupová vzdálenost druhého otvoru.

Pokud je podmínka splněna,
lze jednotlivé otvory posuzovat samostatně.

Pokud podmínka splněna není,
skupina otvorů se posuzuje jako jeden obalový otvor.

## 12. Posouzení padání hořících částí

Pokud existuje riziko padání hořících částí,
stanoví se:

d_fall = 0.36 × h_fall

Výsledná odstupová vzdálenost je větší z hodnot:

- základní odstupová vzdálenost,
- odstupová vzdálenost z hlediska padání částí.

## 13. Vyhodnocení požárně nebezpečného prostoru

Chatbot porovná výslednou odstupovou vzdálenost
s hranicí pozemku a okolními objekty.

## 14. Generování kapitoly PBŘ

Chatbot vytvoří:

- úvod,
- normové posouzení,
- posouzení střechy,
- posouzení ETICS,
- tabulku požárně otevřených ploch,
- závěr.