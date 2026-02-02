<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST');
header('Access-Control-Allow-Headers: Content-Type');

$filename = 'bom_config.json';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if ($data) {
        if (file_put_contents($filename, json_encode($data, JSON_PRETTY_PRINT))) {
            echo json_encode(['status' => 'success', 'message' => 'Configuration saved permanently']);
        } else {
            http_response_code(500);
            echo json_encode(['status' => 'error', 'message' => 'Failed to write to file']);
        }
    } else {
        http_response_code(400);
        echo json_encode(['status' => 'error', 'message' => 'Invalid JSON input']);
    }
} else {
    // GET request
    if (file_exists($filename)) {
        echo file_get_contents($filename);
    } else {
        echo json_encode(['status' => 'new', 'message' => 'No configuration found, using defaults']);
    }
}
?>