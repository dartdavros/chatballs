# Dictation and answer playback through SpeechKit

Add Yandex SpeechKit in provider settings. Enter a name, Yandex Cloud folder
and a service account API key with speech recognition access. The key is
encrypted at rest and is never returned to the browser after saving.
The recognition check makes a real STT v3 request containing a short silence;
it verifies API access. Use dictation to verify actual recognition quality.

Select the recognition provider independently in the agent card. An empty
selection inherits the answer provider if it supports STT. An explicitly
selected broken connection never falls back. Model precedence is agent,
connection, then adapter default: `general` for SpeechKit and `whisper-1` for
the previous compatible STT. SpeechKit is unavailable for chat or embeddings.
Recognition uses the organization language unless an agent language is chosen.

In WEB settings choose microphone off, voice message or dictation. Existing
voice permissions are preserved; dictation is never enabled automatically.
Defaults are 10 MiB and 60 seconds. Both limits may be reduced. Size applies
to both WEB recording modes, duration applies to dictation. Other channels
keep their limits. Dictation requires a configured AI agent.

Visitors confirm the current consent and required form. Old browser tokens
and localStorage flags do not prove consent. Changing the consent version
or form schema requires confirmation again.

The microphone requests browser permission. Stopping recognizes audio and
appends text to the current draft, preserving edits made while waiting.
Only the regular send action or Enter sends a message. Shift+Enter inserts
a newline; Escape cancels dictation. Text above the send limit is retained
in full and must be shortened. Errors allow retrying the in-memory recording,
cancelling or continuing with ordinary typing.

Recording stops at the first size or duration limit. The backend independently
checks actual bytes, container and decoded duration. It handles WebM/Opus,
Ogg/Opus and MP4 through FFmpeg pipes and ignores claimed MIME and duration.
FFmpeg is included in the backend images; no bucket or additional service is
required. Starting recording stops playback.

Dictation audio and results use bounded request/widget memory. Dictation
creates no conversation, message, AI turn or durable queue entry. It stores
no recording in history, persistent storage or diagnostic logs. Cancellation,
session change and leaving the widget release buffers. An explicitly sent
voice message retains its original recording and operator handoff on STT failure.

SpeechKit receives original audio under Yandex Cloud processing and storage
terms. No Chatballs storage does not imply no provider storage. STT v3 creates
an external operation. Chatballs bounds its wait and attempts DeleteRecognition
cleanup. Network failures cannot guarantee deletion; losing the creation
response can leave the operation ID unknown. The key owner pays the provider
directly.

For playback, separately select the agent's synthesis provider, optional model
and voice. An empty connection or voice disables TTS; text and STT providers are
never inherited. Enable “Allow AI answer playback” in WEB. Enabling it adds the
accepted disclosure about sending answer text, including possible personal data,
to SpeechKit. Previously confirmed consent without that disclosure is no longer
current. The synthesis check makes its own real TTS request.

“Listen” beside a saved AI answer starts synthesis. Pause, resume, replay and
the square stop button control playback. Recording stops and hides the player.
Staff replies, internal records, system events and unfinished answers cannot be
synthesized. Formatted replies use their saved plain text, without HTML, CSS or
formatting instructions.

The voice is never automatically replaced. An incompatible language shows an
error beside the answer. Language is inferred from saved text; short ambiguous
answers may be rejected when a compatible language cannot be determined.
SpeechKit v3 receives sequential parts of up to 1000
characters with unsafeMode (its documented limit is 5000). PCM parts join into
one in-memory WAV; partial results are never offered. Limits are 180 seconds,
100,000 input characters and 64 MiB of audio. Exceeding them produces an error
without truncating the answer. There is no pre-generation or autoplay.

Replay uses current-widget memory; concurrent requests for an answer join the
same flight. Keys include session, message, text and TTS settings. Session or
settings changes, history reset and unmount release buffers and object URLs.
Reload may require synthesis again. No persistent TTS cache or new audio message
is created. Failure leaves typing available and never hands the conversation to
an operator.

[SpeechKit documentation](https://aistudio.yandex.ru/en/docs/speechkit/stt/transcribation)
states that recognition results are stored for three days and queueing can take
a long time. Chatballs attempts earlier deletion but cannot guarantee it when
the request outcome is unknown. Local waiting is bounded; after a timeout,
retry the available recording or continue typing.

Actual verification and remaining limitations are recorded in
`docs/verification/T-178/README.md`. This guide does not replace live SpeechKit
acceptance, including a 60-second recording.

Playback verification and actual outcomes: `docs/verification/T-179/README.md`.
