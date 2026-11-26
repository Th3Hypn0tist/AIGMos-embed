<?php
// Copy to config.php, outside your webserver's document root.
return [
    'dsn' => 'pgsql:host=127.0.0.1;port=5432;dbname=AirQualityMon',
    'db_user' => 'aqm_ingest',
    'db_password' => 'REPLACE_WITH_POSTGRES_PASSWORD',
    // Same secret as INGEST_SECRET in the ESP32 firmware. Random 32+ characters.
    'hmac_secret' => 'CHANGE_ME_TO_32_PLUS_RANDOM_CHARACTERS',
];