<?php
$data = ['status' => 'success', 'message' => 'PHP is working'];
header('Content-Type: application/json');
echo json_encode($data);
?>