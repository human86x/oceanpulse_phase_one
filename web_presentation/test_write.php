<?php
$file = 'test_write.json';
$data = ['test' => 'data'];
if (file_put_contents($file, json_encode($data))) {
    echo json_encode(['status' => 'success', 'message' => 'Write successful']);
} else {
    echo json_encode(['status' => 'error', 'message' => 'Write failed']);
}
?>