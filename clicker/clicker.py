"""
clicker.py

Single-file Python 3.9+ global mouse clicker for Windows using Tkinter.

Usage:
- Run this script with Python on Windows.
- Press CTRL+F5 to START rapid clicking at the current mouse position.
- Press CTRL+F6 to STOP clicking.
- The UI is a minimal Tkinter window (no text description) used only so the app can be closed cleanly.

Notes:
- No external dependencies; uses ctypes to call Win32 APIs.
- Tested conceptually on Windows (RegisterHotKey + GetMessage message loop).
- Run with Python 3.9+.

Current cost $0.03 USD and 97,288 tokens.  40,000 to do majority of the work, 50,000 for small changes.
"""

import ctypes
import ctypes.wintypes as wintypes
import threading
import time
import sys
import tkinter as tk

# Configuration
CLICKS_PER_SECOND = 20  # default clicks per second (adjustable)
CLICK_INTERVAL = 1.0 / CLICKS_PER_SECOND

# Hotkey IDs
HOTKEY_ID_START = 1
HOTKEY_ID_STOP = 2

# Win32 constants
MOD_CONTROL = 0x0002
VK_F5 = 0x74   # 116
VK_F6 = 0x75   # 117
WM_HOTKEY = 0x0312

# SendInput constants
INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

# Setup types for SendInput
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class _INPUTunion(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTunion)]
    _anonymous_ = ("union",)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SendInput = user32.SendInput
SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = wintypes.UINT

RegisterHotKey = user32.RegisterHotKey
RegisterHotKey.argtypes = (wintypes.HWND, wintypes.INT, wintypes.UINT, wintypes.UINT)
RegisterHotKey.restype = wintypes.BOOL

UnregisterHotKey = user32.UnregisterHotKey
UnregisterHotKey.argtypes = (wintypes.HWND, wintypes.INT)
UnregisterHotKey.restype = wintypes.BOOL

GetMessage = user32.GetMessageW
GetMessage.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
GetMessage.restype = wintypes.BOOL

PostThreadMessage = user32.PostThreadMessageW
PostThreadMessage.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
PostThreadMessage.restype = wintypes.BOOL

# Shared control objects
running_event = threading.Event()
exit_event = threading.Event()
message_thread_id = None
message_thread_handle = None

def send_left_click():
    """Send a left mouse click (down + up) at current cursor position using SendInput."""
    inputs = (INPUT * 2)()
    # Left down
    inputs[0].type = INPUT_MOUSE
    inputs[0].mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, ULONG_PTR(0))
    # Left up
    inputs[1].type = INPUT_MOUSE
    inputs[1].mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, ULONG_PTR(0))
 
    # Cast array to POINTER(INPUT) so ctypes passes the correct pointer type to SendInput
    ptr = ctypes.cast(inputs, ctypes.POINTER(INPUT))
    n = SendInput(2, ptr, ctypes.sizeof(INPUT))
    if n != 2:
        # Non-fatal; print for diagnostics
        print(f"SendInput sent {n} events (expected 2)")

def click_worker():
    """Worker thread that sends clicks while running_event is set. Respects exit_event to quit."""
    print("Click worker thread started")
    # Use a small sleep granularity loop to allow quicker stop response
    while not exit_event.is_set():
        if running_event.is_set():
            start_time = time.perf_counter()
            send_left_click()
            # Sleep remaining time of interval while allowing early exit
            elapsed = time.perf_counter() - start_time
            to_sleep = max(0.0, CLICK_INTERVAL - elapsed)
            # Break sleep into short chunks so exit_event can interrupt quickly
            slept = 0.0
            chunk = 0.01
            while slept < to_sleep and not exit_event.is_set() and running_event.is_set():
                time.sleep(min(chunk, to_sleep - slept))
                slept += chunk
        else:
            # Not running: wait briefly and check again
            time.sleep(0.05)
    print("Click worker thread exiting")

def message_loop_thread():
    """Thread that registers hotkeys and runs a GetMessage loop to capture WM_HOTKEY."""
    global message_thread_id
    message_thread_id = kernel32.GetCurrentThreadId()
    print(f"Message thread started (thread id {message_thread_id}). Registering hotkeys.")

    # Register hotkeys for this thread (NULL hwnd)
    if not RegisterHotKey(None, HOTKEY_ID_START, MOD_CONTROL, VK_F5):
        print("Failed to register start hotkey (CTRL+F5).")
    else:
        print("Registered start hotkey: CTRL+F5")

    if not RegisterHotKey(None, HOTKEY_ID_STOP, MOD_CONTROL, VK_F6):
        print("Failed to register stop hotkey (CTRL+F6).")
    else:
        print("Registered stop hotkey: CTRL+F6")

    msg = wintypes.MSG()
    try:
        while not exit_event.is_set():
            ret = GetMessage(ctypes.byref(msg), None, 0, 0)
            if ret == 0:  # WM_QUIT
                break
            if ret == -1:
                print("GetMessage returned -1 (error).")
                break
            if msg.message == WM_HOTKEY:
                hid = msg.wParam
                try:
                    hid_val = int(hid)
                except Exception:
                    hid_val = hid & 0xffffffff
                if hid_val == HOTKEY_ID_START:
                    if not running_event.is_set():
                        running_event.set()
                        print("Global hotkey: START (CTRL+F5) - clicking started")
                    else:
                        print("Global hotkey: START received but already running")
                elif hid_val == HOTKEY_ID_STOP:
                    if running_event.is_set():
                        running_event.clear()
                        print("Global hotkey: STOP (CTRL+F6) - clicking stopped")
                    else:
                        print("Global hotkey: STOP received but was not running")
            # Continue loop
    finally:
        # Unregister hotkeys on thread exit
        try:
            UnregisterHotKey(None, HOTKEY_ID_START)
            UnregisterHotKey(None, HOTKEY_ID_STOP)
        except Exception:
            pass
        print("Message thread exiting and hotkeys unregistered")

def on_close(root, threads):
    """Called when the Tk window is closed. Signals threads to exit and waits for them."""
    print("Shutting down...")
    # Clear running, signal exit
    running_event.clear()
    exit_event.set()

    # If message thread is waiting in GetMessage, post a quit message to it
    if message_thread_id:
        # Post WM_QUIT to the message thread to unblock GetMessage
        user32.PostThreadMessageW(message_thread_id, 0x0012, 0, 0)  # 0x0012 == WM_QUIT

    # Join threads (with timeout to avoid hanging indefinitely)
    for t in threads:
        if t is threading.current_thread():
            continue
        t.join(timeout=2.0)

    # Finally destroy the Tk root and exit
    try:
        root.destroy()
    except Exception:
        pass
    print("Exited.")
    sys.exit(0)

def center_window(root, width=200, height=80):
    """Center the Tk window on the primary monitor."""
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

def main():
    # Start message loop thread
    msg_thread = threading.Thread(target=message_loop_thread, name="MsgThread", daemon=True)
    msg_thread.start()

    # Start click worker thread
    worker_thread = threading.Thread(target=click_worker, name="ClickWorker", daemon=True)
    worker_thread.start()

    # Minimal Tkinter UI
    root = tk.Tk()
    root.title("Clicker")  # window title

    # Remove maximize/minimize buttons for minimalism (Windows-specific)
    try:
        root.resizable(False, False)
    except Exception:
        pass

    # Geometry sized to fit the description and exit button
    center_window(root, width=220, height=110)

    # Status label showing whether clicking is enabled
    status_lbl = tk.Label(root, text="Disabled", justify="left")
    status_lbl.pack(pady=(10, 0))
    
    # Hotkey description label (shows start and stop hotkeys)
    info_text = "Start: CTRL+F5\nStop: CTRL+F6"
    lbl = tk.Label(root, text=info_text, justify="left")
    lbl.pack(pady=(4, 4))
    
    # Exit button placed under the description
    btn = tk.Button(root, text="Exit", width=10, command=lambda: on_close(root, [msg_thread, worker_thread]))
    btn.pack(pady=(0, 10))
    
    # Periodically update status label to reflect running state
    def update_status_label():
        if running_event.is_set():
            status_lbl.config(text="Enabled", fg="darkgreen", font=("TkDefaultFont", 9, "bold"))
        else:
            status_lbl.config(text="Disabled", fg="black", font=("TkDefaultFont", 9, "normal"))
        root.after(100, update_status_label)
    
    update_status_label()
    
    # Bind close handler to clean up (also triggered by the window close button)
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root, [msg_thread, worker_thread]))

    # Start the Tk mainloop (runs in main thread)
    try:
        print("Application started. Use CTRL+F5 to start clicking, CTRL+F6 to stop.")
        root.mainloop()
    except KeyboardInterrupt:
        on_close(root, [msg_thread, worker_thread])

if __name__ == "__main__":
    main()