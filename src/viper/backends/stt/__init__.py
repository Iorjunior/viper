"""Speech-to-Text backend contracts and implementations."""

from viper.backends.stt.base import Segment, STTBackend, Transcription

__all__ = ['STTBackend', 'Segment', 'Transcription']
