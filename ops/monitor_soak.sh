#!/bin/bash
# OceanPulse Soak Test Monitor (SPEC-029)
# Version: 1.0

DB_PATH="_cortex/ads/telemetry.db"
LOG_FILE="_cortex/ads/soak_monitor.log"
DURATION_HOURS=48

echo "--- OceanPulse Soak Test Monitor Started: $(date) ---" | tee -a $LOG_FILE
echo "Monitoring $DB_PATH for $DURATION_HOURS hours..." | tee -a $LOG_FILE

while true; do
    echo "--- Stats at $(date) ---" >> $LOG_FILE
    
    # 1. Check Telemetry Counts
    python3 -c "import sqlite3, json, time; 
conn = sqlite3.connect('$DB_PATH'); 
c = conn.cursor(); 
now = time.time();
since = now - 3600; # Last hour
c.execute('SELECT target, COUNT(*) FROM telemetry WHERE ts > ? GROUP BY target', (since,));
rows = c.fetchall();
print(f'Last Hour Packet Counts: {dict(rows)}');

c.execute('SELECT target, MAX(ts) FROM telemetry GROUP BY target');
stale = c.fetchall();
for t, ts in stale:
    age = now - ts;
    status = 'OK' if age < 60 else 'STALE';
    print(f'Target {t:10} | Last Seen: {int(age):4}s ago | Status: {status}');
" >> $LOG_FILE

    # 2. Check for Reboots (ADS events)
    grep -i "session_start" _cortex/ads/events.jsonl | tail -n 5 >> $LOG_FILE

    # 3. Check Persistence
    DB_SIZE=$(ls -lh $DB_PATH | awk '{print $5}')
    echo "Telemetry DB Size: $DB_SIZE" >> $LOG_FILE

    sleep 300 # Monitor every 5 minutes
done
