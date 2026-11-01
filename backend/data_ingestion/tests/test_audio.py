import pytest

from data_ingestion.transcribers.base import AudioTranscriptionError
from data_ingestion.transcribers.mock import MockAudioTranscriber
from data_ingestion.transcribers.manager import AudioTranscriberManager


@pytest.mark.parametrize("ext", [
    "audio.mp3",
    "meeting.wav",
    "voicenote.m4a",
    "recording.ogg",
    "call.webm",
    "interview.flac",
])
def test_transcriber_manager_supports_all_audio_extensions(ext):
    manager = AudioTranscriberManager(provider="mock")
    dummy_audio = b"ID3\x03\x00\x00\x00DUMMY_AUDIO_STREAM_BYTES"
    res = manager.transcribe(dummy_audio, ext)

    assert res.transcript is not None
    assert len(res.transcript) > 0
    assert res.word_count > 0
    assert res.provider_used == "mock_transcriber"


def test_mock_transcriber_custom_text():
    custom_msg = "Confirmed launch deadline is December 15, 2026. All blockers resolved."
    transcriber = MockAudioTranscriber(fixed_text=custom_msg)
    res = transcriber.transcribe(b"SOME_AUDIO_BYTES", "note.mp3")

    assert res.transcript == custom_msg
    assert res.audio_format == "mp3"
    assert res.duration_seconds == 30.0


def test_empty_audio_bytes_rejected():
    manager = AudioTranscriberManager(provider="mock")
    with pytest.raises(AudioTranscriptionError) as exc_info:
        manager.transcribe(b"", "empty.mp3")
    assert "empty" in str(exc_info.value).lower()


def test_unsupported_audio_extension_rejected():
    manager = AudioTranscriberManager(provider="mock")
    with pytest.raises(AudioTranscriptionError) as exc_info:
        manager.transcribe(b"VIDEO_CONTENT", "movie.mp4")
    assert "unsupported audio format '.mp4'" in str(exc_info.value).lower()
