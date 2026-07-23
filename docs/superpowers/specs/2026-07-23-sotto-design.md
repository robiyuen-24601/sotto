# sotto: local push-to-talk dictation for macOS

**Date:** 2026-07-23
**Status:** Approved design, pre-implementation
**Owner:** Rob

## Purpose

A free, fully local replacement for Wispr Flow. Hold Right Option anywhere on
macOS, speak, release; cleaned-up text is inserted into whatever field had
focus. No subscription, no audio leaving the machine.

## Requirements

- Trigger: hold-to-talk on Right Option (keycode 61). Release ends the
  dictation. Holds under 0.3s are discarded as accidental taps. Pressing any
  other key while holding cancels the recording (the user was using Option as
  a modifier).
- Output: transcription cleaned by a small local LLM (filler words and false
  starts removed, punctuation and casing fixed, meaning unchanged). Cleanup
  can be toggled off from the menu bar.
- Works in any app: insertion must land in the focused text field regardless
  of application.
- English only.
- Feedback: menu bar icon with idle / recording / processing states, plus
  subtle system sounds on record start and stop.
- Fully offline after first-run model download. Zero recurring cost.
- Target machine: Apple M5 Pro, 24GB RAM, macOS 26.x.

## Architecture

One resident Python process (a daemon) started at login via LaunchAgent.
All components live in this process so both ML models stay loaded and warm.

```
Right Option down ─▶ Recorder starts (mic, 16kHz mono, in-memory)
Right Option up   ─▶ Recorder stops
                     └▶ Parakeet ASR (parakeet-mlx) ─▶ raw transcript
                        └▶ LLM cleanup (mlx-lm, Qwen3-4B 4-bit) ─▶ text
                           └▶ Injector: clipboard-paste into focused app
```

### Components

1. **Hotkey listener.** Quartz `CGEventTap` on `flagsChanged` (and `keyDown`
   for the cancel-on-other-key rule) watching Right Option. Runs on the main
   run loop. Emits start/stop/cancel events to the worker.
2. **Recorder.** `sounddevice` InputStream, default microphone, 16kHz mono,
   buffered in memory only. Nothing is written to disk.
3. **ASR.** `parakeet-mlx` running NVIDIA Parakeet TDT 0.6b v2. Model loaded
   once at startup. Expected inference: ~100-300ms per utterance.
4. **Cleanup.** `mlx-lm` running Qwen3-4B-Instruct 4-bit with a fixed system
   prompt: remove filler words and false starts, fix punctuation and casing,
   change nothing else, output only the cleaned text.
   Guard: if the LLM output is empty, or its length deviates wildly from the
   raw transcript (outside roughly 0.5x to 2x), fall back to the raw
   transcript. Config allows swapping in Qwen3-1.7B for lower RAM.
5. **Injector.** Save current clipboard contents, place text on the
   clipboard, synthesize Cmd+V via `CGEvent`, restore the previous clipboard
   after a short delay. Paste is chosen over simulated keystrokes because it
   is instant and reliable across apps.
6. **Menu bar UI.** `rumps` app owning the main thread. Icon states: idle,
   recording, processing. Menu items: last transcript (click to re-copy),
   cleanup on/off, pause listening, quit. Start/stop/error sounds via system
   audio (NSSound or afplay).

### Process model

- Main thread: AppKit / rumps event loop plus the event tap.
- Worker thread: record, transcribe, cleanup, inject. The UI never blocks.
- Only one dictation in flight at a time; a new keydown while processing is
  ignored (with an error sound).

## Error handling

- The daemon never exits on a pipeline failure. Any exception in the worker
  is caught, logged, and surfaced as an error sound plus a brief menu bar
  state.
- Logs to `~/Library/Logs/sotto.log` (rotating, no audio content logged;
  transcripts logged only at debug level, off by default).
- If the event tap is disabled by the OS (timeout or user revokes
  Accessibility), the daemon detects it, attempts re-enable, and shows a
  distinct menu bar error state.

## Configuration

`config.toml` in the project root (path resolvable via env var), covering:
hotkey keycode, ASR model id, LLM model id, cleanup enabled default, minimum
hold duration, sound choices, log level.

## Footprint and latency

- Resident RAM: ~4GB (Parakeet ~1.2GB, Qwen3-4B 4-bit ~2.3GB, Python ~0.4GB).
- First run downloads ~3GB of models from Hugging Face; offline thereafter.
- Expected release-to-paste latency: under 1 second for typical utterances
  (cleanup generation dominates).

## Permissions and install

- Microphone and Accessibility permissions attach to the venv's Python
  binary. Setup includes a step to trigger and approve both prompts once.
- Installed as a LaunchAgent
  (`~/Library/LaunchAgents/com.robertyuen.sotto.plist`) pointing at the venv
  Python. `launchctl` load/unload wrapped in small `make` targets or scripts.
- Environment: `uv`-managed venv, Python 3.12+, dependencies:
  `parakeet-mlx`, `mlx-lm`, `sounddevice`, `rumps`, `pyobjc`.

## Testing

- Unit tests (pytest, macOS APIs mocked):
  - hotkey state machine: tap-too-short discard, cancel on other key,
    ignore-while-processing;
  - LLM output guard: empty output, runaway length, normal case;
  - injector sequencing: clipboard save, set, paste, restore ordering.
- Manual QA checklist for the end-to-end path (real mic, real hotkey):
  dictate into TextEdit, a browser text area, and a terminal; verify
  clipboard restoration; verify cancel-on-other-key; verify pause and quit.

## Out of scope (v1)

- Multilingual support.
- Streaming/live transcription while speaking.
- Custom vocabulary or per-app dictionaries.
- A native Swift app (a later rewrite is straightforward if wanted; the
  pipeline design transfers one-to-one).
