#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import sounddevice as sd
import random
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import scipy
import datetime

SAMPLE_RATE = 44100
CHANNELS = 1
FREQUENCY_RANGE = (100, 10000)  # Hz


frequency_list = np.logspace(np.log10(FREQUENCY_RANGE[0]), np.log10(FREQUENCY_RANGE[1]), num=15)

data = [{frequency_list[i]: [0, 1] for i in range(len(frequency_list))}]  # 10 channels of data

state = {
    "enter_counter": 0,
    "data_key": 0,
    "frequency_i": 0,
    "volume": 0,
    "phase": 0,
    "playing": True,
}

fig, ax = plt.subplots(figsize=(5, 3))
ax_ref = ax.twinx()

def audio_callback(outdata, frames, time, status):
    if status:
        print(f"Audio callback status: {status}")
    t = (np.arange(frames) + state["phase"]) / SAMPLE_RATE
    wave = np.sin(np.pi * t) * state["volume"] * np.sin(2 * np.pi * frequency_list[state["frequency_i"]] * t)
    if not state["playing"]:
        wave *= 0
    outdata[:] = wave.reshape(-1, 1).astype(np.float32)
    state["phase"] = (state["phase"] + frames) % SAMPLE_RATE

def amplitude_to_db(amplitude_ref, amplitude):
    return 20 * np.log10(amplitude / amplitude_ref)

def update_plot():

    ax.clear()
    ax_ref.clear()

    ref_interp = None
    if len(data[0]) >= 2:
        ref_items = sorted(data[0].items())
        frequencies, volumes = zip(*ref_items)
        volumes = np.mean(np.array(volumes), axis=1)
        ref_interp = scipy.interpolate.interp1d(
            frequencies,
            volumes,
            kind="linear",
            bounds_error=False,
            fill_value="extrapolate",
        )
        ax_ref.plot(
            frequency_list,
            ref_interp(frequency_list),
            label=f"Channel {0}",
            alpha=0.3,
            markersize=4,
            color=plt.cm.tab10(0),
        )
        ax_ref.scatter(
            frequencies,
            volumes,
            color=plt.cm.tab10(0),
            edgecolor="black",
            alpha=0.3,
            zorder=5,
        )

    for i in range(1, len(data)):
        if len(data[i]) >= 2 and ref_interp is not None:
            channel_items = sorted(data[i].items())
            frequencies, volumes = zip(*channel_items)
            volumes = np.mean(np.array(volumes), axis=1)
            interp = scipy.interpolate.interp1d(
                frequencies,
                volumes,
                kind="linear",
                bounds_error=False,
                fill_value="extrapolate",
            )
            ax.plot(
                frequency_list,
                amplitude_to_db(ref_interp(frequency_list), interp(frequency_list)),
                label=f"Channel {i}",
                markersize=4,
                color=plt.cm.tab10(i),
            )
            ax.scatter(
                frequencies,
                amplitude_to_db(ref_interp(frequencies), volumes),
                color=plt.cm.tab10(i),
                edgecolor="black",
                s=50,
                zorder=5,
            )

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Attenuation (dB)")
    ax_ref.set_ylabel("Ref volumes")
    ax.set_title("Frequency vs Attenuation")
    ax.set_xscale("log")
    ax.grid(True, which="both", ls="--", lw=0.5)

    if ref_interp is not None:
        ax.legend(fontsize=7)
    else:
        ax.set_xlim(FREQUENCY_RANGE)

    plt.pause(0.001)



def update_freq(value):
    state["frequency_i"] = int(value)
    freq_label.config(text=f"freq: {frequency_list[state['frequency_i']]:.3f}")

def set_playing(enabled):
    state["playing"] = enabled
    play_label.config(text="Playing" if enabled else "Muted")


def on_key_toggle(event):
    if event.keysym == "Up":
        set_playing(True)
    elif event.keysym == "Down":
        set_playing(False)


def on_key_volume(event):
    if event.keysym == "Left":
        delta = -0.01
    elif event.keysym == "Right":
        delta = 0.01
    else:
        return

    current = float(volume_slider.get())
    new_value = min(1.0, max(0.0, current + delta))
    volume_slider.set(new_value)
    update_volume(new_value)


def update_volume(value):
    state["volume"] = (2*float(value))**3
    volume_label.config(text=f"Volume: {state['volume']:.3f}")


def on_close():
    try:
        fig.savefig(f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png")
        stream.stop()
        stream.close()
    except Exception:
        pass
    root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Live Tone Slider")
    root.geometry("600x400")
    root.resizable(True, True)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.bind("<Up>", on_key_toggle)
    root.bind("<Down>", on_key_toggle)
    root.bind("<Left>", on_key_volume)
    root.bind("<Right>", on_key_volume)

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")


    freq_label = ttk.Label(frame, text=f"Frequency: {frequency_list[state['frequency_i']]:.1f} Hz")
    freq_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

    freq_slider = tk.Scale(
        frame,
        from_=0,
        to=len(frequency_list) - 1,
        orient="horizontal",
        resolution=1,
        showvalue=False,
        command=update_freq,
    )
    freq_slider.set(0)
    freq_slider.grid(row=2, column=0, columnspan=2, sticky="ew")
    update_freq(0)

    volume_label = ttk.Label(frame, text=f"Volume: {state['volume']:.3f}")
    volume_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 4))

    volume_slider = ttk.Scale(
        frame, from_=0.0, to=1.0, orient="horizontal",
        command=update_volume, value=state["volume"],
    )
    volume_slider.grid(row=4, column=0, columnspan=2, sticky="ew")
    update_volume(0)

    play_label = ttk.Label(frame, text="Playing")
    play_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

    channel_spinbox = ttk.Spinbox(
        frame, from_=0, to=9, width=5,
    )

    def on_channel_change(*args):
        try:
            val = int(channel_spinbox.get())
            if 0 <= val <= 9:
                state["data_key"] = val
        except tk.TclError:
            print("error")

    channel_spinbox.grid(row=6, column=0, pady=(16, 0), sticky="w")
    channel_spinbox.set(state["data_key"])
    channel_spinbox.bind("<<Increment>>", on_channel_change)
    channel_spinbox.bind("<<Decrement>>", on_channel_change)
    channel_spinbox.bind("<FocusOut>", on_channel_change)
    channel_spinbox.bind("<Return>", on_channel_change)

    on_channel_change()

    def on_enter(event=None):
        i = state["enter_counter"] % 2
        state["enter_counter"] += 1

        data[state["data_key"]][frequency_list[state["frequency_i"]]][i] = state["volume"]

        if i != 0:
            state["frequency_i"] += 1
            if state["frequency_i"] >= len(frequency_list):
                state["frequency_i"] = 0
            freq_slider.set(state["frequency_i"])
        volume_slider.set(1 if i != 0 else 0)
        update_volume(volume_slider.get())
        update_freq(freq_slider.get())
        update_plot()

    root.bind("<Return>", on_enter)
    root.bind("<KP_Enter>", on_enter)
    enter_button = ttk.Button(frame, text="Enter", command=on_enter)
    enter_button.grid(row=7, column=0, columnspan=2, pady=(16, 0), sticky="ew")

    close_button = ttk.Button(frame, text="Close", command=on_close)
    close_button.grid(row=8, column=0, columnspan=2, pady=(8, 0), sticky="ew")


    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)

    try:
        stream = sd.OutputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS,
            callback=audio_callback, dtype="float32",
        )
        stream.start()
    except Exception as exc:
        messagebox.showerror(title="Audio Error", message=f"Could not start audio output: {exc}")
        root.destroy()
        raise

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()