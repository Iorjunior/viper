"""Unit tests for pipeline processing stages."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from viper.backends.stt.base import Segment, Transcription
from viper.engine.assets import AudioAsset, BaseAsset, VideoAsset
from viper.stages.audio import extract_audio, separate_vocals
from viper.stages.source import download_video, load_local_file
from viper.stages.speech import merge_segments, synthesize, transcribe
from viper.stages.text import translate
from viper.stages.video import convert_video, render_video


def test_source_download_video(tmp_path: Path) -> None:
    expected_video = tmp_path / 'video.mp4'
    expected_video.write_bytes(b'video')

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        'id': '123',
        'title': 'Test Video',
        'duration': 42.0,
    }
    mock_ydl.prepare_filename.return_value = str(expected_video)

    with patch('yt_dlp.YoutubeDL') as mock_ydl_cls:
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
        result = download_video(
            url='https://youtube.com/watch?v=123',
            output_dir=tmp_path,
        )

        assert 'video' in result
        video_asset = result['video']
        assert isinstance(video_asset, VideoAsset)
        assert video_asset.path == expected_video


def test_source_load_local_file(tmp_path: Path) -> None:
    sample_file = tmp_path / 'test.mp4'
    sample_file.write_bytes(b'data')

    result = load_local_file(path=sample_file)
    assert 'file' in result
    assert isinstance(result['file'], BaseAsset)
    assert result['file'].path == sample_file

    with pytest.raises(FileNotFoundError):
        load_local_file(path=tmp_path / 'non_existent.mp4')


def test_audio_extract_audio(tmp_path: Path) -> None:
    video_file = tmp_path / 'source.mp4'
    video_file.write_bytes(b'fake_video')
    out_audio = tmp_path / 'out.wav'

    with patch('subprocess.run') as mock_subproc:
        mock_subproc.return_value = MagicMock(returncode=0)
        # Create destination so AudioAsset validation sees it
        out_audio.write_bytes(b'fake_wav')

        result = extract_audio(
            video=video_file,
            output_path=out_audio,
            sample_rate=24000,
        )

        assert 'audio' in result
        assert isinstance(result['audio'], AudioAsset)
        assert result['audio'].path == out_audio
        assert result['audio'].sample_rate == 24000


def test_audio_separate_vocals(tmp_path: Path) -> None:
    audio_file = tmp_path / 'mix.wav'
    audio_file.write_bytes(b'mix')

    vocals_file = tmp_path / 'vocals.wav'
    vocals_file.write_bytes(b'vocals')
    accompaniment_file = tmp_path / 'accompaniment.wav'
    accompaniment_file.write_bytes(b'accompaniment')

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        result = separate_vocals(
            audio=audio_file,
            output_dir=tmp_path,
        )

        assert 'vocals' in result
        assert 'accompaniment' in result
        assert isinstance(result['vocals'], AudioAsset)
        assert isinstance(result['accompaniment'], AudioAsset)


def test_speech_transcribe(tmp_path: Path) -> None:
    audio_file = tmp_path / 'speech.wav'
    audio_file.write_bytes(b'audio')

    mock_stt = MagicMock()
    mock_stt.transcribe.return_value = Transcription(
        language='en',
        segments=[
            Segment(start=0.0, end=1.5, text='Hello'),
            Segment(start=1.6, end=3.0, text='world'),
        ],
    )

    with patch('viper.stages.speech.get_stt', return_value=mock_stt):
        result = transcribe(audio=audio_file, language='en')

        assert 'transcription' in result
        assert 'segments' in result
        assert 'text' in result
        assert len(result['segments']) == 2
        assert result['text'] == 'Hello world'


def test_speech_synthesize(tmp_path: Path) -> None:
    out_wav = tmp_path / 'tts.wav'

    mock_tts = MagicMock()
    mock_tts.sample_rate = 24000

    def fake_synthesize(
        text: str, destination: Path, **kwargs: object
    ) -> None:
        destination.write_bytes(b'audio_bytes')

    mock_tts.synthesize.side_effect = fake_synthesize

    with patch('viper.stages.speech.get_tts', return_value=mock_tts):
        result = synthesize(
            text='Hello viper',
            output_path=out_wav,
            voice='pf_dora',
        )

        assert 'audio' in result
        assert isinstance(result['audio'], AudioAsset)
        assert result['audio'].path == out_wav
        assert out_wav.exists()


def test_speech_merge_segments() -> None:
    input_segments = [
        Segment(start=0.0, end=1.0, text='Hello'),
        Segment(start=1.2, end=2.0, text='world!'),
        Segment(start=5.0, end=6.0, text='Next sentence.'),
    ]

    result = merge_segments(segments=input_segments, max_gap=0.5)
    merged = result['segments']

    assert len(merged) == 2
    assert merged[0].text == 'Hello world!'
    assert merged[0].start == 0.0
    assert merged[0].end == 2.0
    assert merged[1].text == 'Next sentence.'


def test_text_translate() -> None:
    mock_llm = MagicMock()
    mock_llm.translate.return_value = ['Olá', 'mundo']

    with patch('viper.stages.text.get_llm', return_value=mock_llm):
        result = translate(
            texts=['Hello', 'world'],
            target_language='pt-BR',
        )

        assert 'translated_texts' in result
        assert result['translated_texts'] == ['Olá', 'mundo']


def test_video_render_video(tmp_path: Path) -> None:
    video_file = tmp_path / 'in.mp4'
    video_file.write_bytes(b'video')
    audio_file = tmp_path / 'in.wav'
    audio_file.write_bytes(b'audio')
    out_video = tmp_path / 'out.mp4'

    with patch('subprocess.run') as mock_subproc:
        mock_subproc.return_value = MagicMock(returncode=0)
        out_video.write_bytes(b'rendered')

        result = render_video(
            video=video_file,
            audio=audio_file,
            output_path=out_video,
        )

        assert 'video' in result
        assert isinstance(result['video'], VideoAsset)
        assert result['video'].path == out_video


def test_video_convert_video(tmp_path: Path) -> None:
    video_file = tmp_path / 'in.mov'
    video_file.write_bytes(b'mov')
    out_video = tmp_path / 'in.mp4'

    with patch('subprocess.run') as mock_subproc:
        mock_subproc.return_value = MagicMock(returncode=0)
        out_video.write_bytes(b'mp4')

        result = convert_video(
            video=video_file,
            output_format='mp4',
            output_path=out_video,
        )

        assert 'video' in result
        assert isinstance(result['video'], VideoAsset)
        assert result['video'].path == out_video
