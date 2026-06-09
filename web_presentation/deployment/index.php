<?php
$cfg = require __DIR__ . '/config.php';
session_name($cfg['session_name']);
session_set_cookie_params($cfg['session_lifetime']);
session_start();

if (empty($_SESSION['auth'])) {
    header('Location: login.php');
    exit;
}
?><!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>OceanPulse Deployment Panel</title>
<link rel="stylesheet" href="assets/app.css?v=3">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head>
<body>
<header class="top">
    <div class="brand">
        <span class="logo">🌊</span>
        <strong data-i18n="app.title">OceanPulse — Deployment Panel</strong>
        <span class="badge" data-i18n="app.badge">INTERNAL</span>
    </div>
    <div class="controls">
        <span id="current-user" class="user-chip" title="Signed in as">👤 <?= htmlspecialchars($_SESSION['user'] ?? '') ?></span>
        <button id="history-btn" class="btn btn-ghost" data-i18n="btn.history">History</button>
        <button id="lang-toggle" class="lang-btn" title="Switch language">🇬🇧 EN</button>
        <button id="download-btn" class="btn btn-ghost" data-i18n="btn.download">⬇ JSON</button>
        <a href="logout.php" class="btn btn-ghost" data-i18n="btn.logout">Logout</a>
    </div>
</header>

<nav class="tabs">
    <button class="tab active" data-tab="roadmap" data-i18n="tab.roadmap">Roadmap</button>
    <button class="tab" data-tab="schematic" data-i18n="tab.schematic">Schematic</button>
    <button class="tab" data-tab="shopping" data-i18n="tab.shopping">Shopping List</button>
</nav>

<main>
    <section id="tab-roadmap" class="panel active">
        <div class="roadmap-header">
            <h1 id="roadmap-title" data-i18n="roadmap.title">Deployment Roadmap v3.0</h1>
            <p class="muted" data-i18n="roadmap.sub">Top-to-Bottom Assembly · HDG Frame Swap Strategy</p>
            <div class="progress-summary" id="progress-summary"></div>
        </div>
        <div id="milestones"></div>
        <button id="add-milestone" class="btn btn-primary" data-i18n="btn.add_milestone">+ Milestone</button>
    </section>

    <section id="tab-schematic" class="panel">
        <h1 data-i18n="schem.title">System Wiring Schematic</h1>
        <p class="muted" data-i18n="schem.hint">Node labels are technical identifiers (not translated). Click "Edit source" to modify.</p>
        <div class="schematic-controls">
            <button id="edit-schem" class="btn btn-ghost" data-i18n="btn.edit_source">✎ Edit source</button>
            <button id="save-schem" class="btn btn-primary hidden" data-i18n="btn.save">Save</button>
            <button id="cancel-schem" class="btn btn-ghost hidden" data-i18n="btn.cancel">Cancel</button>
        </div>
        <div id="schem-render" class="mermaid-wrap"></div>
        <textarea id="schem-source" class="hidden" rows="30" spellcheck="false"></textarea>
    </section>

    <section id="tab-shopping" class="panel">
        <h1 data-i18n="shop.title">Shopping List</h1>
        <div class="shop-filters">
            <label><span data-i18n="shop.filter_task">Filter by task:</span>
                <select id="shop-filter-task"><option value="">—</option></select>
            </label>
            <label><span data-i18n="shop.filter_status">Status:</span>
                <select id="shop-filter-status">
                    <option value="">—</option>
                    <option value="needed">needed</option>
                    <option value="ordered">ordered</option>
                    <option value="in_hand">in hand</option>
                    <option value="installed">installed</option>
                </select>
            </label>
            <button id="add-item" class="btn btn-primary" data-i18n="btn.add_item">+ Item</button>
        </div>
        <table class="shop-table">
            <thead>
                <tr>
                    <th data-i18n="shop.col_item">Item</th>
                    <th data-i18n="shop.col_qty">Qty</th>
                    <th data-i18n="shop.col_cost">€</th>
                    <th data-i18n="shop.col_vendor">Vendor</th>
                    <th data-i18n="shop.col_linked">Linked Task</th>
                    <th data-i18n="shop.col_status">Status</th>
                    <th data-i18n="shop.col_actions"></th>
                </tr>
            </thead>
            <tbody id="shop-tbody"></tbody>
        </table>
    </section>
</main>

<div id="toast" class="toast"></div>

<!-- Task edit modal -->
<div id="modal" class="modal hidden">
    <div class="modal-card">
        <h2 id="modal-title">Edit</h2>
        <div id="modal-body"></div>
        <div class="modal-actions">
            <button id="modal-cancel" class="btn btn-ghost" data-i18n="btn.cancel">Cancel</button>
            <button id="modal-save" class="btn btn-primary" data-i18n="btn.save">Save</button>
        </div>
    </div>
</div>

<script src="assets/app.js?v=3"></script>
</body>
</html>
