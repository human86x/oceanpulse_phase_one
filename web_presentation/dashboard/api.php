<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// All data is pushed via FTP (telemetry.json, snapshot.jpg, snapshot_meta.json)
// This endpoint only serves GET requests — reads files from disk

$filename = 'telemetry.json';

if (!file_exists($filename)) {
    echo json_encode([
        "main" => ["online" => false, "last_update" => 0],
        "health" => ["online" => false, "last_update" => 0],
        "gateway" => ["online" => false, "last_update" => 0],
        "vision" => ["online" => false, "last_update" => 0]
    ]);
    exit;
}

$current = json_decode(file_get_contents($filename), true);

// Merge vision snapshot if FTP-uploaded file exists and is fresh (<120s)
$now = time();
$snapshot_file = 'snapshot.jpg';
$snapshot_meta = 'snapshot_meta.json';
if (file_exists($snapshot_file) && file_exists($snapshot_meta)) {
    clearstatcache(true, $snapshot_file);
    $meta = json_decode(file_get_contents($snapshot_meta), true);
    $file_age = $now - filemtime($snapshot_file);
    if ($file_age <= 120) {
        $current['vision']['snapshot_url'] = 'snapshot.jpg?t=' . filemtime($snapshot_file);
        $current['vision']['snapshot_time'] = $meta['timestamp'];
    }
}

echo json_encode($current);
?>
