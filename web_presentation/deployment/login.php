<?php
$cfg = require __DIR__ . '/config.php';
session_name($cfg['session_name']);
session_set_cookie_params($cfg['session_lifetime']);
session_start();

$error = '';
$selected = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $user = $_POST['user'] ?? '';
    $pw   = $_POST['password'] ?? '';
    $selected = $user;
    $hash = hash('sha256', $pw);
    if (in_array($user, $cfg['users'], true) && hash_equals($cfg['password_sha256'], $hash)) {
        $_SESSION['auth']     = true;
        $_SESSION['user']     = $user;
        $_SESSION['login_ts'] = time();
        header('Location: index.php');
        exit;
    } else {
        $error = 'Invalid user or password.';
        usleep(600000);
    }
}
?><!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>OceanPulse · Deployment Panel · Login</title>
<link rel="stylesheet" href="assets/app.css?v=3">
</head>
<body class="login-body">
<div class="login-card">
    <div class="login-logo">🌊</div>
    <h1>Deployment Panel</h1>
    <p class="muted">OceanPulse · Internal Team Access</p>
    <?php if ($error): ?>
        <div class="login-error"><?= htmlspecialchars($error) ?></div>
    <?php endif; ?>
    <form method="POST" autocomplete="off">
        <select name="user" required>
            <option value="">— Who are you? —</option>
            <?php foreach ($cfg['users'] as $u): ?>
                <option value="<?= htmlspecialchars($u) ?>"<?= $u===$selected?' selected':'' ?>><?= htmlspecialchars($u) ?></option>
            <?php endforeach; ?>
        </select>
        <input type="password" name="password" placeholder="Shared password" required>
        <button type="submit" class="btn btn-primary btn-block">Sign in</button>
    </form>
</div>
</body>
</html>
