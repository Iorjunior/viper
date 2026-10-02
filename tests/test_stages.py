"""Unit tests for pipeline processing stages."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from viper.backends.stt.base import Segment, Transcription
from viper.engine.assets import AudioAsset, BaseAsset, VideoAsset
from viper.stages.audio import extract_audio, separate_vocals
from viper.stages.source import download_video, load_local_file
from viper.stages.speech import (
    apply_micro_fades,
    filter_repeats,
    merge_segments,
    synthesize,
    transcribe,
)
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

        assert 'height<=720' in mock_ydl_cls.call_args[0][0]['format']
        assert 'video' in result
        video_asset = result['video']
        assert isinstance(video_asset, VideoAsset)
        assert video_asset.path == expected_video

        # Test with source parameter instead of url
        result_source = download_video(
            source='https://youtube.com/watch?v=123',
            output_dir=tmp_path,
        )
        assert isinstance(result_source['video'], VideoAsset)

        # Test local file bypass without calling yt-dlp
        local_result = download_video(source=str(expected_video))
        assert isinstance(local_result['video'], VideoAsset)
        assert local_result['video'].path == expected_video

        # Test missing parameter raises ValueError
        with pytest.raises(ValueError, match='Missing required'):
            download_video()


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


def test_base_asset_fspath(tmp_path: Path) -> None:
    asset_file = tmp_path / 'asset.mp4'
    asset = VideoAsset(path=asset_file)
    assert Path(asset) == asset_file
    assert str(asset) == str(asset_file)


def test_stages_dict_and_alias_inputs(tmp_path: Path) -> None:
    video_file = tmp_path / 'in.mp4'
    video_file.write_bytes(b'video')
    out_audio = tmp_path / 'out.wav'
    out_audio.write_bytes(b'audio')

    with patch('subprocess.run') as mock_subproc:
        mock_subproc.return_value = MagicMock(returncode=0)

        # Stage receiving previous stage output dict
        res_audio = extract_audio(
            video={'video': VideoAsset(path=video_file)},
            output_path=out_audio,
        )
        assert isinstance(res_audio['audio'], AudioAsset)

        # Separate vocals receiving previous stage output dict
        res_vocals = separate_vocals(
            audio=res_audio,
            output_dir=tmp_path,
        )
        assert 'vocals' in res_vocals
        assert 'background' in res_vocals

    # Test merge_segments with transcript alias
    mock_trans = Transcription(
        language='en',
        segments=[
            Segment(start=0.0, end=1.0, text='Hello'),
            Segment(start=1.2, end=2.0, text='world'),
        ],
    )
    res_merge = merge_segments(transcript={'transcription': mock_trans})
    assert len(res_merge['segments']) == 1
    assert res_merge['text'] == 'Hello world'

    # Test translate with transcript alias
    mock_llm = MagicMock()
    mock_llm.translate.return_value = ['Olá mundo']
    with patch('viper.stages.text.get_llm', return_value=mock_llm):
        res_translate = translate(transcript=res_merge)
        assert res_translate['translated_texts'] == ['Olá mundo']
        assert res_translate['translation'] == 'Olá mundo'

    # Test synthesize with translation alias
    mock_tts = MagicMock()
    mock_tts.sample_rate = 24000
    with patch('viper.stages.speech.get_tts', return_value=mock_tts):
        out_tts = tmp_path / 'synth.wav'
        res_speech = synthesize(translation=res_translate, output_path=out_tts)
        assert isinstance(res_speech['audio'], AudioAsset)

    # Test render_video with output dicts
    out_dubbed = tmp_path / 'dubbed.mp4'
    with patch('subprocess.run') as mock_subproc:
        mock_subproc.return_value = MagicMock(returncode=0)
        out_dubbed.write_bytes(b'dubbed')
        res_render = render_video(
            video={'video': VideoAsset(path=video_file)},
            audio=res_speech,
            output_path=out_dubbed,
        )
        assert isinstance(res_render['video'], VideoAsset)


def test_merge_segments_advanced_rules() -> None:
    # 1. Punctuation break even if gap is small
    segs = [
        Segment(start=0.0, end=2.0, text='Hello world.'),
        Segment(start=2.1, end=4.0, text='Next sentence.'),
    ]
    res = merge_segments(segments=segs, max_gap=0.5)
    assert len(res['segments']) == 2

    # 2. Duration break even without punctuation
    segs_long = [
        Segment(start=0.0, end=6.0, text='First long part'),
        Segment(start=6.1, end=12.0, text='Second long part'),
    ]
    res_dur = merge_segments(segments=segs_long, max_gap=0.5, max_duration=8.0)
    assert len(res_dur['segments']) == 2

    # 3. Character length break
    segs_chars = [
        Segment(start=0.0, end=1.0, text='a' * 120),
        Segment(start=1.1, end=2.0, text='b' * 120),
    ]
    res_chars = merge_segments(
        segments=segs_chars, max_gap=0.5, max_characters=150
    )
    assert len(res_chars['segments']) == 2


def test_speech_synthesize_timeline(tmp_path: Path) -> None:
    out_wav = tmp_path / 'timeline_synth.wav'
    sample_rate = 24000

    mock_tts = MagicMock()
    mock_tts.sample_rate = sample_rate

    # Return 1 second (24000 samples) of audio for each segment
    mock_tts.synthesize_raw.return_value = (
        np.ones(sample_rate, dtype=np.float32) * 0.5
    )

    segs = [
        Segment(start=1.0, end=2.0, text='Phrase one'),
        Segment(start=4.0, end=5.0, text='Phrase two'),
    ]

    with patch('viper.stages.speech.get_tts', return_value=mock_tts):
        res = synthesize(
            segments=segs,
            output_path=out_wav,
            voice='pf_dora',
        )

        assert 'audio' in res
        assert 'segments' in res
        assert len(res['segments']) == 2
        # Phrase two starts at 4.0, duration 1.0 => end 5.0
        assert res['segments'][1]['start'] == 4.0
        assert out_wav.exists()


def test_video_render_with_background(tmp_path: Path) -> None:
    video_file = tmp_path / 'in.mp4'
    video_file.write_bytes(b'video')
    speech_file = tmp_path / 'speech.wav'
    speech_file.write_bytes(b'speech')
    bg_file = tmp_path / 'bg.wav'
    bg_file.write_bytes(b'background')
    out_video = tmp_path / 'out.mp4'

    with patch('subprocess.run') as mock_subproc:
        mock_subproc.return_value = MagicMock(returncode=0)
        out_video.write_bytes(b'rendered')

        result = render_video(
            video=video_file,
            audio=speech_file,
            background=bg_file,
            output_path=out_video,
        )

        assert 'video' in result
        assert isinstance(result['video'], VideoAsset)

        # Inspect the ffmpeg command executed
        cmd = mock_subproc.call_args[0][0]
        assert '-shortest' not in cmd
        assert '-filter_complex' in cmd
        assert 'sidechaincompress' in cmd[cmd.index('-filter_complex') + 1]
        assert 'amix' in cmd[cmd.index('-filter_complex') + 1]


def test_filter_repeats() -> None:
    segs = [
        Segment(start=0.0, end=2.0, text='Hello world.'),
        Segment(start=2.0, end=4.0, text='I see you next time.'),
        Segment(start=4.0, end=6.0, text='I see you next time!'),
        Segment(start=6.0, end=8.0, text='I see you next time...'),
        Segment(start=8.0, end=10.0, text='I see you next time'),
        Segment(start=10.0, end=12.0, text='...'),
        Segment(start=12.0, end=14.0, text='Back to normal'),
    ]
    res = filter_repeats(segs, max_consecutive=2)
    texts = [s.text for s in res]
    assert len(texts) == 4
    assert texts[0] == 'Hello world.'
    assert texts[1] == 'I see you next time.'
    assert texts[2] == 'I see you next time!'
    assert texts[3] == 'Back to normal'


def test_video_render_duration_enforced(tmp_path: Path) -> None:
    video_file = tmp_path / 'in.mp4'
    video_file.write_bytes(b'video')
    speech_file = tmp_path / 'speech.wav'
    speech_file.write_bytes(b'speech')
    out_video = tmp_path / 'out.mp4'
    out_video.write_bytes(b'rendered')

    def fake_subproc(cmd, **_kwargs):
        if 'ffprobe' in cmd[0]:
            return MagicMock(returncode=0, stdout='753.116\n')
        return MagicMock(returncode=0, stdout='')

    with patch('subprocess.run', side_effect=fake_subproc) as mock_run:
        render_video(
            video=video_file,
            audio=speech_file,
            output_path=out_video,
        )
        ffmpeg_cmd = mock_run.call_args[0][0]
        assert '-t' in ffmpeg_cmd
        assert '753.116' in ffmpeg_cmd


def test_speech_synthesize_timing_drift(tmp_path: Path) -> None:
    out_wav = tmp_path / 'no_drift.wav'
    sample_rate = 24000
    mock_tts = MagicMock()
    mock_tts.sample_rate = sample_rate
    mock_tts.synthesize_raw.return_value = np.zeros(
        sample_rate * 3, dtype=np.float32
    )

    segs = [
        Segment(start=0.0, end=1.0, text='Long audio in short slot'),
        Segment(start=2.0, end=3.0, text='Second sentence'),
    ]

    with patch('viper.stages.speech.get_tts', return_value=mock_tts):
        res = synthesize(
            segments=segs,
            output_path=out_wav,
            voice='pf_dora',
        )
        assert len(res['segments']) == 2
        assert res['segments'][0]['end'] <= 2.0
        assert res['segments'][1]['start'] == 2.0


def test_apply_micro_fades() -> None:
    sr = 24000
    samples = np.ones(sr, dtype=np.float32)
    faded = apply_micro_fades(samples, sr, fade_ms=10.0)
    fade_len = int(sr * 0.010)
    assert faded[0] == 0.0
    assert faded[-1] == 0.0
    assert np.isclose(faded[fade_len], 1.0, atol=0.01)
    assert np.isclose(faded[len(faded) - fade_len - 1], 1.0, atol=0.01)


def test_speech_synthesize_bidirectional_and_elastic(tmp_path: Path) -> None:
    out_wav = tmp_path / 'elastic.wav'
    sr = 24000
    mock_tts = MagicMock()
    mock_tts.sample_rate = sr
    raw_samples = np.ones(int(sr * 0.5), dtype=np.float32)
    mock_tts.synthesize_raw.return_value = raw_samples

    segs = [
        Segment(start=0.0, end=2.0, text='Short speech in big window'),
    ]

    with patch('viper.stages.speech.get_tts', return_value=mock_tts):
        res = synthesize(
            segments=segs,
            output_path=out_wav,
            voice='pf_dora',
        )
        assert len(res['segments']) == 1
        placed = res['segments'][0]
        assert placed['start'] > 0.0
        assert placed['end'] <= 2.0
        assert out_wav.exists()


def test_text_translate_with_durations() -> None:
    mock_llm = MagicMock()
    mock_llm.translate.return_value = ['Olá mundo rápido']

    segs = [Segment(start=0.0, end=2.5, text='Hello fast world')]

    with patch('viper.stages.text.get_llm', return_value=mock_llm):
        result = translate(
            transcript={'segments': segs},
            target_language='pt-BR',
        )

        mock_llm.translate.assert_called_once()
        call_kwargs = mock_llm.translate.call_args[1]
        assert call_kwargs.get('durations') == [2.5]
        assert len(result['segments']) == 1
        assert result['segments'][0].text == 'Olá mundo rápido'
