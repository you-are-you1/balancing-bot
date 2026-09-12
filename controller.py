import tkinter as tk
import asyncio
import threading
from contextlib import suppress

from bleak import BleakScanner, BleakClient


# ============================================================
# Pybricks Bluetooth UUID
# ============================================================

PYBRICKS_COMMAND_EVENT_CHAR_UUID = (
    "c5f50002-8280-46da-89f4-6d8051e4aeef"
)


# ============================================================
# BLE state
# ============================================================

ble_loop = None
ble_client = None
connected = False

ready_event = None
send_lock = None


# ============================================================
# Status
# ============================================================

def update_status(message, color="blue"):
    root.after(
        0,
        lambda: status_label.config(
            text=message,
            fg=color
        )
    )


# ============================================================
# Connect to hub
# ============================================================

async def connect_to_hub(name):
    global ble_client
    global connected
    global ready_event
    global send_lock

    update_status("Scanning for hub...")

    try:
        # Find the hub by Bluetooth name
        device = await BleakScanner.find_device_by_name(name)

        if device is None:
            update_status(
                f'Could not find "{name}"',
                "red"
            )
            return

        update_status(
            f"Found {device.name}. Connecting..."
        )

        ready_event = asyncio.Event()
        send_lock = asyncio.Lock()

        # ----------------------------------------------------
        # Handle data received from hub
        # ----------------------------------------------------

        def handle_rx(_, data: bytearray):

            if len(data) == 0:
                return

            # 0x01 = write stdout event
            if data[0] == 0x01:

                payload = data[1:]

                # Hub is ready for another command
                if payload == b"rdy":
                    ready_event.set()

        # ----------------------------------------------------
        # Handle disconnection
        # ----------------------------------------------------

        def handle_disconnect(_):
            global connected

            connected = False

            update_status(
                "Hub disconnected",
                "red"
            )

        # ----------------------------------------------------
        # Connect
        # ----------------------------------------------------

        ble_client = BleakClient(
            device,
            handle_disconnect
        )

        await ble_client.connect()

        await ble_client.start_notify(
            PYBRICKS_COMMAND_EVENT_CHAR_UUID,
            handle_rx
        )

        connected = True

        update_status(
            f"Connected to {device.name}",
            "green"
        )

        print("Connected.")
        print("Start the Pybricks program on the hub.")

    except Exception as e:

        connected = False

        update_status(
            f"Connection error: {e}",
            "red"
        )

        print("Connection error:", e)


# ============================================================
# Send data to Pybricks
# ============================================================

async def send_data(data):

    global connected

    if not connected or ble_client is None:
        return

    async with send_lock:

        try:
            # Wait until Pybricks says it is ready
            await ready_event.wait()

            # Prepare for next ready notification
            ready_event.clear()

            # 0x06 = write stdin
            await ble_client.write_gatt_char(
                PYBRICKS_COMMAND_EVENT_CHAR_UUID,
                b"\x06" + data,
                response=True
            )

        except Exception as e:

            connected = False

            update_status(
                f"Send error: {e}",
                "red"
            )

            print("Send error:", e)


# ============================================================
# Send command
# ============================================================

def send_command(command):

    if not connected:
        return

    asyncio.run_coroutine_threadsafe(
        send_data(command.encode("ascii")),
        ble_loop
    )


# ============================================================
# BLE event loop thread
# ============================================================

def ble_thread_function():

    global ble_loop

    ble_loop = asyncio.new_event_loop()

    asyncio.set_event_loop(ble_loop)

    ble_loop.run_forever()


ble_thread = threading.Thread(
    target=ble_thread_function,
    daemon=True
)

ble_thread.start()


# ============================================================
# Connect / Disconnect
# ============================================================

def connect_button_pressed():

    name = hub_name_entry.get().strip()

    if not name:

        update_status(
            "Enter the hub name",
            "red"
        )

        return

    connect_button.config(
        state="disabled"
    )

    asyncio.run_coroutine_threadsafe(
        connect_to_hub(name),
        ble_loop
    )


async def disconnect_from_hub():

    global ble_client
    global connected

    connected = False

    if ble_client is not None:

        try:
            await ble_client.stop_notify(
                PYBRICKS_COMMAND_EVENT_CHAR_UUID
            )
        except Exception:
            pass

        try:
            await ble_client.disconnect()
        except Exception:
            pass

    ble_client = None

    update_status(
        "Disconnected",
        "blue"
    )

    root.after(
        0,
        lambda: connect_button.config(
            state="normal"
        )
    )


def disconnect_button_pressed():

    asyncio.run_coroutine_threadsafe(
        disconnect_from_hub(),
        ble_loop
    )


# ============================================================
# Keyboard controls
# ============================================================

key_commands = {
    "Up": "W",
    "Left": "A",
    "Down": "S",
    "Right": "D"
}


# Keep track of which keys are currently held
keys_held = set()


def key_pressed(event):

    command = key_commands.get(event.keysym)

    if command is None:
        return

    # Ignore repeated KeyPress events generated while holding a key down
    if event.keysym in keys_held:
        return

    keys_held.add(event.keysym)

    send_command(command)


def key_released(event):

    command = key_commands.get(event.keysym)

    if command is None:
        return

    if event.keysym not in keys_held:
        return

    keys_held.remove(event.keysym)

    send_command("X")


# ============================================================
# Mouse controls
# ============================================================

def mouse_pressed(command):
    send_command(command)


def mouse_released():
    send_command("X")


# ============================================================
# GUI
# ============================================================

root = tk.Tk()

root.title("Pybricks WASD Remote")
root.geometry("360x390")
root.resizable(False, False)


# ============================================================
# Hub name
# ============================================================

tk.Label(
    root,
    text="Hub name:",
    font=("Arial", 12)
).pack(pady=(15, 5))


hub_name_entry = tk.Entry(
    root,
    font=("Arial", 14),
    justify="center",
    width=25
)

hub_name_entry.pack()


# ============================================================
# Connect
# ============================================================

connect_button = tk.Button(
    root,
    text="Connect",
    font=("Arial", 12),
    width=12,
    command=connect_button_pressed
)

connect_button.pack(pady=10)


# ============================================================
# Disconnect
# ============================================================

disconnect_button = tk.Button(
    root,
    text="Disconnect",
    font=("Arial", 12),
    width=12,
    command=disconnect_button_pressed
)

disconnect_button.pack()


# ============================================================
# Status
# ============================================================

status_label = tk.Label(
    root,
    text="Not connected",
    font=("Arial", 11),
    fg="blue"
)

status_label.pack(pady=15)


# ============================================================
# Direction buttons
# ============================================================

button_frame = tk.Frame(root)
button_frame.pack()


up_button = tk.Button(
    button_frame,
    text="↑\nW",
    font=("Arial", 16),
    width=7,
    height=2
)

up_button.grid(
    row=0,
    column=1,
    padx=5,
    pady=5
)


left_button = tk.Button(
    button_frame,
    text="←\nA",
    font=("Arial", 16),
    width=7,
    height=2
)

left_button.grid(
    row=1,
    column=0,
    padx=5,
    pady=5
)


down_button = tk.Button(
    button_frame,
    text="↓\nS",
    font=("Arial", 16),
    width=7,
    height=2
)

down_button.grid(
    row=1,
    column=1,
    padx=5,
    pady=5
)


right_button = tk.Button(
    button_frame,
    text="→\nD",
    font=("Arial", 16),
    width=7,
    height=2
)

right_button.grid(
    row=1,
    column=2,
    padx=5,
    pady=5
)


# ============================================================
# Mouse press/release
# ============================================================

up_button.bind(
    "<ButtonPress-1>",
    lambda event: mouse_pressed("W")
)

up_button.bind(
    "<ButtonRelease-1>",
    lambda event: mouse_released()
)


left_button.bind(
    "<ButtonPress-1>",
    lambda event: mouse_pressed("A")
)

left_button.bind(
    "<ButtonRelease-1>",
    lambda event: mouse_released()
)


down_button.bind(
    "<ButtonPress-1>",
    lambda event: mouse_pressed("S")
)

down_button.bind(
    "<ButtonRelease-1>",
    lambda event: mouse_released()
)


right_button.bind(
    "<ButtonPress-1>",
    lambda event: mouse_pressed("D")
)

right_button.bind(
    "<ButtonRelease-1>",
    lambda event: mouse_released()
)


# ============================================================
# Keyboard press/release
# ============================================================

root.bind(
    "<KeyPress-Up>",
    key_pressed
)

root.bind(
    "<KeyPress-Left>",
    key_pressed
)

root.bind(
    "<KeyPress-Down>",
    key_pressed
)

root.bind(
    "<KeyPress-Right>",
    key_pressed
)


root.bind(
    "<KeyRelease-Up>",
    key_released
)

root.bind(
    "<KeyRelease-Left>",
    key_released
)

root.bind(
    "<KeyRelease-Down>",
    key_released
)

root.bind(
    "<KeyRelease-Right>",
    key_released
)


# ============================================================
# Keyboard focus
# ============================================================

root.focus_force()


# ============================================================
# Close
# ============================================================

def on_close():

    if ble_loop is not None:

        future = asyncio.run_coroutine_threadsafe(
            disconnect_from_hub(),
            ble_loop
        )

        with suppress(Exception):

            try:
                future.result(timeout=2)
            except Exception:
                pass

        ble_loop.call_soon_threadsafe(
            ble_loop.stop
        )

    root.destroy()


root.protocol(
    "WM_DELETE_WINDOW",
    on_close
)


# ============================================================
# Start
# ============================================================

root.mainloop()