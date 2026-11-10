"""
Notification, Voice Alert & Windows Toast System.
Provides audible chimes, asynchronous Text-to-Speech voice announcements,
and Windows desktop toast notifications so the user knows exactly what the bot is doing
even when in another window.
"""

from __future__ import annotations
import sys
import threading
import subprocess
import logging
import winsound

logger = logging.getLogger(__name__)


class Notifier:
    """Dispatches audio cues, TTS voice announcements, and Windows desktop toast alerts."""

    def __init__(self, voice_enabled: bool = True, sounds_enabled: bool = True, toasts_enabled: bool = True):
        self.voice_enabled = voice_enabled
        self.sounds_enabled = sounds_enabled
        self.toasts_enabled = toasts_enabled
        self._lock = threading.Lock()

    def play_chime(self, chime_type: str = "ok") -> None:
        """Plays non-blocking Windows sound cues."""
        if not self.sounds_enabled:
            return

        def _play():
            try:
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
            except Exception:
                pass

        threading.Thread(target=_play, daemon=True).start()

    def show_windows_toast(self, title: str, message: str) -> None:
        """Displays a direct Windows desktop toast notification popup."""
        if not self.toasts_enabled:
            return

        def _toast():
            try:
                clean_title = title.replace('"', '').replace("'", "")
                clean_msg = message.replace('"', '').replace("'", "")
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
            except Exception as e:
                logger.debug(f"Toast notification failed: {e}")

        threading.Thread(target=_toast, daemon=True).start()

    def announce(self, message: str, chime: str = "ok", toast_title: str = "CoC Farm Controller") -> None:
        """Speaks a message asynchronously, plays an audio chime, and shows a Windows toast notification."""
        logger.info(f"[ALERT] {message}")
        if self.sounds_enabled and chime:
            self.play_chime(chime)

        if self.toasts_enabled:
            self.show_windows_toast(toast_title, message)

        if not self.voice_enabled or not message:
            return

        def _tts():
            with self._lock:
                try:
                    clean_msg = message.replace('"', '').replace("'", "").replace('`', '')
                    ps_cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{clean_msg}')"
                    subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                        capture_output=True,
                        timeout=5
                    )
                except Exception as e:
                    logger.debug(f"TTS output failed: {e}")

        threading.Thread(target=_tts, daemon=True).start()


# Backward compatibility alias
NotificationDispatcher = Notifier

