# M6 voice setup and labelled evaluation

The implementation adds Python-owned capture, local English transcription, explicit transcript review and interruptible Windows SAPI spoken results. The current task service accepts `fs.create_note`, so voice input supports the same note operation. Voice cannot resolve action approvals or call desktop/file adapters directly.

## Enable voice

Install the optional `voice` dependencies into the existing backend environment if needed (`uv sync --extra voice --group dev` from `backend`). Configure an **already downloaded CTranslate2 faster-whisper model directory** containing `model.bin`, `config.json`, tokenizer and vocabulary assets. No model-name download fallback is allowed.

From the project root in PowerShell, set the variable in the terminal that starts the backend:

```powershell
$env:VICTUS_VOICE_MODEL_PATH = 'C:/local-models/faster-whisper-base.en'
$env:VICTUS_EMERGENCY_HOTKEY = '1'
./backend/.venv/Scripts/victus.exe serve
```

Use the existing session token and dashboard instructions. The backend does not automatically load `.env` files. Missing model configuration leaves voice disabled. A bad/incomplete local model reports an error on transcription without attempting a download. Microphone permission/device availability is checked when the user starts recording, not by opening a device during service startup. The emergency shortcut remains on its independent thread; the dashboard Stop and shortcut trip the same task and voice cancellation paths.

In the dashboard, activate **Start recording**, speak, then activate **Finish recording**. Both work with keyboard focus and Enter/Space. This is a two-activation push-to-talk control; there is no always-on listening or browser microphone stream. Capture also finishes automatically on silence or the duration limit. Read the transcript, correct **Reviewed filename** and **Reviewed note text**, and choose **Submit reviewed transcript**. Example: `create note reminder.txt with text bring the notebook`. Dictation that does not identify an exact supported target asks for correction rather than guessing.

A reload restores the current in-memory voice snapshot and never submits it. Transcripts are not saved across backend restarts. After a task finishes, its short summary appears in the dashboard; only an acknowledgement of that displayed revision allows speech. Use **Mute spoken results**, **Cancel voice / interrupt speech**, or **Stop all work** as needed. Cancelling voice after submission interrupts voice handling but does not cancel the queued task; **Stop all work** stops tasks as well. Cancel the completed voice session before starting another recording.

## Bounds and handling

- Microphone: one exclusive Python `RawInputStream`, mono PCM16 at 16 kHz, 20 ms frames, at most 20 seconds / 640,000 PCM bytes retained in a ring. Driver overflow or loss fails the capture. Failed driver closure retains ownership to prevent a competing stream.
- Activity gate: RMS energy threshold 0.012; 4 seconds of initial silence or 1.5 seconds after activity ends capture, with a hard 20-second ceiling. This is an activity gate, not a calibrated speech/speaker detector. Whisper also uses its VAD filter.
- Audio conversion accepts PCM16 mono/stereo and bounded sample rates; float conversion clips finite samples. Resampling uses linear interpolation; production capture is already 16 kHz, so it takes an identity conversion. Acoustic quality at other sample rates needs separate evaluation.
- STT: CPU/int8, English, local files only, a persistent spawned worker that loads the model once. Model startup and lazy segment consumption are covered by the 90-second operation deadline. Stop/deadline terminates the worker; later sessions create a new one. Inference and device work run outside the ASGI event loop.
- Audio is transferred in memory, never written to a temporary WAV by the service. Buffers are released on completion, cancellation and error. Raw transcript/proposal text is ephemeral, available only through authenticated voice snapshots, and cleared on submission, cancellation, expiry or error. The existing task service retains reviewed action data according to its own protected payload policy. Python/native allocator memory is not claimed to be cryptographically erased.
- Review expires after 120 seconds. Submission requires the current session/revision and explicit human review, and uses a session-bound task idempotency key. STT likelihood is never approval authority.
- Result observation is bounded to 180 seconds; display acknowledgement expires after 30 seconds. Speech is limited to 240 characters and 20 seconds, uses literal text rather than XML, and can be interrupted. Wake detection/capture is suppressed during playback and a 750 ms echo cooldown. Wake-word detection itself is deferred to M7.

## The required acoustic test set

`manifest.template.json` contains **unrecorded label placeholders**, not measured results: 50 quiet command labels, 50 noisy command labels, and initial silence/background/assistant-speech negatives. Copy it outside the repository with the corresponding recordings and correct the references to what was actually spoken. Use opaque sample IDs; consented recordings may contain personal audio and should stay outside Git.

Record each of the 50 commands twice: once quiet and once with realistic, documented noise. Include varied filenames/content, near-sounding targets and ambiguous targets; label the intended target before inspecting STT output. Do not tune and report on the same test split. Add several silence clips, unrelated background conversations, and assistant-output clips, including assistant speech played through the actual speakers. Templates alone cannot establish accuracy.

Each manifest row has `id`, `condition`, `language` (`en` only), `audio` (relative PCM16 WAV path), `reference` (verbatim reference speech), `intent` (`fs.create_note` or null), and `target` (exact filename or null). WAVs must be at most 30 seconds and 8–48 kHz mono/stereo. Audio negative conditions use null intent and target. A background voice that says a valid command can still produce a proposal; explicit human review is the execution boundary, not the acoustic classifier.

Run from the project root:

```powershell
./backend/.venv/Scripts/python.exe -m victus.voice.evaluation --manifest C:/private-voice-test/manifest.json --model C:/local-models/faster-whisper-base.en --output .local/m6-acoustic-report.json
```

The runner loads the local model once and produces per-condition word error rate, intent accuracy and exact-target accuracy **separately**, plus a count of negative clips that produced proposals. It emits opaque IDs and aggregate/count metrics, not recognized/reference text or audio paths. Empty-reference WER is undefined and reported as null; insertion counts remain available. It never submits a task. It requires exactly 50 quiet and 50 noisy labels and each audio-negative category. It rejects non-English labels: Hindi and mixed-language support need separate labelled sets and adapters/settings qualification.

Also perform an observed device/UI protocol, because WAV inference does not test hardware capture:

1. Unplug/disable the active input while recording. Confirm capture closes, the UI shows a disconnected/error state, no transcript is submitted, and reconnect requires a fresh recording.
2. Press Stop during recording, transcribing, review, task execution and speaking; confirm no late transcript/submission/speech occurs. Test Ctrl+Alt+Pause while SAPI is speaking as well as keyboard-only dashboard Stop.
3. During actual assistant playback, try to start capture and any future wake detector. Confirm both remain suppressed through playback/cooldown. Verify this with real speakers/headphones; offline assistant-audio clips alone do not qualify echo behavior.
4. Mute/interrupt SAPI and confirm audible speech stops promptly. Record actual device, driver, model revision, conditions, dates and observed outcome without storing private speech in audit logs.

## Automated evidence, 2026-10-16

The implementation has automated tests for capture ownership/bounds, VAD timeouts, driver loss, transcript parsing/review, expiry, duplicate/stale submissions, cancellation from every relevant state, persistent STT/deadline shutdown, SAPI COM/flags with a fake voice, mute, echo suppression, result-display acknowledgement and shared verified note creation.

- Backend regression: 539 tests passed; XML at `.local/m6-regression.xml`. Later refinements received a separate 89-test focused rerun, all passed, recorded in `.local/m6-qualified.xml`; the final worker-cleanup adjustment also passed its four focused process tests.
- Frontend: build/type generation, 20 tests and lint passed.
- M6 Chromium fixtures: keyboard recording controls, review/reload protection, duplicate clicks, literal transcript rendering, display-before-speech acknowledgement, mute, keyboard Stop and 390px mobile overflow passed. Report/screenshots: `.local/m6-browser/`.
- Existing M5 Chromium task/approval checks still pass.
- An already-downloaded `faster-whisper-base.en` model loaded locally on CPU/int8, reused one worker for two synthetic-silence calls and rejected silence; `.local/m6-local-stt.json` records this limited smoke check.
- Changed Python files pass Ruff. A broad repository Ruff check also found four existing lint issues in untouched storage/browser/desktop files; those were not changed as part of M6.

**The 50 quiet / 50 noisy acoustic evaluation, physical microphone disconnect, audible SAPI/shortcut and real speaker echo checks have not been run. No Hindi/mixed-language accuracy claim is made.**

Reference implementation APIs were checked against the [faster-whisper documentation](https://github.com/SYSTRAN/faster-whisper), [sounddevice raw streams](https://python-sounddevice.readthedocs.io/en/latest/api/raw-streams.html), and [Microsoft SAPI Speak documentation](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms723609(v=vs.85)).
