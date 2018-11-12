import re
import sys
import logging

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from six.moves import queue

LOG = logging.getLogger()
LOG.removeHandler(LOG.handlers[0])

class GoogleStreamer:
    def __init__(self, rate=16000,lang='zh-TW'):
        self.client = speech.SpeechClient()
        LOG = logging.getLogger()
        LOG.removeHandler(LOG.handlers[0])

        config = types.RecognitionConfig(
                encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=rate,
                language_code=lang
                )

        self.streaming_config = types.StreamingRecognitionConfig(
                config=config,
                interim_results=True
                )

    
    def start_recognition_stream(self, stream):
        requests = (types.StreamingRecognizeRequest(audio_content=content) for content in stream)

        return self.client.streaming_recognize(self.streaming_config, requests)

