# sotto

Local push-to-talk dictation for macOS. Hold **Right Option**, speak,
release. About a second later, clean text appears in whatever app has
focus. No cloud, no subscription, no audio leaving your machine.

Named for *sotto voce*: speaking under your breath.

## How it works

One resident Python process:

```
hold Right Option ──▶ mic capture (16kHz, in memory)
release           ──▶ Parakeet ASR (parakeet-mlx, ~100-300ms)
                      ──▶ LLM cleanup: fillers/punctuation (Qwen3-4B via mlx-lm)
                          ──▶ paste into the focused app (clipboard is restored)
```

A menu bar icon shows state (🎙 idle, 🔴 recording, ⏳ processing) with a
last-transcript entry, a cleanup on/off toggle, and pause. Quick taps are
discarded; pressing any other key while holding cancels (so Option-key
shortcuts still work). Everything runs on Apple Silicon via MLX.

## Requirements

- Apple Silicon Mac, macOS 14+, ~5GB free RAM while running
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)

## Install

```bash
git clone https://github.com/robiyuen-24601/sotto.git
cd sotto
uv sync
make run
```

First run downloads ~3GB of models from Hugging Face, then works fully
offline. Two permission grants are needed, and macOS attributes them to
**whatever launches the process**:

1. Running `make run` from a terminal: grant **Microphone** and
   **Accessibility** to your terminal app (System Settings > Privacy &
   Security).
2. Once it works, install it as a login item:

```bash
make install-agent
```

Under launchd the permissions attach to `.venv/bin/python` instead, so
add that binary under Accessibility and approve the new Microphone prompt,
then `launchctl kickstart -k gui/$(id -u)/com.robertyuen.sotto`.

`make uninstall-agent` removes it; `make logs` tails the app log.

## Configure

Edit `config.toml` (or point `SOTTO_CONFIG` at another file): hotkey
keycode, model ids, cleanup default, sounds, log level. Swap the LLM to
`mlx-community/Qwen3-1.7B-Instruct-4bit` for a ~1GB memory footprint.
Restart the agent to apply.

## Privacy

Audio is captured to RAM only and never written to disk. Transcripts are
logged only at debug level (off by default). Nothing is sent anywhere;
after the first-run model download the whole pipeline is offline.

## Limitations

- English-focused (Parakeet); swap in a multilingual model if you need more.
- Dictating pure silence is a silent no-op by design.
- Holding both Option keys and releasing only the right one can miss the
  release (rare; tap Right Option again to reset).
