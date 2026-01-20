# ModeSwitch Plugin for Pwnagotchi

**ModeSwitch** is a Python plugin for Pwnagotchi (specifically designed for the **jayofelony/pwnagotchi-torch** fork). It allows users to toggle between **AUTO** (AI/Action) mode and **MANUAL** (Station/Maintenance) mode without needing SSH access, providing visual feedback and a safety cancellation mechanism.

## Features

*   **Mode Toggling:** Switch between AI/AUTO and MANUAL modes easily.
*   **Visual Feedback:** Displays a splash screen indicating the target mode and a countdown before rebooting.
*   **Safety/Cancellation:** Includes a countdown timer allowing you to abort the switch if triggered accidentally.
*   **Hybrid Trigger System:**
    *   **Webhooks:** Trigger via HTTP requests to the Pwnagotchi API.
    *   **Filesystem Watchdog:** Monitor `/tmp/` for trigger files, enabling integration with hardware buttons (e.g., PiSugar GPIO).
*   **UI Test Mode:** Calibrate UI element positions without rebooting.

## Installation

1.  Copy `mode_switch.py` to your Pwnagotchi's custom plugins directory (usually `/usr/local/share/pwnagotchi/custom-plugins/` or `/home/pi/custom-plugins/`).
2.  Enable the plugin in your `config.toml`.

## Configuration

Add the following to your `/etc/pwnagotchi/config.toml` file:

```toml
[main.plugins.mode_switch]
enabled = true
restart_delay = 5
face = "( Z_Z )"
msg = "REBOOTING TO\n    {mode}"
abort_msg = "Click again to Cancel"

# UI Positioning (Optional overrides)
# face_x = 55
# face_y = 15
# face_size = 35
# msg_x = 45
# msg_y = 65
# msg_size = 20
# abort_x = 50
# abort_y = 105
# abort_size = 12
```

## Usage

### Webhooks
You can control the plugin via the web interface or curl commands (port 8080):

*   **Toggle Mode:** `http://<pwnagotchi-ip>:8080/plugins/mode_switch/toggle`
*   **Cancel Reboot:** `http://<pwnagotchi-ip>:8080/plugins/mode_switch/cancel`
*   **Test UI:** `http://<pwnagotchi-ip>:8080/plugins/mode_switch/test`

### Hardware Buttons (Filesystem Triggers)
The plugin monitors the `/tmp/` directory for specific files. This is useful for mapping physical buttons (like on a PiSugar) to shell scripts.

1.  **Switch Mode:** `touch /tmp/pwn_switch_request`
2.  **Cancel:** `touch /tmp/pwn_cancel`
3.  **Test UI:** `touch /tmp/pwn_ui_test`

#### Example Scripts
Create these scripts in `/home/pi/` and map your hardware buttons to execute them:

**`mode_switch_trigger.sh`**
```bash
#!/bin/bash
touch /tmp/pwn_switch_request
```

**`mode_switch_cancel.sh`**
```bash
#!/bin/bash
touch /tmp/pwn_cancel
```

## License
MIT
