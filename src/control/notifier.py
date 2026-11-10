"""
Notification, Voice Alert & Desktop Toast System.
Cross-Platform: Windows (winsound, SAPI TTS, Toast) & macOS (afplay, 'say' TTS, osascript notifications).
Provides audible chimes, asynchronous Text-to-Speech voice announcements,
and desktop toast notifications so the user knows exactly what the bot is doing
even when in another window.
"""

from __future__ import annotations
import sys
import os
import threading
import subprocess
import logging

logger = logging.getLogger(__name__)

# Safe platform conditional sound import
if sys.platform == "win32":
    try:
        import winsound
    except ImportError:
        winsound = None
else:
    winsound = None


class Notifier:
    """Dispatches audio cues, TTS voice announcements, and desktop toast alerts across Windows and macOS."""

    def __init__(self, voice_enabled: bool = True, sounds_enabled: bool = True, toasts_enabled: bool = True):
        self.voice_enabled = voice_enabled
        self.sounds_enabled = sounds_enabled
        self.toasts_enabled = toasts_enabled
        self._lock = threading.Lock()

    def play_chime(self, chime_type: str = "ok") -> None:
        """Plays non-blocking audio sound cues."""
        if not self.sounds_enabled:
            return

        def _play():
            try:
                if sys.platform == "win32" and winsound:
                    if chime_type == "accept":
                        winsound.Beep(880, 120)
                        winsound.Beep(1174, 160)
                    elif chime_type == "skip":
                        winsound.Beep(523, 80)
                    elif chime_type == "victory":
                        winsound.Beep(659, 100)
                        winsound.Beep(783, 100)
                        winsound.Beep(1046, 250)
                    elif chime_type == "pause":
                        winsound.Beep(600, 150)
                        winsound.Beep(400, 200)
                    elif chime_type == "error":
                        winsound.MessageBeep(winsound.MB_ICONHAND)
                    else:
                        winsound.MessageBeep(winsound.MB_OK)
                elif sys.platform == "darwin":
                    # macOS system sound mappings
                    sound_map = {
                        "accept": "/System/Library/Sounds/Glass.aiff",
                        "skip": "/System/Library/Sounds/Tink.aiff",
                        "victory": "/System/Library/Sounds/Hero.aiff",
                        "pause": "/System/Library/Sounds/Blow.aiff",
                        "error": "/System/Library/Sounds/Basso.aiff",
                        "ok": "/System/Library/Sounds/Ping.aiff"
                    }
                    sound_path = sound_map.get(chime_type, "/System/Library/Sounds/Ping.aiff")
                    if os.path.exists(sound_path):
                        subprocess.run(["afplay", sound_path], timeout=2, capture_output=True)
                    else:
                        sys.stdout.write("\a")
                        sys.stdout.flush()
                else:
                    # Linux or generic POSIX
                    sys.stdout.write("\a")
                    sys.stdout.flush()
            except Exception:
                pass

        threading.Thread(target=_play, daemon=True).start()

    def show_desktop_toast(self, title: str, message: str) -> None:
        """Displays a desktop toast / notification popup across Windows and macOS."""
        if not self.toasts_enabled:
            return

        def _toast():
            try:
                clean_title = title.replace('"', '').replace("'", "")
                clean_msg = message.replace('"', '').replace("'", "")

                if sys.platform == "win32":
                    ps_script = f"""
                    [reflection.assembly]::loadwithpartialname("System.Windows.Forms") | Out-Null
                    $notification = New-Object System.Windows.Forms.NotifyIcon
                    $notification.Icon = [System.Drawing.SystemIcons]::Information
                    $notification.BalloonTipTitle = "{clean_title}"
                    $notification.BalloonTipText = "{clean_msg}"
                    $notification.Visible = $True
                    $notification.ShowBalloonTip(3000)
                    Start-Sleep -Seconds 3
                    $notification.Dispose()
                    """
                    subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                        capture_output=True,
                        timeout=5
                    )
                elif sys.platform == "darwin":
                    osa_script = f'display notification "{clean_msg}" with title "{clean_title}"'
                    subprocess.run(["osascript", "-e", osa_script], capture_output=True, timeout=5)
                else:
                    # Linux fallback (notify-send)
                    subprocess.run(["notify-send", clean_title, clean_msg], capture_output=True, timeout=5)
            except Exception as e:
                logger.debug(f"Toast notification failed: {e}")

        threading.Thread(target=_toast, daemon=True).start()

    # Alias for backward compatibility
    show_windows_toast = show_desktop_toast

    def announce(self, message: str, chime: str = "ok", toast_title: str = "CoC Farm Controller") -> None:
        """Speaks a message asynchronously, plays an audio chime, and shows a desktop notification."""
        logger.info(f"[ALERT] {message}")
        if self.sounds_enabled and chime:
            self.play_chime(chime)

        if self.toasts_enabled:
            self.show_desktop_toast(toast_title, message)

        if not self.voice_enabled or not message:
            return

        def _tts():
            with self._lock:
                try:
                    clean_msg = message.replace('"', '').replace("'", "").replace('`', '')
                    if sys.platform == "win32":
                        ps_cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{clean_msg}')"
                        subprocess.run(
                            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                            capture_output=True,
                            timeout=5
                        )
                    elif sys.platform == "darwin":
                        subprocess.run(["say", clean_msg], capture_output=True, timeout=5)
                    else:
                        # Linux fallback (spd-say or espeak)
                        subprocess.run(["spd-say", clean_msg], capture_output=True, timeout=5)
                except Exception as e:
                    logger.debug(f"TTS output failed: {e}")

        threading.Thread(target=_tts, daemon=True).start()


# Backward compatibility alias
NotificationDispatcher = Notifier
