<?php
// SPEC-032 Internal Roadmap Panel — configuration
// Users share one password (for now). Attribution is by selected username.
// To change the password:
//   python3 -c 'import hashlib; print(hashlib.sha256(b"NEW_PASSWORD").hexdigest())'
// then replace password_sha256 below and re-deploy.

return [
    'users'            => ['Gee', 'Paul', 'Victor'],
    'password_sha256'  => '664d580b830fb153752bb6d16c385546c2b0b425658297d5cf33620259856a9b',
    'data_file'        => __DIR__ . '/data/roadmap_v3.json',
    'backup_dir'       => __DIR__ . '/data/backups/',
    'max_backups'      => 50,
    'max_audit_log'    => 200,
    'session_name'     => 'op_deploy_panel',
    'session_lifetime' => 60 * 60 * 12, // 12 hours
];
