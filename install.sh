#!/bin/bash

# ModeSwitch Plugin Installer for Pwnagotchi
# Repo: https://github.com/keag-dev/ModeSwitch

PLUGIN_URL="https://raw.githubusercontent.com/keag-dev/ModeSwitch/main/mode_switch.py"
# Standard Pwnagotchi custom plugins directory
INSTALL_DIR="/usr/local/share/pwnagotchi/custom-plugins"
# Helper scripts location (in PATH)
SCRIPT_DIR="/usr/local/bin"

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run this script as root (use sudo)."
  exit 1
fi

echo "=== ModeSwitch Plugin Installer ==="

# 1. Install Plugin File
echo "[+] Checking plugin directory..."
if [ ! -d "$INSTALL_DIR" ]; then
    echo "    Directory $INSTALL_DIR not found. Creating it..."
    mkdir -p "$INSTALL_DIR"
fi

echo "[+] Downloading mode_switch.py..."
# Try wget, fall back to curl
if command -v wget >/dev/null 2>&1; then
    wget -q "$PLUGIN_URL" -O "$INSTALL_DIR/mode_switch.py"
elif command -v curl >/dev/null 2>&1; then
    curl -s "$PLUGIN_URL" -o "$INSTALL_DIR/mode_switch.py"
else
    echo "Error: Neither wget nor curl found. Cannot download plugin."
    exit 1
fi

# Verify download
if [ ! -f "$INSTALL_DIR/mode_switch.py" ]; then
    echo "Error: Download failed. Check your internet connection or URL."
    exit 1
fi
echo "    Installed to: $INSTALL_DIR/mode_switch.py"

# 2. Create Helper Scripts
echo "[+] Creating helper scripts in $SCRIPT_DIR..."

create_script() {
    local name=$1
    local trigger_file=$2
    local message=$3
    local path="$SCRIPT_DIR/$name"
    
    echo "#!/bin/bash" > "$path"
    echo "if touch \"$trigger_file\" 2>/dev/null; then" >> "$path"
    echo "    echo \"[+] $message\"" >> "$path"
    echo "else" >> "$path"
    echo "    echo \"[!] Error: Could not write to $trigger_file. Are you root?\"" >> "$path"
    echo "    exit 1" >> "$path"
    echo "fi" >> "$path"
    chmod +x "$path"
    echo "    Created: $name"
}

create_script "pwn-toggle"   "/tmp/pwn_switch_request" "Mode Switch signal sent to Pwnagotchi."
create_script "pwn-shutdown" "/tmp/pwn_shutdown"       "Shutdown signal sent to Pwnagotchi."
create_script "pwn-reboot"   "/tmp/pwn_reboot"         "Reboot signal sent to Pwnagotchi."
create_script "pwn-cancel"   "/tmp/pwn_cancel"         "Cancellation signal sent to Pwnagotchi."
create_script "pwn-test"     "/tmp/pwn_ui_test"        "UI Test signal sent to Pwnagotchi."

# 3. Final Instructions
echo ""
echo "=== Installation Complete! ==="
echo ""
echo "Step 1: Add the following lines to your config file (/etc/pwnagotchi/config.toml):"
echo "--------------------------------------------------------"
echo "[main.plugins.mode_switch]"
echo "enabled = true"
echo "restart_delay = 5"
echo "face = \"( Z_Z )\""
echo "msg = \"REBOOTING TO\\n    {mode}\""
echo "--------------------------------------------------------"
echo ""
echo "Step 2: Restart Pwnagotchi to load the plugin."
echo "        sudo systemctl restart pwnagotchi"
echo ""
echo "You can now use these commands from your shell or hardware buttons:"
echo "  pwn-toggle     : Toggle between Auto/Manual"
echo "  pwn-shutdown   : Initiate Safe Shutdown"
echo "  pwn-reboot     : Initiate Safe Reboot"
echo "  pwn-cancel     : Cancel a pending reboot/shutdown"
echo "  pwn-test       : Test the UI splash screen"
echo ""