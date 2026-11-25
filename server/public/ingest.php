<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function reply(int $status, array $payload): never {
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: POST');
    reply(405, ['error' => 'POST required']);
}

$config = require __DIR__ . '/../private/config.php';
if (!is_array($config) ||
    ($config['hmac_secret'] ?? '') === 'CHANGE_ME_TO_32_PLUS_RANDOM_CHARACTERS' ||
    strlen((string)($config['hmac_secret'] ?? '')) < 32) {
    reply(503, ['error' => 'Endpoint not configured']);
}

// Reject very large/empty requests before JSON parsing or DB work.
if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 2048) reply(413, ['error' => 'Too large']);
$body = file_get_contents('php://input', false, null, 0, 2049);
if ($body === false || $body === '' || strlen($body) > 2048) reply(400, ['error' => 'Invalid request body']);

$provided = (string)($_SERVER['HTTP_X_AQM_SIGNATURE'] ?? '');
$expected = hash_hmac('sha256', $body, (string)$config['hmac_secret']);
if (!preg_match('/\A[a-fA-F0-9]{64}\z/D', $provided) || !hash_equals($expected, strtolower($provided))) {
    reply(401, ['error' => 'Invalid signature']);
}

try {
    $d = json_decode($body, true, 32, JSON_THROW_ON_ERROR);
} catch (JsonException $e) {
    reply(400, ['error' => 'Invalid JSON']);
}
if (!is_array($d)) reply(400, ['error' => 'JSON object required']);

function requiredInt(array $d, string $key, int $min, int $max): int {
    $v = $d[$key] ?? null;
    if (!is_int($v) || $v < $min || $v > $max) throw new InvalidArgumentException($key);
    return $v;
}
function optionalInt(array $d, string $key, int $min, int $max): ?int {
    $v = $d[$key] ?? null;
    if ($v === null) return null;
    if (!is_int($v) || $v < $min || $v > $max) throw new InvalidArgumentException($key);
    return $v;
}
function optionalFloat(array $d, string $key, float $min, float $max): ?float {
    $v = $d[$key] ?? null;
    if ($v === null) return null;
    if ((!is_int($v) && !is_float($v)) || !is_finite((float)$v) || $v < $min || $v > $max) {
        throw new InvalidArgumentException($key);
    }
    return (float)$v;
}
try {
    $device = $d['device_id'] ?? null;
    $boot = $d['boot_id'] ?? null;
    $chip = $d['humidity_chip'] ?? 'unknown';
    $diag = $d['humidity_diag'] ?? '';
    if (!is_string($device) || !preg_match('/\A[a-zA-Z0-9_-]{1,48}\z/D', $device)) throw new InvalidArgumentException('device_id');
    if (!is_string($boot) || !preg_match('/\A[a-f0-9]{16}\z/D', $boot)) throw new InvalidArgumentException('boot_id');
    if (!is_string($chip) || !preg_match('/\A[a-zA-Z0-9_-]{1,32}\z/D', $chip)) throw new InvalidArgumentException('humidity_chip');
    if (!is_string($diag) || !preg_match('/\A[a-zA-Z0-9_-]{0,64}\z/D', $diag)) throw new InvalidArgumentException('humidity_diag');
    $warmup = $d['ccs_warming_up'] ?? null;
    if (!is_bool($warmup)) throw new InvalidArgumentException('ccs_warming_up');

    $values = [
        ':device_id'         => $device,
        ':boot_id'           => $boot,
        ':seq'               => requiredInt($d, 'seq', 0, 2147483647),
        ':uptime_ms'         => requiredInt($d, 'uptime_ms', 0, 4294967295),
        ':temperature_c'     => optionalFloat($d, 'temperature_c', -40, 125),
        ':bmp_temperature_c' => optionalFloat($d, 'bmp_temperature_c', -40, 125),
        ':humidity_rh'       => optionalFloat($d, 'humidity_rh', 0, 100),
        ':pressure_hpa'      => optionalFloat($d, 'pressure_hpa', 300, 1200),
        ':eco2_ppm'          => optionalInt($d, 'eco2_ppm', 0, 65535),
        ':tvoc_ppb'          => optionalInt($d, 'tvoc_ppb', 0, 65535),
        ':ccs_warming_up'    => $warmup ? 'true' : 'false',
        ':ccs_error'         => requiredInt($d, 'ccs_error', 0, 255),
        ':humidity_chip'     => $chip,
        ':humidity_diag'     => $diag,
        ':rssi_dbm'          => optionalInt($d, 'rssi_dbm', -127, 0),
    ];
} catch (InvalidArgumentException $e) {
    reply(422, ['error' => 'Invalid field', 'field' => $e->getMessage()]);
}

try {
    $pdo = new PDO((string)$config['dsn'], (string)$config['db_user'], (string)$config['db_password'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_EMULATE_PREPARES => false,
        PDO::ATTR_TIMEOUT => 3,
    ]);
    $sql = 'INSERT INTO aqm.samples (
        device_id, boot_id, seq, uptime_ms,
        temperature_c, bmp_temperature_c, humidity_rh, pressure_hpa,
        eco2_ppm, tvoc_ppb, ccs_warming_up, ccs_error,
        humidity_chip, humidity_diag, rssi_dbm
    ) VALUES (
        :device_id, :boot_id, :seq, :uptime_ms,
        :temperature_c, :bmp_temperature_c, :humidity_rh, :pressure_hpa,
        :eco2_ppm, :tvoc_ppb, :ccs_warming_up, :ccs_error,
        :humidity_chip, :humidity_diag, :rssi_dbm
    ) ON CONFLICT (device_id, boot_id, seq) DO NOTHING RETURNING id';
    $stmt = $pdo->prepare($sql);
    $stmt->execute($values);
    $id = $stmt->fetchColumn();
    reply($id === false ? 200 : 201, [
        'ok' => true,
        'stored' => $id !== false,
        'id' => $id === false ? null : (int)$id,
    ]);
} catch (Throwable $e) {
    error_log('AirQuality ingest error: ' . $e->getMessage());
    reply(500, ['error' => 'Database write failed']);
}