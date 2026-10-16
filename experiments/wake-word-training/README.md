# Custom wake-word experiment

Status: Windows dependency combination checked; no custom wake asset or pilot
accuracy qualification is supplied. Push to talk remains available. Training is
an offline experiment, never an automatic download or runtime install.

On Windows 11 build 26200, Python 3.12.14, an isolated environment passed imports,
`uv pip check` and a CPU ONNX Identity inference with openwakeword 0.6.0,
numpy 2.5.4, onnxruntime 1.31.0, scipy 1.18.1 and scikit-learn 1.9.1.
This does not establish custom model compatibility, microphone performance or
recognition accuracy. Install optional extras `voice,wake` only on this qualified
Windows/Python combination; other platforms and combinations need qualification.

Keep all training audio, generated audio, feature arrays and models outside Git.
Use a separate asset directory, including the two upstream feature ONNX assets.
Record source URLs, licenses, consent, collection conditions, speakers, language,
augmentation, generator/version/seeds and train/validation/test split for every
training source. No speaker or duplicate recording may cross the held-out split.
Record the upstream training commit, configuration, output hashes and feature
model versions. The JSON templates intentionally contain unusable placeholders.
They are configuration/provenance scaffolding, not a trained model.

Collect at least 100 unique labelled held-out positive clips and 7200 seconds of
realistic negative recordings, including TV, background speakers, near misses,
assistant speech and ordinary laptop noise. Do not substitute repeated silence,
training samples or synthetic fixtures. Evaluate threshold changes on validation
audio before freezing the test configuration. Record results by condition and
speaker. This pilot requires recall >=90% and <=1 false activation/hour; these are
local acceptance targets, not upstream performance guarantees.

Run `evaluate.py CONFIG CORPUS OUTPUT` with an environment containing the backend
and wake extra. It consumes local mono 16 kHz PCM16 WAV files only. It verifies
unique hashes/provenance, calculates clip recall and negative-audio false
activations, and binds results to the exact configuration. Review the corpus,
permissions and results before setting `human_reviewed` to true in the output.
This local evidence file is trusted operator input, not a cryptographic attestation.
Set `VICTUS_WAKE_MANIFEST_PATH` to that reviewed output outside Git, restart, and
explicitly press Enable wake listening. Listening never starts on service boot.

Wake opens a six-second capture window by default. STT review and explicit task
submission remain mandatory. Python owns both streams, releasing wake capture
before command capture; push to talk disables the listener before recording.
Stop, playback suppression, disconnect and queue overflow stop detection safely.
Raw wake frames stay in a bounded transient queue and are not written to disk.

Sources: [openWakeWord v0.6.0](https://github.com/dscripka/openWakeWord/tree/v0.6.0),
[ONNX model interface](https://github.com/dscripka/openWakeWord/blob/v0.6.0/openwakeword/model.py).
