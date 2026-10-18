# Helenaveen bezorgd

Een 3D-spelletje in de browser: vanaf Soemeersingel 25 in Helenaveen bezorg je in vijf minuten zoveel mogelijk adressen, langs de Helenavaart, over de houten fietsbrug en de betonnen brug bij Kamp Mariaveen, en over de wortelbulten van de laanbomen. Rij je te hard waar de politie het ziet, dan komen ze achter je aan.

Spelen: https://jankeesvw.github.io/helenaveen-bezorgd/

## Wagens

Op de startkaart kies je je wagen; de beste dienst wordt per wagen bijgehouden.

- **Piaggio Ape**, groen, met een laadbak vol kool. Haalt 45 km/u, opgevoerd 70, en kantelt als je hem op snelheid op vol stuur neemt.
- **Fiat 500** (de oude), rood, met het linnen schuifdak. 85 km/u, plankgas 95.
- **Volkswagen Kever** (de oude), rood, met losse spatborden en treeplanken. 100 km/u, plankgas 120.
- **Volkswagen T2-busje**, Samtgrün met een wit dak. 95 km/u, plankgas 110, en helt flink over in de bocht.

## Bezorgen

Een dienst duurt vijf minuten. Je krijgt steeds een willekeurig adres in het dorp, een van de bijna vierhonderd echte adressen uit de BAG; het paaltje met het huisnummer staat aan de stoep en een lichtbaken wijst het van ver aan. Sta je er stil, dan is het bezorgd en krijg je meteen het volgende adres. Elk adres levert punten op naar de afstand, plus fooi die wegloopt naarmate je er langer over doet.

Elk adres krijgt een eigen lading, die in de laadbak van de Ape staat of op een imperiaal op het dak van de andere wagens. Een pakketje of kool van de Koolweg zijn gewoon; pizza's leveren meer fooi op maar die loopt snel weg; eieren en een verjaardagstaart breken op bulten en bij klappen; uit een aquarium met een goudvis klotst het water als je hard remt of scherp stuurt; melkbussen zijn zwaar, zodat je minder snel optrekt, maar leveren meer op. Wat er kapot is gaat van de punten af.

## Helenaveen van toen

Na elke twee gewone adressen wacht een verhaal uit de geschiedenis van het dorp: eerst iets ophalen, dan wegbrengen. Eierkisten van een kippenhouder aan de Koolweg naar de eierwagen op de Sevenumseweg; warme melk voor de kaasboerin op een Koningshoeve, voordat hij afkoelt; de Gouden Helm die turfsteker Gebbel Smolenaars in 1910 vond; twee botanici die in 1895 door de kermis geen bed hadden en naar Meijel moesten; bijenkasten voor meester Theelen, waar bij een klap de bijen uit ontsnappen; en balen turfstrooisel van de eerste turfstrooiselfabriek van Nederland.

Langs de weg staan bruine bordjes met een gouden munt erboven. Rijd je erlangs, dan krijg je een weetje over het oude Helenaveen (de kazemat bij Soemeersingel 25, de kool onder glas aan de Koolweg, de scheepswerf, de sage van het Soemeer en meer) en tijdens een dienst 25 punten. Welke je al hebt gevonden, onthoudt je browser.

De verhalen en weetjes komen van [Helenaveen van toen](https://www.helenaveenvantoen.nl), [DeurneWiki](https://www.deurnewiki.nl) en de [straatnaamverklaring van André Vervuurt](https://www.andre-vervuurt.nl/09_Straatnaamverklaring_AV.pdf).

## Politie

Er rijden steeds twee witte politiewagens rond. Overal geldt de echte maximumsnelheid uit OpenStreetMap (veel 30 in het dorp, 60 erbuiten), die zie je naast je teller. Rij je meer dan 5 km/u te hard en ziet een politiewagen het, dan gaan zwaailicht en sirene aan en komen ze achter je aan, zoals in GTA. Hoe langer de achtervolging duurt, hoe meer sterren en hoe meer wagens; een politiewagen rammen helpt ook niet. Zolang ze achter je aan zitten kun je niet bezorgen. Blijf lang genoeg uit hun zicht (achter de huizen, of gewoon verder weg) en ze geven het op, wat je wat punten oplevert. Val je stil met een politiewagen tegen je aan, dan ben je aangehouden en kost de bekeuring 100 punten per ster.

## Rijden

De wagens rijden met echte physics (Rapier): elk heeft zijn eigen massa, zwaartepunt en vering per wiel. Ze hellen over in de bocht, duiken bij het remmen, stuiteren over de wortelbulten en glijden weg als je de grip kwijtraakt, op zand en gras eerder dan op asfalt. Een Ape neem je op snelheid niet op vol stuur: dan gaat hij op twee wielen en daarna om. Huizen, bomen en brugleuningen houden je echt tegen.

## Verkeer

Om je heen rijdt verkeer: auto's, bestelbussen, trekkers (soms met een aanhanger vol kratten kool of aarde) en fietsers, en een flink deel komt je over je route tegemoet. Ze houden rechts, remmen voor wat er voor ze rijdt, wijken op smalle weggetjes uit naar de berm, halen een fietser of trekker in als de weg vrij is en gaan opzij voor een politiewagen met zwaailicht. Sta je stil in de weg, dan toeteren ze of bellen ze. Rijd je iemand aan terwijl de politie het ziet, dan komen ze achter je aan.

## Onderweg

Af en toe staat er een bewoner in de voortuin die je nazwaait, of loopt er iemand langs de weg. Bij de voordeuren zitten katten; die rennen weg als je te dichtbij komt, en soms schiet er een vlak voor je de weg over. Op het kanaal zwemmen zwanen, sommige met grijze jongen erachteraan. Toeter je, dan zwaaien de mensen terug, schieten de katten weg en sissen de zwanen.

## Besturing

Pijltjes of WASD om te rijden, Shift voor opgevoerd (tot 70 km/u), spatie om te remmen (blijf je erop staan, dan rij je achteruit), H om te toeteren, C voor een andere camera en R om terug op de weg te komen. Op een telefoon stuur je met je duim over het stuurvlak links en zitten gas en rem rechts.

## Hoe het gemaakt is

Alles staat in één HTML-bestand met [three.js](https://threejs.org), [Rapier](https://rapier.rs) voor de physics en [N8AO](https://github.com/N8python/n8ao) voor de ambient occlusion (alleen op de computer, samen met een lichte bloom en SMAA). Met `#simpel` achter de URL rijd je met de oude eenvoudige besturing, met `#plat` zonder nabewerking. De wereld komt uit open data:

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
