import pytest

from data_ingestion.config import ingestion_settings
from data_ingestion.transcribers.base import AudioTranscriptionError
from data_ingestion.transcribers.mock import MockAudioTranscriber
from data_ingestion.transcribers.manager import AudioTranscriberManager


# -------------------------------------------------------------------
# Core 3 Formats: MP3, WAV, M4A
# -------------------------------------------------------------------
def test_transcribe_valid_mp3():
    # ID3v2 header
    valid_mp3 = b"ID3\x03\x00\x00\x00\x00\x00#DUMMY_MP3_STREAM_PAYLOAD_DATA"
    manager = AudioTranscriberManager(provider="mock")
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True

    res = manager.transcribe(valid_mp3, "standup.mp3")
    assert res.audio_format == "mp3"
    assert len(res.transcript) > 0
    assert res.provider_used == "mock_transcriber"


def test_transcribe_valid_wav():
    # RIFF....WAVE header
    valid_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00"
    manager = AudioTranscriberManager(provider="mock")
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True

    res = manager.transcribe(valid_wav, "meeting.wav")
    assert res.audio_format == "wav"
    assert len(res.transcript) > 0


def test_transcribe_valid_m4a():
    # ISO ftyp header for M4A
    valid_m4a = b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00M4A mp42isom"
    manager = AudioTranscriberManager(provider="mock")
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True

    res = manager.transcribe(valid_m4a, "voicenote.m4a")
    assert res.audio_format == "m4a"
    assert len(res.transcript) > 0


# -------------------------------------------------------------------
# Error Case: Missing Transcription Credentials in Production
# -------------------------------------------------------------------
def test_missing_credentials_raises_error_and_never_returns_fake():
    """
    Critical verification: When credentials are missing and test mocking is disabled,
    it must return a clear processing error and NEVER pretend transcription succeeded.
    """
    saved_mock_flag = ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER
    saved_openai_key = ingestion_settings.OPENAI_API_KEY
    saved_gemini_key = ingestion_settings.GEMINI_API_KEY

    try:
        ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = False
        ingestion_settings.OPENAI_API_KEY = ""
        ingestion_settings.GEMINI_API_KEY = ""

        manager = AudioTranscriberManager(provider="auto")
        valid_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00"

        with pytest.raises(AudioTranscriptionError) as exc_info:
            manager.transcribe(valid_wav, "client_call.wav")

        assert "unavailable" in str(exc_info.value).lower()
        assert "neither openai_api_key nor gemini_api_key is configured" in str(exc_info.value).lower()
    finally:
        ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = saved_mock_flag
        ingestion_settings.OPENAI_API_KEY = saved_openai_key
        ingestion_settings.GEMINI_API_KEY = saved_gemini_key


# -------------------------------------------------------------------
# Error Cases: MIME / Audio Header Mismatches
# -------------------------------------------------------------------
def test_mime_mismatch_mp3_containing_plain_text():
    fake_mp3 = b"This is plain text with an .mp3 extension, not valid audio."
    manager = AudioTranscriberManager(provider="mock")
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True

    with pytest.raises(AudioTranscriptionError) as exc_info:
        manager.transcribe(fake_mp3, "spoofed.mp3")
    assert "mime/format mismatch" in str(exc_info.value).lower()


def test_mime_mismatch_wav_containing_plain_text():
    fake_wav = b"This is plain text with a .wav extension."
    manager = AudioTranscriberManager(provider="mock")
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True

    with pytest.raises(AudioTranscriptionError) as exc_info:
        manager.transcribe(fake_wav, "spoofed.wav")
    assert "mime/format mismatch" in str(exc_info.value).lower()


def test_mime_mismatch_m4a_containing_plain_text():
    fake_m4a = b"This is plain text with an .m4a extension."
    manager = AudioTranscriberManager(provider="mock")
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True

    with pytest.raises(AudioTranscriptionError) as exc_info:
        manager.transcribe(fake_m4a, "spoofed.m4a")
    assert "mime/format mismatch" in str(exc_info.value).lower()


# -------------------------------------------------------------------
# Error Cases: Empty and Unsupported
# -------------------------------------------------------------------
def test_empty_audio_bytes_rejected():
    manager = AudioTranscriberManager(provider="mock")
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True

    with pytest.raises(AudioTranscriptionError) as exc_info:
        manager.transcribe(b"", "empty.mp3")
    assert "empty" in str(exc_info.value).lower()


def test_unsupported_audio_extension_rejected():
    manager = AudioTranscriberManager(provider="mock")
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True

    with pytest.raises(AudioTranscriptionError) as exc_info:
        manager.transcribe(b"RIFF\x24\x00\x00\x00WAVEfmt ", "video.avi")
    assert "unsupported audio format '.avi'" in str(exc_info.value).lower()
