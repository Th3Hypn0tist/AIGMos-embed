# AirQualityMonitorSystem – kehitysmuistiinpanot
Päivitetty: 2026-11-24
Tarkoitus: jatkaminen toisessa ChatGPT-sessiossa. LUE TÄMÄ ENSIN.

## Tilanne lyhyesti

- Repo: https://github.com/Th3Hypn0tist/AirQualityMonitorSystem
- Vanha nimi oli AirQualityMonitor-ESP32. Uusi nimi on tarkoituksella alustariippumaton.
- Ensimmäisten muistiinpanojen aikaan repo oli tyhjä. **2026-11-25 lisättiin talteen aiemmin tuotettu koodiluonnos**, ks. alempana. Koodin toimivuutta ei ole vielä varmistettu ESP32-C6 + TimescaleDB -kokoonpanossa.
- Ensimmäinen testilaitteisto on **ESP32-C6 + CJMCU-8128**. Käyttäjällä on myös ESP8266-laitteita; samaan keruujärjestelmään tulee voida liittää useita erilaisia laitteita.
- Mittaus- ja OLED-testit on tehty edellisessä keskustelussa. **OLED jätetään pois seuraavasta firmwareversiosta.** Paikallinen englanninkielinen web-dashboard säilytetään.
- Tavoite: mittausdata palvelimelle **5 sekunnin välein**, PostgreSQL-kantaan, jossa hyödynnetään TimescaleDB:tä.

## Käyttäjän tekemät arkkitehtuuripäätökset

1. Projekti on **AirQualityMonitorSystem**, EI ESP32:een rajattu tuote. ESP32-C6 on vain ensimmäinen mittauslaite, ESP8266 myös kohde.
2. Tietokanta: **PostgreSQL + TimescaleDB**. Palvelimella on muitakin PostgreSQL-tietokantoja.
3. Mittausjärjestelmän tietokannan nimi: **AirQualityMon** (käyttäjän valitsema nimi).
4. **Mittausarvot omiin sarakkeisiin.** Sarakkeita lisätään vasta, kun uusia sensoreita otetaan oikeasti hyllystä käyttöön. Älä muuta tätä geneeriseksi EAV/measurement-type/value -malliksi.
5. Jokainen laite erotetaan device_id-tunnisteella; puuttuvat mittaukset sallitaan NULL-arvoina. Vältä mittausvirheiden merkitsemistä nolliksi.
6. Raakadataa ei automaattisesti poisteta; pitkän aikavälin säilytys. TimescaleDB:n hypertablet, tarvittaessa jatkuvat aggregaatit ja pakkaus myöhemmissä vaiheissa. Älä ota retention policyä automaattisesti käyttöön.
7. Näytteen lähetys **5 s välein**. Nykyisessä protossa sensorien mittaus/ruudun päivitys oli noin 2 s välein, mutta lopullista ajoitusta ei ole vielä vahvistettu.
8. Älä rakenna ylisuurta abstraktiokerrosta tai tuo lisäriippuvuuksia ilman tarvetta. Aloita toimivalla, testattavalla datankeruulla.
9. Käyttäjä haluaa suunnitella ennen massiivisia koodimuutoksia. Vältä keksimästä uusia ominaisuuksia tai ilmoittamasta toteutusta valmiiksi ilman testiä.

## Toimivaksi todettu ESP32-C6-laitteisto

- ESP32-C6 Dev Module, Arduino ESP32 core 3.3.8, Arduino/C++.
- I²C: SDA GPIO4, SCL GPIO5, 100 kHz; Wire.begin(4, 5, 100000).
- CJMCU-8128-yhdistelmä:
  - 0x40: Si7021-yhteensopiva, lämpötila ja suhteellinen kosteus.
  - 0x5A: CCS811, eCO₂ (ppm, laskennallinen CO₂-ekvivalentti) ja TVOC (ppb). WAK kytketty GND:hen.
  - 0x76: BMP280, lämpötila ja ilmanpaine (hPa).
- Kaikki 3,3 V, I²C-väylä yhteinen.
- Testattu selaindashboard ja mittausarvot toimivat: lämpötila, RH, paine, eCO₂, TVOC, signaalinvoimakkuus.
- Verkon SSID oli IOT, ESP32-C6:n staattinen IP 192.168.0.50, gateway/DNS 192.168.0.1, maski 255.255.255.0. Tarkista seuraavassa sessiossa, ovatko nämä edelleen ajantasaisia. **Älä tallenna Wi-Fi-salasanoja tai tietokantatunnuksia repositorioon.**
- ESP32:n HTTP WebServer portissa 80; dashboard englanniksi, otsikko "Air quality monitor"; JSON API /api/sensors; selain päivittää noin 2 s välein.
- Toteutuksessa käytettiin Wire, WiFi, WebServer; anturit luettiin ilman ulkoisia anturikirjastoja.
- 128x64 OLED 0x3C testattiin, mutta yläpuoliskosta puuttui joka toinen pikselirivi jopa 0xA5 all-pixels-on -testillä. Näytön fyysinen/riviohjainvika todennäköinen; sitä **ei sisällytetä uuteen keruuversioon**. Palauttaminen ei ole prioriteetti.

## Tietokannan suunta

Tietokanta AirQualityMon, suunnitellut alkuperäiset mittaussarakkeet:
- mittausaika (timestamptz, TimescaleDB:n time-dimensio; esimerkiksi measured_at tai received_at, valittava)
- device_id
- temperature_c (Si7021-yhteensopivan anturin)
- bmp_temperature_c (BMP280: erillinen lämpötila)
- humidity_rh
- pressure_hpa
- eco2_ppm
- tvoc_ppb

Mahdolliset hyödylliset metatiedot käyttötarpeen mukaan: boot_id, seq, uptime_ms, rssi_dbm, tilakoodit, palvelimen vastaanottoaika. **Älä pakota kaikkia mukaan ilman yhteistä päätöstä.** Hypertable/uniikki-indeksit on suunniteltava niin, että TimescaleDB:n ositusavain sisältyy uniikkirajoitteisiin.

Tavoite kirjoitusrajapinnalle:
ESP8266/ESP32 → yhteinen HTTP/JSON-sopimus → palvelimen ingest-rajapinta → AirQualityMon (PostgreSQL/TimescaleDB).
ESP-laitteeseen ei laiteta suoria PostgreSQL-tunnuksia. Aiemmin ehdotettiin PHP ingest -endpointia ja HMAC-SHA256-todennusta, mutta **backendin toteutusta tai palvelinasennusta ei ole vielä vahvistettu**. Jos käytetään HTTP:tä ilman TLS:ää, HMAC ei salaa dataa.

## Palvelin / TimescaleDB – tarkka status

- Käyttäjällä on jo PostgreSQL ja MariaDB; PostgreSQL valittiin.
- TimescaleDB-paketti saatiin asennettua APT:llä. Aluksi pakettia ei löytynyt; Debianin pakettivaihtoehto ja valmistajan APT-repo käsiteltiin.
- Komento SHOW shared_preload_libraries; palautti **tyhjän arvon** (ennen asetuksen lisäämistä).
- Ohjeistettiin asettamaan:
    ALTER SYSTEM SET shared_preload_libraries = 'timescaledb';
  ja käynnistämään PostgreSQL:n kyseinen klusteri uudelleen (esimerkkiohjeessa PostgreSQL 17/main).
- Käyttäjä ilmoitti, että nyt on hyvä hetki restartille, koska mitään muuta ei ole kesken. **Ei vielä vahvistettua lokia siitä, että preload, restart, CREATE DATABASE tai CREATE EXTENSION olisivat onnistuneet.** Älä oleta valmista tilaa.
- Aiemmat ehdotetut tarkistukset:
    pg_lsclusters
    sudo -u postgres psql -c "SHOW shared_preload_libraries;"
    sudo -u postgres psql -d AirQualityMon -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';"
- PostgreSQL:n muut tietokannat säilyvät; shared_preload_libraries on kuitenkin **klusterikohtainen** asetus. CREATE EXTENSION ajetaan vain AirQualityMon-kannassa.
- Huomio mixed-case-nimeen: PostgreSQL taittaa lainaamattomat SQL-tunnisteet pieniksi. Jos luodaan täsmälleen nimetty tietokanta, käytä tarvittaessa CREATE DATABASE "AirQualityMon"; ja tarkista olemassa oleva nimi ennen luontia.
- Käyttäjällä on tehokas palvelin ja vähän muita kuormittajia, eikä suorituskykyyn kannata tehdä ennenaikaista optimointia. 5 s väli = 17 280 riviä/vrk/laite, noin 6,3 M riviä/vuosi/laite.

## Ehdotettu mutta EI hyväksytty lopulliseksi tiedostorakenne

- firmware/ (alustakohtaiset ohjelmat: ESP32, ESP8266 jne.)
- server/ (ingest API + konfiguraatiomalli)
- database/ (schema, migrations)
- developement/ (nämä muistiinpanot)

**Hakemiston nimi on tässä tarkoituksella käyttäjän kirjoittama "developement".** Älä uudelleennimeä kysymättä.

## Kesken / seuraavan session aloitus

1. Tarkista repon nykyinen sisältö ja lue tämä tiedosto. Tässä sessiossa tehdään **vain muistiinpanot**, ei firmware- tai skeemakommiteja.
2. Varmista PostgreSQL/TimescaleDB:n todellinen tila (preload, versio, tietokannan olemassaolo, CREATE EXTENSION).
3. Lukitse ensimmäinen minimaalinen skeema: device_id, aikaleima, nykyiset mittaussarakkeet sekä tarpeelliset diagnostiikkakentät.
4. Suunnittele ja toteuta PostgreSQL/TimescaleDB DDL + minimaalinen turvallinen ingest-rajapinta erillisinä tiedostoina. Päätä yhteinen JSON-sopimus, aikaleiman auktoriteetti, idempotenssi ja mitä tapahtuu verkkokatkossa.
5. Vertaa talteen otettua firmwareluonnosta käyttäjän **oikeasti laitteessa ajossa olevaan** versioon. Repoon talletettu .ino on aiemmin generoitu OLEDiton ja 5 s ingest -versio, mutta sitä ei ole todettu käännetyksi tai laitteella toimivaksi. Aiempi OLED:llä testattu koodi ja myöhemmät käyttäjän käsin tekemät OLED-asettelumuutokset eivät ole varmuudella samassa tiedostossa. Säilytä toimiva mittaus- ja dashboard-logiikka, älä oleta ingestin toimivan.
6. Testaa ensin tietokannan kirjoitus vastaanottorajapinnasta, sitten yksittäisen ESP32-C6:n päästä, lopuksi lisätään ESP8266.
7. Säilytä käyttäjän päätös: uudet sensoriarvot → uusia sarakkeita hallitusti migraatiolla; ei EAV-mallia.

## Tietojen varmuus

Tämä dokumentti kirjaa keskustelussa päätetyt asiat ja aiemmat testihavainnot. Se **ei** todista, että palvelin olisi jo asetettu valmiiksi tai että uusin keruuversio olisi käännetty ja testattu.

## 2026-11-25: aiemmat lähdekoodit talteen (TÄRKEÄ)

Käyttäjä pyysi myös nykyisen koodin tallentamista. Aiemmin samassa keskustelussa tuotettu **OLEDiton PostgreSQL-ingest-luonnos** on nyt commitattu erikseen:
- `firmware/esp32-c6/AirQualityMonitor/AirQualityMonitor.ino` – aiemmin tuotettu 5 s HTTP-ingestillä varustettu Arduino-luonnos
- `server/public/ingest.php` – PHP-vastaanotin
- `server/private/config.example.php` – **vain esimerkkiasetukset**, ei salasanoja
- `database/schema.sql` – **vanha tavallisen PostgreSQL:n** skeemaluonnos

**Ei saa tulkita valmiiksi toteutukseksi!** Tallennus on lähdekoodin arkistointi tulevaa jatkoa varten. Merkittävä ero sovittuun uuteen arkkitehtuuriin: `config.example.php` käyttää tietokantanimeä `air_quality` (pitää vaihtaa `AirQualityMon`-nimeen, tarkistettava kirjainkoon käsittely); `schema.sql` käyttää tavallista taulua ja `id PRIMARY KEY` + `UNIQUE(device_id,boot_id,seq)` ilman ositusaikaa, mikä ei sellaisenaan käy TimescaleDB-hypertablen uniikkirajoitteiksi. Suunnittele DDL uudelleen ennen käyttöönottoa.

ESP32-C6:n *viimeisin fyysisesti testattu* ohjelma käytti OLEDia, mutta sen koko täsmällistä lähdekoodia ei ole vielä palautettu tämän repon arkistoon. Pyydä laitteen ajossa oleva .ino tai etsi se aiemmasta sessiosta, jos tarvitsee verrata. **Älä korvaa toimivaa laiteversiota arkistoidulla, testaamattomalla keruuversiolla ilman testausta.**
