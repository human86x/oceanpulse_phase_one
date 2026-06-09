<?php
$cfg = require __DIR__ . '/config.php';
session_name($cfg['session_name']);
session_start();

header('Content-Type: application/json');

if (empty($_SESSION['auth'])) {
    http_response_code(401);
    echo json_encode(['error' => 'unauthorized']);
    exit;
}

$dataFile  = $cfg['data_file'];
$backupDir = $cfg['backup_dir'];
$user      = $_SESSION['user'] ?? 'unknown';
@mkdir($backupDir, 0755, true);

function read_data($file) {
    if (!file_exists($file)) return null;
    $fh = fopen($file, 'r');
    flock($fh, LOCK_SH);
    $raw = stream_get_contents($fh);
    flock($fh, LOCK_UN);
    fclose($fh);
    return json_decode($raw, true);
}

function write_data($file, $backupDir, $maxBackups, $data) {
    if (file_exists($file)) {
        $ts = gmdate('Ymd_His');
        @copy($file, $backupDir . "roadmap_v3_{$ts}.json");
        $files = glob($backupDir . 'roadmap_v3_*.json');
        if ($files && count($files) > $maxBackups) {
            sort($files);
            foreach (array_slice($files, 0, count($files) - $maxBackups) as $old) @unlink($old);
        }
    }
    $tmp = $file . '.tmp';
    $fh = fopen($tmp, 'w');
    flock($fh, LOCK_EX);
    fwrite($fh, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    fflush($fh);
    flock($fh, LOCK_UN);
    fclose($fh);
    if (!rename($tmp, $file)) { @unlink($tmp); return false; }
    return true;
}

function task_fields() { return ['title_en','title_ru','owner','status','notes']; }
function item_fields() { return ['item_en','item_ru','quantity','unit_cost_eur','vendor_url','status','linked_task_id','notes']; }
function milestone_fields() { return ['title_en','title_ru','description_en','description_ru','owner']; }

function differs($a, $b, $fields) {
    foreach ($fields as $f) {
        if (($a[$f] ?? null) !== ($b[$f] ?? null)) return true;
    }
    return false;
}

function index_by_id($list) {
    $out = [];
    foreach ($list as $x) if (isset($x['id'])) $out[$x['id']] = $x;
    return $out;
}

function attribute_changes($old, &$new, $user, $now) {
    $changes = [];

    // --- Milestones + tasks ---
    $oldMs = index_by_id($old['milestones'] ?? []);
    $oldTaskMap = [];
    foreach (($old['milestones'] ?? []) as $m) {
        foreach (($m['tasks'] ?? []) as $t) {
            if (isset($t['id'])) $oldTaskMap[$t['id']] = $t;
        }
    }

    $seenMs = [];
    $seenTasks = [];

    foreach ($new['milestones'] as $mi => $m) {
        $mid = $m['id'] ?? null;
        if ($mid) {
            $seenMs[$mid] = true;
            $oldM = $oldMs[$mid] ?? null;
            if (!$oldM) {
                $changes[] = "milestone:$mid:added";
                $new['milestones'][$mi]['updated_by'] = $user;
                $new['milestones'][$mi]['updated_at'] = $now;
            } elseif (differs($oldM, $m, milestone_fields())) {
                $changes[] = "milestone:$mid";
                $new['milestones'][$mi]['updated_by'] = $user;
                $new['milestones'][$mi]['updated_at'] = $now;
            } else {
                if (isset($oldM['updated_by'])) $new['milestones'][$mi]['updated_by'] = $oldM['updated_by'];
                if (isset($oldM['updated_at'])) $new['milestones'][$mi]['updated_at'] = $oldM['updated_at'];
            }
        }
        foreach (($m['tasks'] ?? []) as $ti => $t) {
            $tid = $t['id'] ?? null;
            if (!$tid) continue;
            $seenTasks[$tid] = true;
            $oldT = $oldTaskMap[$tid] ?? null;
            if (!$oldT) {
                $changes[] = "task:$tid:added";
                $new['milestones'][$mi]['tasks'][$ti]['updated_by'] = $user;
                $new['milestones'][$mi]['tasks'][$ti]['updated_at'] = $now;
            } elseif (differs($oldT, $t, task_fields())) {
                $changes[] = "task:$tid";
                $new['milestones'][$mi]['tasks'][$ti]['updated_by'] = $user;
                $new['milestones'][$mi]['tasks'][$ti]['updated_at'] = $now;
            } else {
                if (isset($oldT['updated_by'])) $new['milestones'][$mi]['tasks'][$ti]['updated_by'] = $oldT['updated_by'];
                if (isset($oldT['updated_at'])) $new['milestones'][$mi]['tasks'][$ti]['updated_at'] = $oldT['updated_at'];
            }
        }
    }
    foreach ($oldMs as $id => $_) if (empty($seenMs[$id])) $changes[] = "milestone:$id:deleted";
    foreach ($oldTaskMap as $id => $_) if (empty($seenTasks[$id])) $changes[] = "task:$id:deleted";

    // --- Shopping list ---
    $oldItems = index_by_id($old['shopping_list'] ?? []);
    $seenItems = [];
    foreach (($new['shopping_list'] ?? []) as $i => $it) {
        $id = $it['id'] ?? null;
        if (!$id) continue;
        $seenItems[$id] = true;
        $oldIt = $oldItems[$id] ?? null;
        if (!$oldIt) {
            $changes[] = "item:$id:added";
            $new['shopping_list'][$i]['updated_by'] = $user;
            $new['shopping_list'][$i]['updated_at'] = $now;
        } elseif (differs($oldIt, $it, item_fields())) {
            $changes[] = "item:$id";
            $new['shopping_list'][$i]['updated_by'] = $user;
            $new['shopping_list'][$i]['updated_at'] = $now;
        } else {
            if (isset($oldIt['updated_by'])) $new['shopping_list'][$i]['updated_by'] = $oldIt['updated_by'];
            if (isset($oldIt['updated_at'])) $new['shopping_list'][$i]['updated_at'] = $oldIt['updated_at'];
        }
    }
    foreach ($oldItems as $id => $_) if (empty($seenItems[$id])) $changes[] = "item:$id:deleted";

    // --- Schematic ---
    $oldSchem = $old['schematic']['mermaid_source'] ?? '';
    $newSchem = $new['schematic']['mermaid_source'] ?? '';
    if ($oldSchem !== $newSchem) {
        $changes[] = "schematic";
        $new['schematic']['updated_by'] = $user;
        $new['schematic']['updated_at'] = $now;
    } else {
        if (isset($old['schematic']['updated_by'])) $new['schematic']['updated_by'] = $old['schematic']['updated_by'];
        if (isset($old['schematic']['updated_at'])) $new['schematic']['updated_at'] = $old['schematic']['updated_at'];
    }

    return $changes;
}

$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'GET') {
    $data = read_data($dataFile);
    if ($data === null) {
        http_response_code(404);
        echo json_encode(['error' => 'data_not_found']);
        exit;
    }
    $data['_session'] = ['user' => $user];
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

if ($method === 'POST') {
    $raw = file_get_contents('php://input');
    $new = json_decode($raw, true);
    if (!is_array($new) || !isset($new['milestones'])) {
        http_response_code(400);
        echo json_encode(['error' => 'invalid_payload']);
        exit;
    }
    unset($new['_session']);
    $old = read_data($dataFile) ?? [];
    $now = gmdate('c');

    $changes = attribute_changes($old, $new, $user, $now);
    $new['updated_at'] = $now;
    $new['updated_by'] = $user;

    if (!empty($changes)) {
        $new['audit_log'] = $new['audit_log'] ?? ($old['audit_log'] ?? []);
        $new['audit_log'][] = ['ts' => $now, 'user' => $user, 'changes' => $changes];
        $maxA = $cfg['max_audit_log'] ?? 200;
        if (count($new['audit_log']) > $maxA) {
            $new['audit_log'] = array_slice($new['audit_log'], -$maxA);
        }
    } else {
        $new['audit_log'] = $old['audit_log'] ?? [];
    }

    if (!write_data($dataFile, $backupDir, $cfg['max_backups'], $new)) {
        http_response_code(500);
        echo json_encode(['error' => 'write_failed']);
        exit;
    }
    echo json_encode(['status' => 'ok', 'updated_at' => $now, 'changes' => $changes, 'user' => $user]);
    exit;
}

http_response_code(405);
echo json_encode(['error' => 'method_not_allowed']);
