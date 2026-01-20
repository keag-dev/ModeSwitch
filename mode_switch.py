import logging
import os
import time
import threading
import subprocess
from PIL import ImageFont

import pwnagotchi.plugins as plugins
from pwnagotchi.ui.components import Text
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts

class ModeSwitch(plugins.Plugin):
    __author__ = 'YourName'
    __version__ = '0.1.1-alpha'
    __license__ = 'MIT'
    __description__ = 'Toggle Auto/Manual mode with UI feedback, Test mode, and Cancellation.'

    # --- CONSTANTS ---
    # Filesystem triggers monitored by the watchdog thread.
    # These allow hardware buttons (via shell scripts) to trigger plugin actions.
    TRIGGER_SWITCH = "/tmp/pwn_switch_request"
    TRIGGER_TEST   = "/tmp/pwn_ui_test"
    TRIGGER_CANCEL = "/tmp/pwn_cancel"

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.agent = None
        self.ui = None
        
        # Threading control
        self.running = False
        self.thread = None
        self.lock = threading.Lock()  # Prevents race conditions between Webhook and Filesystem triggers
        
        # State Management
        self.restart_pending = False
        self.cancel_event = threading.Event() # Used to signal the countdown thread to abort
        
        # UI Snapshot Storage
        # Stores the state of the screen before we wipe it for the splash screen.
        self.ui_backup = {}

    def on_loaded(self):
        """
        PWNAGOTCHI LIFECYCLE: Called when the plugin is first loaded.
        We start the background watchdog thread here.
        """
        self.running = True
        self.thread = threading.Thread(target=self._watchdog_worker, daemon=True)
        self.thread.start()
        self.log.info(f"ModeSwitch {self.__version__} loaded.")

    def on_ready(self, agent):
        """
        PWNAGOTCHI LIFECYCLE: Called when the main Agent is ready.
        We need the 'agent' object to check the current mode (AUTO vs MANUAL).
        """
        self.agent = agent

    def on_ui_setup(self, ui):
        """
        PWNAGOTCHI LIFECYCLE: Called during UI initialization.
        CRITICAL: We must capture the 'ui' object here to manipulate the display later.
        """
        self.ui = ui

    def on_unload(self, ui):
        """
        PWNAGOTCHI LIFECYCLE: Called on shutdown/unload.
        Stops the watchdog loop.
        """
        self.running = False

    def on_webhook(self, path, request):
        """
        PWNAGOTCHI LIFECYCLE: Handle incoming HTTP requests.
        Endpoint base: http://<ip>:8080/plugins/mode_switch/
        """
        if path == 'toggle':
            return self._initiate_switch("Webhook")
        elif path == 'test':
            return self._run_test_ui("Webhook")
        elif path == 'cancel':
            return self._trigger_cancel("Webhook")
        return "Unknown command."

    def _watchdog_worker(self):
        """
        BACKGROUND TASK: Polls the /tmp/ directory for trigger files every 0.5s.
        If a file is found, it deletes it (debounce) and executes the corresponding logic.
        """
        while self.running:
            if os.path.exists(self.TRIGGER_SWITCH):
                self._safe_remove(self.TRIGGER_SWITCH)
                self._initiate_switch("Filesystem")
            
            if os.path.exists(self.TRIGGER_TEST):
                self._safe_remove(self.TRIGGER_TEST)
                self._run_test_ui("Filesystem")

            if os.path.exists(self.TRIGGER_CANCEL):
                self._safe_remove(self.TRIGGER_CANCEL)
                self._trigger_cancel("Filesystem")

            time.sleep(0.5)

    def _safe_remove(self, filepath):
        try:
            os.remove(filepath)
        except OSError:
            pass

    # --- LOGIC HANDLERS ---

    def _trigger_cancel(self, source):
        """
        Sets the threading event to abort the countdown.
        """
        if self.restart_pending:
            self.log.info(f"[{source}] Cancel signal received! Aborting restart.")
            self.cancel_event.set()
            return "Cancellation signal sent."
        return "Nothing to cancel."

    def _run_test_ui(self, source):
        """
        UI TEST: Snapshots the UI, shows the splash screen for 'restart_delay' seconds, 
        then restores the UI. Used for calibrating CSS/Positions.
        """
        if self.restart_pending:
            return "Cannot test while restart is pending."

        self.log.info(f"[{source}] Running UI Test...")
        delay = self.options.get('restart_delay', 5)
        
        self._show_splash_screen("TESTING")
        time.sleep(delay)
        self._restore_ui()
        return "Test complete. Restoring UI."

    def _initiate_switch(self, source):
        """
        MAIN LOGIC:
        1. Determines target mode (AUTO <-> MANUAL).
        2. Shows splash screen.
        3. Starts background countdown thread for reboot.
        """
        with self.lock:
            if not self.agent:
                return "Agent not ready."
            if self.restart_pending:
                return "Restart already in progress."

            self.restart_pending = True
            self.cancel_event.clear()

            current_mode = self.agent.mode
            target_mode = "MANUAL" if current_mode in ['AUTO', 'AI'] else "AUTO"
            delay = self.options.get('restart_delay', 5)
            
            self.log.info(f"[{source}] Switching {current_mode} -> {target_mode} in {delay}s")

            self._show_splash_screen(target_mode)

            # Pwnagotchi uses file flags in /root/ to determine boot mode
            if target_mode == "MANUAL":
                cmd = "touch /root/.pwnagotchi-manu && systemctl restart pwnagotchi"
            else:
                cmd = "touch /root/.pwnagotchi-auto && systemctl restart pwnagotchi"

            threading.Thread(target=self._countdown_and_execute, args=(cmd, delay)).start()
            
            return f"Restarting into {target_mode} in {delay} seconds... (Trigger 'cancel' to abort)"

    def _countdown_and_execute(self, cmd, delay):
        """
        BACKGROUND TASK: Waits for 'delay' seconds while checking for cancel signal.
        If not cancelled, executes the system reboot command.
        """
        # Check 10 times per second for responsiveness
        steps = int(delay * 10)
        for _ in range(steps):
            if self.cancel_event.is_set():
                self.log.info("Restart ABORTED by user.")
                self.restart_pending = False
                self._restore_ui() # CRITICAL: Put the old UI elements back
                return
            time.sleep(0.1)

        self.log.info("Countdown finished. Executing restart.")
        subprocess.Popen(cmd, shell=True)

    # --- UI MANIPULATION ---

    def _show_splash_screen(self, target_mode):
        """
        1. Backs up current UI state.
        2. Wipes screen.
        3. Draws custom splash screen elements.
        """
        if not self.ui: return

        # ARCHITECTURE NOTE: Pwnagotchi UI elements are stored in self.ui._state.
        # We backup this dict so we can restore it if the user cancels.
        if not self.ui_backup:
            self.ui_backup = self.ui._state.copy()

        # Remove all current elements to clear the "Whiteboard"
        for key in list(self.ui._state.keys()):
            self.ui.remove_element(key)

        # Load Config
        face_str = self.options.get('face', '( Z_Z )')
        face_x = self.options.get('face_x', 55)
        face_y = self.options.get('face_y', 15)
        face_size = self.options.get('face_size', 35)
        
        msg_fmt = self.options.get('msg', 'REBOOTING TO\n    {mode}')
        msg_str = msg_fmt.replace('{mode}', target_mode)
        msg_x = self.options.get('msg_x', 45)
        msg_y = self.options.get('msg_y', 65)
        msg_size = self.options.get('msg_size', 20)
        
        abort_str = self.options.get('abort_msg', 'Click again to Cancel')
        abort_x = self.options.get('abort_x', 50)
        abort_y = self.options.get('abort_y', 105) 
        abort_size = self.options.get('abort_size', 12)

        try:
            # Fallback for font path
            font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
            if hasattr(fonts, 'status_font') and hasattr(fonts.status_font, 'path'):
                font_path = fonts.status_font.path
            
            font_face = ImageFont.truetype(font_path, face_size)
            font_msg = ImageFont.truetype(font_path, msg_size)
            font_abort = ImageFont.truetype(font_path, abort_size)

            self.ui.add_element('restart_face', Text(color=BLACK, value=face_str, position=(face_x, face_y), font=font_face))
            self.ui.add_element('restart_msg', Text(color=BLACK, value=msg_str, position=(msg_x, msg_y), font=font_msg))
            self.ui.add_element('restart_abort', Text(color=BLACK, value=abort_str, position=(abort_x, abort_y), font=font_abort))
            
            self.ui.update(force=True)

        except Exception as e:
            self.log.error(f"UI update failed: {e}")

    def _restore_ui(self):
        """
        Restores the screen to its pre-splash state.
        Necessary because Pwnagotchi only updates elements it expects to exist.
        """
        if not self.ui: return
        try:
            self.log.info("Restoring normal UI...")
            # 1. Remove Splash elements
            for el in ['restart_face', 'restart_msg', 'restart_abort']:
                if el in self.ui._state:
                    self.ui.remove_element(el)

            # 2. Restore Original elements from backup
            if self.ui_backup:
                for key, component in self.ui_backup.items():
                    self.ui.add_element(key, component)
                self.ui_backup = {}

            # 3. Force Redraw
            self.ui.update(force=True)
        except Exception as e:
            self.log.error(f"UI restore failed: {e}")
