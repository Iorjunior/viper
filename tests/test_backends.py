"""Unit tests for backend abstractions and resolver."""

from pathlib import Path
from typing import override
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from viper.backends.llm.base import LLMBackend
from viper.backends.llm.mlx_lm import MlxLmBackend
from viper.backends.llm.openai_compatible import OpenAICompatibleBackend
from viper.backends.resolver import get_llm, get_stt, get_tts
from viper.backends.stt.base import Segment, STTBackend, Transcription
from viper.backends.stt.faster_whisper import FasterWhisperBackend
from viper.backends.stt.mlx_whisper import MlxWhisperBackend
from viper.backends.stt.openai import OpenAISTTBackend
from viper.backends.tts.base import TTSBackend
from viper.backends.tts.kokoro import KokoroBackend
from viper.backends.tts.openai import OpenAITTSBackend


class DummySTT(STTBackend):
    @override
    def transcribe(
        self, path: Path, language: str | None = None
    ) -> Transcription:
        return Transcription(
            language='en',
            segments=[Segment(start=0.0, end=1.5, text='Hello world')],
        )


class DummyLLM(LLMBackend):
    @override
    def translate(
        self,
        segments: list[str],
        target_language: str,
        durations: list[float] | None = None,
    ) -> list[str]:
        return [f'{s} in {target_language}' for s in segments]

    @override
    def generate(self, prompt: str, system: str = '') -> str:
        return f'generated: {prompt}'


class DummyTTS(TTSBackend):
    sample_rate: int = 24000

    @override
    def synthesize_raw(self, text: str, **kwargs) -> np.ndarray:
        return np.zeros(2400, dtype=np.float32)


def test_stt_base_contract(tmp_path: Path) -> None:
    backend = DummySTT()
    dummy_file = tmp_path / 'audio.wav'
    dummy_file.write_bytes(b'dummy')

    result = backend.transcribe(dummy_file, language='en')
    assert isinstance(result, Transcription)
    assert result.language == 'en'
    assert len(result.segments) == 1
    assert result.segments[0].start == 0.0
    assert result.segments[0].end == 1.5
    assert result.segments[0].text == 'Hello world'


def test_llm_base_contract() -> None:
    backend = DummyLLM()
    translated = backend.translate(['Hello'], target_language='pt-BR')
    assert translated == ['Hello in pt-BR']

    generated = backend.generate('Say hi', system='You are a bot')
    assert generated == 'generated: Say hi'


def test_tts_base_contract(tmp_path: Path) -> None:
    backend = DummyTTS()
    raw = backend.synthesize_raw('Hello')
    assert isinstance(raw, np.ndarray)
    assert len(raw) == 2400

    out_file = tmp_path / 'out.wav'
    with patch('soundfile.write') as mock_sf_write:
        backend.synthesize('Hello', out_file)
        mock_sf_write.assert_called_once()
        args, _ = mock_sf_write.call_args
        assert args[0] == str(out_file)
        assert args[2] == 24000


@patch('viper.backends.resolver.get_config_value')
def test_resolver_stt_explicit(mock_config: MagicMock) -> None:
    mock_config.side_effect = lambda key, default=None: {
        'VIPER_STT_BACKEND': 'faster_whisper',
    }.get(key, default)

    stt = get_stt()
    assert isinstance(stt, STTBackend)
    assert stt.__class__.__name__ == 'FasterWhisperBackend'


@patch('platform.machine', return_value='arm64')
@patch('platform.system', return_value='Darwin')
@patch('viper.backends.resolver.get_config_value')
def test_resolver_stt_auto_apple(
    mock_config: MagicMock, mock_sys: MagicMock, mock_mach: MagicMock
) -> None:
    mock_config.side_effect = lambda key, default=None: {
        'VIPER_STT_BACKEND': 'auto',
    }.get(key, default)

    stt = get_stt()
    assert isinstance(stt, STTBackend)
    assert stt.__class__.__name__ == 'MlxWhisperBackend'


@patch('torch.cuda.is_available', return_value=False)
@patch('platform.system', return_value='Linux')
@patch('viper.backends.resolver.get_config_value')
def test_resolver_stt_auto_cpu(
    mock_config: MagicMock, mock_sys: MagicMock, mock_cuda: MagicMock
) -> None:
    mock_config.side_effect = lambda key, default=None: {
        'VIPER_STT_BACKEND': 'auto',
    }.get(key, default)

    stt = get_stt()
    assert isinstance(stt, STTBackend)
    assert stt.__class__.__name__ == 'FasterWhisperBackend'
    assert getattr(stt, 'device', None) == 'cpu'


@patch('viper.backends.resolver.get_config_value')
def test_resolver_llm_explicit_ollama(mock_config: MagicMock) -> None:
    mock_config.side_effect = lambda key, default=None: {
        'VIPER_LLM_BACKEND': 'ollama',
    }.get(key, default)

    llm = get_llm()
    assert isinstance(llm, LLMBackend)
    assert llm.__class__.__name__ == 'OpenAICompatibleBackend'
    assert str(getattr(llm, 'base_url', '')).endswith('/v1')


@patch('viper.backends.resolver.get_config_value')
def test_resolver_tts_explicit_kokoro(mock_config: MagicMock) -> None:
    mock_config.side_effect = lambda key, default=None: {
        'VIPER_TTS_BACKEND': 'kokoro',
    }.get(key, default)

    tts = get_tts()
    assert isinstance(tts, TTSBackend)
    assert tts.__class__.__name__ == 'KokoroBackend'


@patch('viper.backends.resolver.get_config_value')
def test_resolver_unknown_backend_raises(mock_config: MagicMock) -> None:
    mock_config.side_effect = lambda key, default=None: {
        'VIPER_STT_BACKEND': 'unknown_stt',
    }.get(key, default)

    with pytest.raises(ValueError, match='Unsupported STT backend'):
        get_stt()


def test_faster_whisper_backend(tmp_path: Path) -> None:
    audio_file = tmp_path / 'sample.wav'
    audio_file.write_bytes(b'fake audio')

    mock_segment = MagicMock()
    mock_segment.start = 0.0
    mock_segment.end = 2.0
    mock_segment.text = ' Test faster whisper'

    mock_info = MagicMock()
    mock_info.language = 'en'

    target = 'viper.backends.stt.faster_whisper.WhisperModel'
    with patch(target) as mock_model_cls:
        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = ([mock_segment], mock_info)
        mock_model_cls.return_value = mock_instance

        backend = FasterWhisperBackend(model_size='base', device='cpu')
        result = backend.transcribe(audio_file)

        assert result.language == 'en'
        assert len(result.segments) == 1
        assert result.segments[0].text == 'Test faster whisper'


def test_faster_whisper_import_error(tmp_path: Path) -> None:
    audio_file = tmp_path / 'sample.wav'
    audio_file.write_bytes(b'fake audio')

    backend = FasterWhisperBackend()
    with (
        patch('viper.backends.stt.faster_whisper.WhisperModel', None),
        pytest.raises(ImportError, match='faster-whisper is not installed'),
    ):
        backend.transcribe(audio_file)


def test_openai_compatible_backend_generate() -> None:
    backend = OpenAICompatibleBackend(
        base_url='http://localhost:11434/v1',
        model='qwen2.5:1.5b',
        api_key='ollama',
    )

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = 'Paris'
    mock_client.chat.completions.create.return_value.choices = [mock_choice]

    with patch.object(backend, '_get_client', return_value=mock_client):
        reply = backend.generate('Capital of France?')
        assert reply == 'Paris'


def test_openai_compatible_backend_translate() -> None:
    backend = OpenAICompatibleBackend(
        base_url='http://localhost:11434/v1',
        model='qwen2.5:1.5b',
        api_key='ollama',
    )

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '["Olá mundo"]'
    mock_client.chat.completions.create.return_value.choices = [mock_choice]

    with patch.object(backend, '_get_client', return_value=mock_client):
        translations = backend.translate(
            ['Hello world'], target_language='pt-BR'
        )
        assert translations == ['Olá mundo']


def test_mlx_whisper_backend(tmp_path: Path) -> None:
    audio_file = tmp_path / 'sample.wav'
    audio_file.write_bytes(b'dummy')

    backend = MlxWhisperBackend(model='fake-model')
    fake_result = {
        'language': 'pt',
        'segments': [{'start': 0.0, 'end': 1.0, 'text': 'Olá'}],
    }

    mock_mlx = MagicMock()
    mock_mlx.transcribe.return_value = fake_result
    with patch('viper.backends.stt.mlx_whisper.mlx_whisper', mock_mlx):
        transcription = backend.transcribe(audio_file, language='pt')
        assert transcription.language == 'pt'
        assert len(transcription.segments) == 1
        assert transcription.segments[0].text == 'Olá'


def test_mlx_whisper_import_error(tmp_path: Path) -> None:
    audio_file = tmp_path / 'sample.wav'
    audio_file.write_bytes(b'dummy')
    backend = MlxWhisperBackend()

    with patch('viper.backends.stt.mlx_whisper.mlx_whisper', None):
        with pytest.raises(ImportError, match='mlx-whisper is not installed'):
            backend.transcribe(audio_file)


def test_mlx_lm_backend() -> None:
    backend = MlxLmBackend(model='fake-model')

    with (
        patch(
            'viper.backends.llm.mlx_lm.load',
            return_value=(MagicMock(), MagicMock()),
        ),
        patch(
            'viper.backends.llm.mlx_lm.generate',
            return_value='["Traduzido"]',
        ),
    ):
        gen = backend.generate('prompt')
        assert gen == '["Traduzido"]'

        res = backend.translate(['Original'], target_language='pt-BR')
        assert res == ['Traduzido']


def test_mlx_lm_import_error() -> None:
    backend = MlxLmBackend(model='fake-model')

    with patch('viper.backends.llm.mlx_lm.load', None):
        with pytest.raises(ImportError, match='mlx-lm is not installed'):
            backend.generate('prompt')


def test_kokoro_backend() -> None:
    backend = KokoroBackend()
    assert backend.synthesize_raw('').size == 0

    mock_chunk = np.ones(100, dtype=np.float32)
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [('g', 'p', mock_chunk)]

    with patch.object(backend, '_get_pipeline', return_value=mock_pipeline):
        audio = backend.synthesize_raw('Olá mundo')
        assert isinstance(audio, np.ndarray)
        assert len(audio) == 100


def test_kokoro_import_error() -> None:
    backend = KokoroBackend()

    with patch('viper.backends.tts.kokoro.KPipeline', None):
        with pytest.raises(ImportError, match='kokoro is not installed'):
            backend.synthesize_raw('Olá')


def test_openai_stt_backend(tmp_path: Path) -> None:
    audio_file = tmp_path / 'sample.wav'
    audio_file.write_bytes(b'dummy')
    backend = OpenAISTTBackend(api_key='fake-key')

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.language = 'en'
    mock_response.segments = [{'start': 0.0, 'end': 1.0, 'text': 'Hello'}]
    mock_client.audio.transcriptions.create.return_value = mock_response

    with patch('viper.backends.stt.openai.OpenAI', return_value=mock_client):
        res = backend.transcribe(audio_file)
        assert res.language == 'en'
        assert res.segments[0].text == 'Hello'


def test_openai_tts_backend() -> None:
    backend = OpenAITTSBackend(api_key='fake-key')
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = b'RIFFfakeWAV'
    mock_client.audio.speech.create.return_value = mock_response

    fake_audio = (np.zeros(200, dtype=np.float32), 24000)
    with (
        patch('viper.backends.tts.openai.OpenAI', return_value=mock_client),
        patch('soundfile.read', return_value=fake_audio),
    ):
        raw = backend.synthesize_raw('Hello')
        assert len(raw) == 200
