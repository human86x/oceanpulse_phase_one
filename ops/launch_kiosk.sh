#!/bin/bash
# OceanPulse Headless Kiosk Launcher
# SPEC-021 Compliant

# Chromium App Flags
FLAGS="--app=http://localhost:5000
       --start-maximized
       --no-first-run
       --noerrdialogs
       --disable-infobars
       --autoplay-policy=no-user-gesture-required
       --check-for-update-interval=31536000
       --disable-pinch
       --disable-features=TranslateUI
       --ozone-platform=wayland
       --enable-features=UseOzonePlatform"

# Wayland/wlroots environment
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export WLR_BACKENDS=drm
export WLR_RENDERER=pixman
export WLR_LIBINPUT_NO_DEVICES=0
# Cursor: pixman needs software cursor; Adwaita theme is installed
export WLR_NO_HARDWARE_CURSORS=1
export XCURSOR_THEME=Adwaita
export XCURSOR_SIZE=24
export XCURSOR_PATH=/usr/share/icons
# Suppress dbus errors from headless service
export DBUS_SESSION_BUS_ADDRESS=/dev/null

echo "Launching Cage kiosk..."
exec cage -- chromium-browser $FLAGS
