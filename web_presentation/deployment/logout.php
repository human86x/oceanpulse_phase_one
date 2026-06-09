<?php
$cfg = require __DIR__ . '/config.php';
session_name($cfg['session_name']);
session_start();
$_SESSION = [];
session_destroy();
header('Location: login.php');
exit;
