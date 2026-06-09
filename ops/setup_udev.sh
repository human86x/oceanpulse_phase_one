#!/bin/bash
# setup_udev.sh — Deploy OceanPulse persistent serial symlinks (SPEC-023)
# Creates /dev/op-mega and /dev/op-lora using kernel/attr matching.

set -e

RULE_FILE="/etc/udev/rules.d/99-oceanpulse.rules"
RULES="# OceanPulse SPEC-023: Persistent Serial Symlinks
# 2026-05-16: removed CH340 from op-lora — DO sensor's FIT0737 RS485 dongle
# uses 1a86:7523, same as a hypothetical CH340-LoRa variant. The collision
# was silently routing AT commands to the DO Modbus dongle and Modbus
# queries to the LoRa radio. Now: CP2102N => op-lora, CH340 => op-do.
# 2026-05-20: Health Pi gained a second CH340 (1a86:7523) — Joy-IT SBC-TTL
# pen wired to Victron MPPT 75|15 VE.Direct. Same VID:PID as the DO sensor's
# RS485 dongle. Disambiguated by USB port path (1-1.3 on Health Pi). CH340
# lacks a unique serial attr so port-pin is the only option short of an FTDI
# swap. Label the physical port 'VE.Direct only'. The port-pinned rule must
# come BEFORE the generic op-do rule so udev matches it first on Health Pi.
# 2026-05-21: SPEC-036 — Health Pi gained a THIRD CH340 (1a86:7523) — Joy-IT
# SBC-TTL pen wired to Victron SmartShunt 300A VE.Direct on USB port 1-1.1.3.
# Both VE.Direct pens need 3V3 jumper position (BMV-class is 3V3; MPPT is 5V
# but tolerant). Same port-pinning approach as op-vedirect.
# TODO: once Main is reachable, port-pin op-do too — currently generic, any
# future second CH340 on Main would race-claim /dev/op-do.
KERNEL==\"ttyACM*\", ATTRS{idVendor}==\"2341\", ATTRS{idProduct}==\"0042\", SYMLINK+=\"op-mega\"
KERNEL==\"ttyUSB*\", ATTRS{idVendor}==\"10c4\", ATTRS{idProduct}==\"ea60\", SYMLINK+=\"op-lora\"
KERNEL==\"ttyUSB*\", ATTRS{idVendor}==\"1a86\", ATTRS{idProduct}==\"7523\", KERNELS==\"1-1.3\", SYMLINK+=\"op-vedirect\"
KERNEL==\"ttyUSB*\", ATTRS{idVendor}==\"1a86\", ATTRS{idProduct}==\"7523\", KERNELS==\"1-1.1.3\", SYMLINK+=\"op-shunt\"
KERNEL==\"ttyUSB*\", ATTRS{idVendor}==\"1a86\", ATTRS{idProduct}==\"7523\", SYMLINK+=\"op-do\"
"

echo "=== Deploying udev rules for OceanPulse (SPEC-023) ==="

echo "$RULES" | sudo tee "$RULE_FILE" > /dev/null
sudo udevadm control --reload-rules
# Use --action=change so already-plugged devices re-evaluate rules
# (default 'add' trigger only fires for newly-added devices).
sudo udevadm trigger --action=change --subsystem-match=tty
sudo udevadm trigger --action=change --subsystem-match=usb
# Settle briefly so symlinks are in place before we ls.
sudo udevadm settle --timeout=5

echo "=== Success: Symlinks created (if devices connected) ==="
ls -l /dev/op-* || echo "Warning: Devices not detected. Check physical connection."
