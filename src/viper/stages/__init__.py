"""Built-in pipeline processing stages."""

from viper.stages.audio import extract_audio, separate_vocals
from viper.stages.source import download_video, load_local_file
from viper.stages.speech import merge_segments, synthesize, transcribe
from viper.stages.text import translate
from viper.stages.video import convert_video, render_video

__all__ = [
    'convert_video',
    'download_video',
    'extract_audio',
    'load_local_file',
    'merge_segments',
    'render_video',
    'separate_vocals',
    'synthesize',
    'transcribe',
    'translate',
]
