# Met de Ape naar Koolweg 42

Een 3D-spelletje in de browser: je rijdt van Soemeersingel 25 in Helenaveen naar Koolweg 42, langs de Helenavaart, over de houten fietsbrug en de betonnen brug bij Kamp Mariaveen, en over de wortelbulten van de laanbomen.

Spelen: https://jankeesvw.github.io/ape-helenaveen/

## Wagens

Op de startkaart kies je je wagen; de snelste tijd wordt per wagen bijgehouden.

- **Piaggio Ape**, groen, met een laadbak vol kool. Haalt 45 km/u, opgevoerd 70, en kantelt als je hem op snelheid op vol stuur neemt.
- **Fiat 500** (de oude), rood, met het linnen schuifdak. 85 km/u, plankgas 95.
- **Volkswagen Kever** (de oude), rood, met losse spatborden en treeplanken. 100 km/u, plankgas 120.
- **Volkswagen T2-busje**, Samtgrün met een wit dak. 95 km/u, plankgas 110, en helt flink over in de bocht.

## Besturing

Pijltjes of WASD om te rijden, Shift voor opgevoerd (tot 70 km/u), spatie om te remmen, H om te toeteren, C voor een andere camera en R om terug op de weg te komen. Op een telefoon stuur je met je duim over het stuurvlak links en zitten gas en rem rechts.

## Hoe het gemaakt is

Alles staat in één HTML-bestand met [three.js](https://threejs.org). De wereld komt uit open data:

- wegen, water en landgebruik: © [OpenStreetMap-bijdragers](https://www.openstreetmap.org/copyright) (ODbL)
- bomen: het [AHN](https://www.ahn.nl) via PDOK. Langs de wegen zijn het eiken, in het bos dennen, berken en eiken. Het verschil tussen oppervlakte- en maaiveldmodel geeft de hoogte van alles boven de grond; zonder de gebouwen blijven de boomkruinen over, en elke kruintop wordt een boom met zijn echte hoogte en kruinstraal. De wortelbulten op de Soemeersingel en de Koolweg liggen bij die echte laanbomen.
- gebouwen met echte dakvormen en hoogtes: [3DBAG](https://3dbag.nl) van de TU Delft (CC BY 4.0)
- adressen, bouwjaar en gebruiksdoel: BAG via [PDOK](https://www.pdok.nl)
- ondergrond en dakkleuren: de actuele luchtfoto van [PDOK](https://www.pdok.nl) (CC BY 4.0), in tegels in `luchtfoto/` (telefoons laden de halve resolutie uit `luchtfoto/lr`)

De brondata staat niet in de repo. Opnieuw opbouwen gaat zo:

```bash
tools/fetch_osm.sh
python3 tools/fetch_3dbag.py
python3 tools/fetch_bag.py
python3 tools/fetch_luchtfoto.py   # vraagt Pillow
python3 tools/ahn_trees.py         # vraagt numpy, scipy en Pillow
python3 tools/build.py             # schrijft index.html
```

`src/game.html` is de game zelf, `tools/build.py` zet de kaartdata om en plakt die erin. Lokaal spelen kan met `python3 -m http.server` in deze map.
