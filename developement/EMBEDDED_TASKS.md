# AIGMos Embedded – työlista

Tavoite: natiivi alustariippumaton AIGMos-toteutus mikrokontrollereille. AQM on ensimmäinen referenssisovellus. Tämä on työlista, ei toteutuneen protokollan dokumentaatio.

## 1. Arkkitehtuuri ja rakennemäärittely
- [x] AIGMos Embedded -repository (`AIGMos-embed`).
- [ ] Koneellisesti luettava SSOT ja AIGMos-yhteensopivat rakenteet. (Alustava `embedded/structure.json`.)
- [x] Natiivin C/C++-toteutuksen rajaus (C99 baseline, C++ adapter ABI).
- [ ] HardCore-, Core-, Adapter- ja UserModule-erottelu.
- [ ] Build-kohtainen ominaisuuksien karsinta. (Valittujen runtime-lähteiden build plan ja object compilation lisätty; linkitys ja kohdealustat avoinna.)
- [ ] Nollariippuvuuden automaattinen validointi. (Include-rajojen tarkistin lisätty; ajo ja linkitysauditointi avoinna.)
- [ ] Alustariippumattomuuden validointi.

## 2. HardCore
- [ ] State ja #I-namespace. (Ensimmäinen C99-toteutus ja host-testi lisätty; testiajo avoinna; #I-kirjoitusrajapinta lisätty.)
- [ ] Command Surface ja Command Registry. (Natiivin rekisterin ja dispatchin ensimmäinen toteutus lisätty; host-testi ja AC avoinna.)
- [ ] Trigger, Event, Runner ja TER-suoritusketju. (Korjattu erillisiin rekistereihin: Trigger condition/state, Event trigger/commands, Runner state/commands; host-testit päivitetty, ajo avoinna.)
- [ ] TER:n condition-semantiikka, aktivointi ja resetointi vahvistettava AIGMos 1.9:n kanssa.
- [ ] Valinnainen ExpressionEngine ja Expression Registry; Expression Condition != Trigger Condition, ei TER-riippuvuutta. Tarkasta 1.9-syntaksi ennen toteutusta.
- [ ] Rutiinien suoritus. (Nimetyt &-rutiinit, järjestetty suoritus, virhekatkaisu ja rekursiosuoja lisätty; host-testi ajamatta.)
- [ ] AccessCore-tuen valinnainen sisällyttäminen. (AIGMOS_ACCESSCORE-build flag ja fail-closed CS-valtuutusrajapinta lisätty; ei vielä varsinaista AccessCore-integraatiota; testi ajamatta.)
- [ ] Muistinkäytön minimointi ja suorituskykytestit. (Host sizeof -profilointityökalu lisätty; ajo ja kohdealustamittaukset avoinna.)

```text
Sensor
└── Input Module
    └── State
        └── #I:sensor
            └── Trigger
                └── Event
                    └── Runner
                        └── Command
                            └── Output Module
                                └── Actuator
```

## 3. Platform Adapters
- [ ] Yhteinen alustarajapinta. (Ensimmäinen ulkoinen C ABI lisätty; adapterit ja testaus avoinna.)
- [ ] GPIO, ADC, PWM, I²C, SPI, UART.
- [ ] Timers, flash storage, network.
- [ ] ESP8266-adapteri.
- [ ] ESP32-C6-adapteri.
- [ ] ESP32-S3-adapterivalmius (ei vielä toteutusvaatimusta).
- [ ] Alustakohtaiset toolchainit.
- [ ] Piirilevykohtaiset pinout-määritykset, pin capabilities ja rajoitukset. (D1 mini -metadata lisätty, verifioimatta.)

## 4. Module Registry
- [ ] Yhteinen moduulirakenne. (Ensimmäinen koneellisesti luettava sensorirekisteri lisätty.)
- [ ] Tunnistusfunktiot, liityntävaatimukset, pin bindings.
- [ ] Input- ja Command-määritykset. (Namespace moduulikohtainen, #I fyysisille ja #OSC OSC IN:lle.)
- [ ] Moduulikohtaiset konfiguraatiot.
- [ ] Alustayhteensopivuus, riippuvuudet ja validointi.

```text
Module Registry
├── Input Modules
│   ├── BMP180
│   ├── BMP280
│   ├── DHT11
│   ├── HDC1080
│   ├── Si7021
│   └── CCS811
├── Output Modules
├── Communication Modules
│   └── OSC
└── Custom Modules
```

## 5. Node Manager
- [ ] Automaattinen USB-, MCU- ja flash-muistitunnistus.
- [ ] MAC-pohjainen node ID ja pysyvä node registry. (Atominen paikallinen JSON-rekisteri lisätty; testiajo avoinna.)
- [ ] Alustakohtaisen probe-firmwaren muodostaminen.
- [ ] Probe-firmwaren flashaus eksplisiittisellä Detect hardware -käskyllä.
- [ ] I²C-sensoritunnistus ja GPIO-tunnistus sallituilla pinneillä.
- [ ] Hardware inventory.
- [ ] Moduulien manuaalinen lisääminen, poistaminen ja vaihtaminen.
- [ ] Nodekohtaisten kompositioiden tallentaminen ja palauttaminen. (SHA-256-versiot ja palautus lisätty; testiajo avoinna.)

## 6. Pin Mapper
- [ ] Piirilevykohtainen visuaalinen pinout.
- [ ] Moduulien liityntävaatimusten automaattinen esittäminen.
- [ ] Interaktiivinen pinnien bindaus ja capabilities-suodatus.
- [ ] Varattujen pinnien ja boot-strapping-rajoitusten tunnistus.
- [ ] Pin conflict detection. (Python-validaattori ja testit lisätty; ajamatta.)
- [ ] Jaetut väylät ja I²C-osoitekonfliktit. (Validaattori lisätty; testit ajamatta.)
- [ ] Puuttuvien bindausten validointi. (Ensimmäinen toteutus eksplisiittisille I2C/GPIO-bindauksille.)
- [ ] Moduulikohtainen live-testaus.

## 7. Network Manager
- [ ] OSC-nodejen ja legacy PostgreSQL -nodejen tunnistus.
- [ ] USB- ja verkkoinventaarion yhdistäminen.
- [ ] MAC-pohjainen IP-rekisteri. (Paikallinen toteutus lisätty.)
- [ ] Automaattinen IP-allokointi 50 + node_index (nollapohjainen; 192.168.0.50, .51, ...). (Toteutus lisätty, testiajo avoinna.)
- [ ] Osoitekonfliktien tarkistus ja aiempien varausten säilyttäminen. (Rekisterin sisäinen ja annetun inventaarion tarkistus lisätty; aktiivinen verkkohaku avoinna.)
- [ ] DHCP, static IP, manuaalinen IP ja Wi-Fi-konfiguraatio.
- [ ] OSC destination ja UDP 9000.
- [ ] Verkkoyhteyden validointi.

## 8. Composition Engine
- [ ] Kohdealustan, HardCore- ja Core-ominaisuuksien valinta. (Platform/board ja HardCore feature resolver lisätty; Core-valinta lisätty build plan -tasolla.)
- [ ] Input-, Output-, Communication- ja UserModule-valinnat.
- [ ] State-rakenteen, Command Registryn ja TER-konfiguraation muodostaminen. (C99-taulugeneraattori lisätty; tyypitetyt komentoargumentit lisätty; testiajo ja täydet moduulibindaukset avoinna.)
- [ ] Pin bindings -generointi.
- [ ] Riippuvuuksien resolvointi ja komposition validointi. (Natiivien State/CS/TER-taulujen validointi lisätty; host-testi ajamatta.)
- [ ] Firmware-lähdekoodin generointi. (Ensimmäinen State/CS/TER-taulujen generointi; ei vielä kokonainen firmware.)
- [ ] Build manifest ja komposition versionointi. (Deterministinen draft manifest ja SHA-256 lisätty; lähde- ja header-hashit sekä generated code -hash lisätty build plan -tasolla; build-ready manifest avoinna.)

```text
Composition
├── Platform
├── HardCore
├── Core
├── Input Modules
├── Output Modules
├── Communication Modules
├── UserModules
├── State Definition
├── Commands
├── TER Configuration
└── Hardware Bindings
    └── Validated Composition
        └── Build
            └── Firmware Artifact
```

## 9. Deployment
- [ ] Alustakohtainen build ja toolchain-tunnistus.
- [ ] Build-lokitus. (Host object compilation -lokitus lisätty, testiajo avoinna.)
- [ ] Flashaus ja Push to node.
- [ ] Flashauksen, firmwareversion ja komposition verifiointi.
- [ ] Sensorien toiminnan ja verkkoyhteyden verifiointi.
- [ ] Virhetilanteista palautuminen.

```text
DISCONNECTED
└── CONNECTED
    └── IDENTIFIED
        └── [ Detect hardware ]
            └── PROBE BUILD
                └── PROBE FLASH
                    └── DISCOVERY
                        └── CONFIGURATION
                            ├── Module selection
                            ├── Pin mapping
                            ├── Network configuration
                            ├── State configuration
                            └── TER configuration
                                └── VALIDATED
                                    └── [ Push to node ]
                                        └── COMPOSITION
                                            └── BUILD
                                                └── FLASH
                                                    └── VERIFY
                                                        └── ONLINE
```

## 10. AIGMos Panel / TUI
- [x] LMTS:n TUI-rakenteen alustava tarkastus.
- [ ] Yhteisten TUI-primitiivien erottelu ja AIGMos Panel.
- [ ] Node Manager UserModule.
- [ ] Nodes-, Hardware- ja Module Manager -näkymät.
- [ ] Pin Mapper ja Network Configuration.
- [ ] State-, Command- ja TER Configuration.
- [ ] Composition-, Deployment- ja Monitor-näkymät.
- [ ] Command Surface -integraatio.

## 11. AQM – ensimmäinen referenssisovellus
- [x] Nykyisen ratkaisun arkistointi.
- [x] Nykyisen tietokantaskeeman tarkastus.
- [x] OSC IN -backendin ensimmäinen toteutus (testaamatta).
- [x] Psycopg-integraation ensimmäinen toteutus (testaamatta).
- [ ] OSC-moduulin ja nykyisten sensorimoduulien sovittaminen AIGMos Embedded -rakenteeseen. (BMP180 ja DHT11 natiivit C99-ajurit sekä #I-kirjoitus lisätty; adapteri, OSC ja testiajo avoinna.)
- [ ] AQM-kompositiomääritys. (ESP8266 BMP180+DHT11 -luonnos lisätty; OSC ja TER vielä avoinna.)
- [ ] Mittausten kirjoittaminen Stateen #I-rakenteella. (BMP180/DHT11 sample-rajapinnat lisätty, virheessä NULL; integraatiotestaus avoinna.)
- [ ] TER-pohjainen mittaus- ja lähetysrutiini, 5 s.
- [ ] Kalibrointitoiminnallisuus.
- [ ] Expose-yhteensopiva Python OSC IN → #OSC → AQM DB-käsittely; verifioi 1.9 Expose -sopimus.
- [ ] Säilytä lasermittaus, kalibrointi, mittausdata, DB-funktiot ja dashboard; vain node→backend-protokolla muuttuu.
- [ ] Backendin integraatiotestaus.
- [ ] Nykyisen dashboardin yhteensopivuuden verifiointi.

## 12. Integraatiotestaus
- [ ] ESP8266 – BMP180 + DHT11. (Ajurit ja host-vektoritesti lisätty; ajo ja laitetestaus avoinna.)
- [ ] Tyhjän noden tunnistus ja probe-firmware.
- [ ] Pin Mapper ja komposition muodostaminen.
- [ ] Push to node.
- [ ] State, #I ja TER.
- [ ] OSC OUT, OSC IN, PostgreSQL ja dashboard.
- [ ] Rinnakkaiskäyttö nykyisen ESP32-C6-noden kanssa.
- [ ] ESP32-C6:n migraatio vasta ESP8266:n hyväksytyn testauksen jälkeen.
- [ ] Muistinkäytön profilointi ja pitkäkestoiset toimintatestit.
- [ ] Nollariippuvuuden verifiointi.

## 13. Dokumentointi
- [ ] Asennustyökalu, toolchainien ja UserModule-riippuvuuksien asennus.
- [ ] Node Managerin käyttöohje.
- [ ] Uuden alustan, moduulin ja komposition lisääminen.
- [ ] Toteutuneen arkkitehtuurin dokumentointi.
- [ ] PROTOCOL.md:n päivittäminen vain toteutuneen toiminnallisuuden perusteella.

## Arkkitehtuurin invariantit

| Ominaisuus | Vaatimus |
|---|---|
| AIGMos | 0 ulkoista riippuvuutta |
| HardCore ja Core | Alustariippumattomat |
| Arduino | Ei pakollinen |
| Valmistajien SDK:t | Ulkoisissa adaptereissa |
| UserModules | Riippuvuudet sallittu |
| Input | Input Module → State → moduulin namespace (#I / #OSC) |
| Output | Command → Output Module |
| Suoritusmekanismi | TER, riippumaton ExpressionEnginestä |
| Event | Trigger reference/state + Commands; ei omaa statea |
| Expose | OSC IN → #OSC; AQM DB-käsittely erillinen |
| SSOT | Koneellisesti luettava rakenne |
| Firmware | Komposition build-artifact |
| TUI | AIGMos Panel, johdettu LMTS:stä |
| Provisiointi | Kaksivaiheinen, eksplisiittiset Detect hardware ja Push to node |
| AQM-tietokantaskeema | Ei muutoksia |
| AQM-dashboard | Säilytetään |
| Tiedonsiirto | Yhteinen OSC/UDP, salaamaton luotetussa IOT-verkossa |
| Dokumentaatio | Kuvaa toteutunutta toiminnallisuutta |
| Laajennettavuus | Rakenteellinen, ei sovelluskohtainen |

## Definition of Done

```text
USB
└── Detect
    └── Configure
        └── Bind
            └── Compose
                └── Push to node
                    └── AIGMos Embedded
                        └── ONLINE
```

Ensimmäinen hyväksytty toteutus on ESP8266:lla toimiva AQM-node, joka on provisioitu kokonaan Node Managerilla ja jonka mittausdata näkyy nykyisessä dashboardissa. Nykyinen Arduino-pohjainen firmware on kehitysmateriaalia, ei valmis AIGMos Embedded -toteutus. Nykyistä C6-nodea ei muuteta ennen ESP8266:n hyväksyntää.
