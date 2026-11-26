# AIGMos Embedded – jäljellä oleva toteutusjärjestys

Lähtötilanne: 661fcb3. Ensimmäinen Node Manager -tekstivalikko, runtime-luonnos, taulugeneraattori ja BMP180/DHT11-ajurit ovat repositoryssa. Testiajoja ei ole vahvistettu. Tämä on priorisoitu jäljellä oleva työ, ei uusi arkkitehtuurimääritys. Kattava alkuperäinen työlista: [EMBEDDED_TASKS.md](EMBEDDED_TASKS.md).

## P0 – Node Managerin provisiointi (aloita tästä)
- [ ] Aja nykyiset Python- ja C99-host-testit; korjaa havaitut virheet. Älä merkitse hyväksytyksi ilman testitulosta.
- [ ] Erota LMTS:n TUI-primitiivit yhteiseen AIGMos Paneliin; Node Manager geneerisenä UserModulena.
- [ ] USB-porttien live-listaus ja laitteen valinta. (Valinta ja uudelleenlistaus Identify-valikossa lisätty; jatkuva päivitys avoinna.)
- [ ] MCU-, MAC- ja flash-kokoluokan tunnistus bootloaderin kautta ilman firmwarekirjoitusta; toolchain-tunnistus. (Esptool 4.x -rajapinta ja PATH-tunnistus lisätty, mock-testit ja fyysinen testi ajamatta.)
- [ ] Pysyvä node-identiteetti, laiteinventaario ja valittu vs aktiivinen kompositio. (Tunnistetun MAC:n ja flash-koon tallennus lisätty; aktiivinen versio vasta deployment-verifioinnissa.)
- [ ] ESP8266:n probe-firmwaren build ja eksplisiittinen Detect hardware; ei automaattista flashausta. Huomioi olemassa oleva firmware ja palautus. (Probe plan ja C-taulut generoidaan; SDK-build/flash puuttuvat.)
- [ ] Sallitut I²C-probet ja GPIO-inventaario; epävarmat sensorit merkitään ehdokkaiksi, ei varmoiksi havainnoiksi. (I2C scan -primitiivi ja inventory JSON-import lisätty; GPIO-luku/serial-report ja testit avoinna.)
- [ ] Hardware-, Modules- ja Pin Mapper -näkymät: lisää/poista/vaihda, pinout, capabilities, reserved/strap, jaetut väylät, osoite- ja pinnikonfliktit, live-testi. (Tekstipohjainen editori, ehdokkaat, pin-taulukko ja versionoitu validointi lisätty; live-testi ja lopullinen Panel avoinna.)
- [ ] Network-näkymä: DHCP/auto/static, Wi-Fi-konfiguraatio, USB- ja verkkoinventaarion yhdistys, osoitekonfliktit ja saavutettavuus; tunnukset paikallisesti eikä Gitiin. (Network panel, erillinen credential-tiedosto, neighbor cache, ICMP ja OSC-kohde lisätty; testit ja target-integraatio avoinna.)
- [ ] Säilytä C6:n .50-varaus; ESP8266 .51; auto 50 + node_index. Älä muuta C6:n firmwarea. (Uudet rekisterit varaavat index 0:n C6:lle; vanhojen rekisterien migraatio ja todellinen C6-MAC vahvistamatta.)
- [ ] State-, Commands-, Trigger-, Event-, Runner- ja Composition-näkymät sekä versioiden valinta/palautus. (Composition Manager -näkymä, JSON-osioeditori, luonnosvalidointi ja historia/palautus lisätty; erilliset rekisterieditorit, runtime-validointi ja testiajo avoinna.)
- [ ] Build/deployment/monitor-näkymät ja CS-integraatio; estä Push to node kun build ei ole valmis. (Build/deployment-valikko, host compile, plan-hash/stale-status ja fail-closed Push lisätty; target/monitor/CS ja testiajo avoinna.)

## P1 – ESP8266:n ajettava kompositio
- [ ] Ulkoinen ESP8266 SDK -adapteri: GPIO, I²C, monotonic timer/delay, UART, Wi-Fi, UDP; flash-rajapinnat tarpeen mukaan. (Valinnainen ulkoinen Arduino-core adapteri lisätty GPIO/I2C/UART/timer/delay/UDP:lle; Wi-Fi setup, SDK build ja testit avoinna. Ei pakollinen runtime-riippuvuus.)
- [ ] Tarkista D1 mini -pinout ja sähköiset rajoitteet; BMP180 GPIO4/5, osoite 0x77; DHT11 GPIO14.
- [ ] Vahvista AIGMos 1.9:n TER- ja CS-semantiikka (condition, aktivointi/resetointi, run, komentojen järjestys ja virheet).
- [ ] Ajastettu Trigger, Eventin komentolista ja CS:n kautta käynnistettävä Runner; testaa ettei aktiivinen Trigger tai Runner aiheuta toistuvaa tahatonta ajoa.
- [ ] Muuttujaviittaukset, State-viittaukset ja rakenteinen data CS:n argumentteina; säilytä geneerinen State ja erilliset #I / #OSC.
- [ ] Sensorien read-komentojen rekisteröinti ja moduulikohtaiset kontekstit; virheessä NULL.
- [ ] Geneerinen osc.out, vastaanottajan resolvointi ja OSC-serialisointi; varmista yhteensopivuus nykyisen AQM wire-SSOT:n kanssa. Ei PostgreSQL-ajuria nodeen.
- [ ] Moduuli- ja adapterilähteiden valinta, pin bindings, init, entry point, scheduler ja generoidut rekisterit. (Valittujen moduulien lähteet/headerit mukana host build planissa.)
- [ ] Build-kohtaiset HardCore/Core/UM-valinnat, lähdehashit, käännös, linkitys ja flashattava artifact; build_ready vain onnistuneen todellisen buildin jälkeen.
- [ ] AQM-komposition pending_ter muutetaan ajettavaksi; ei sovelluskohtaista logiikkaa HardCoressa tai Node Managerissa.
- [ ] Eksplisiittinen Push to node, build-log, flash-verifiointi, komposition tunniste, palautus ja aktiivisen version päivitys vasta hyväksytyn verifioinnin jälkeen.

## P2 – AQM end-to-end
- [ ] AQM-kompositio: $master=192.168.0.18, UDP/9000, Trigger interval 5000 ms → Event: run aqm_sample → Runner: um.bmp.read; um.dht.read; osc.out $master #I:sensorit:data.
- [ ] Muodosta #I:sensorit:data nykyisen AQM:n mittauskentistä; säilytä BMP primäärilämpötilana, puuttuvat sensorit NULL nykyisen sopimuksen mukaisesti.
- [ ] Vahvista AIGMos 1.9 System Expose -sopimus; geneerinen OSC IN → #OSC, ei AQM- tai DB-logiikkaa Exposessa.
- [ ] Python-backendin AQM UserModule: #OSC → nykyiset PostgreSQL-funktiot, AirQualityMon; säilytä wire-version ja ingest-identiteetin yhteensopivuus.
- [ ] Säilytä kalibrointi, lasermittaus, nykyinen tietokantaskeema ja dashboard; varmista myös kalibroinnin kulku.
- [ ] Backendin dekoodaus-, virhe-, duplikaatti- ja DB-integraatiotestit.
- [ ] Fyysinen ESP8266-testi: sensorit, ajoitus, Wi-Fi-kuormitus, OSC, DB, dashboard; vertaa legacy C6:n rinnalla.
- [ ] Pitkäkestoinen testi, verkkokatkos, uudelleenkäynnistys, puuttuva sensori, muistinkäyttö ja ajoitus. Hyväksy ESP8266 ennen C6-migraatiota.

## P3 – Yleistys ja viimeistely
- [ ] ESP32-C6-adapteri ja nykyiset BMP280, RH/T (HDC1080/Si7021 tunnistus), CCS811; varmista todelliset pinnit ja sensorit ennen migraatiota.
- [ ] C6:n provisiointi vasta P2-hyväksynnän jälkeen; ESP32-S3-adapterivalmius, ei pakollista toteutusta.
- [ ] Muut alustarajapinnat ADC/PWM/SPI/flash ja laajennettava Input/Output/Communication/UserModule-rekisteri.
- [ ] ExpressionEngine ja Expression Registry: tarkasta 1.9-syntaksi; Expression Condition != Trigger Condition; valinnainen ja TER:stä riippumaton.
- [ ] Rutiinit, valinnainen AccessCore ja fail-closed valtuutus; build-kohtainen karsinta sekä integraatiotestit.
- [ ] SSOT- ja alustariippumattomuusvalidointi; include- ja linkitysauditointi, AIGMos-runtime 0 ulkoista riippuvuutta.
- [ ] Asennustyökalu, toolchain/adapteri/UM-riippuvuuksien asennus, käyttöohje, laajennusohje ja PROTOCOL.md vain toteutuneesta toiminnasta.

## Hyväksyntäportti
ESP8266 provisioidaan kokonaan Node Managerilla ja mittaus näkyy nykyisessä dashboardissa 5 sekunnin välein. Detect hardware ja Push to node ovat erillisiä eksplisiittisiä toimintoja. C6:n tuotantofirmware säilyy koskemattomana siihen asti.

Priorisointi on toteutusjärjestysehdotus: P0:n probe ja P1:n adapteri/toolchain etenevät riippuvuuksiensa mukaan; P3:n valinnaiset komponentit eivät estä ensimmäistä AQM-nodea. Päivitä molemmat työlistat toteutuscommitien yhteydessä.
