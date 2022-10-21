import os
import pprint
import subprocess

import crepe
import numpy
from scipy.io import wavfile
from pytube import YouTube
import re


class YoutubeUtil:

    def downloadYouTube(self, youtubeUrl: str):
        # instantiate youtube with video url
        yt = YouTube(youtubeUrl)

        # get the title and clean it up (can be used in later stages)
        title = re.sub('[\[\(].*', '', yt.title).strip()

        # get video and audio streams - for now only save audio as audio.wav (requires ffmpeg)
        videoStream = yt.streams.get_by_resolution("720p")
        audioStream = yt.streams.filter(only_audio=True).order_by("abr").last()
        out_file = audioStream.download(filename="temp.webm")
        subprocess.run('ffmpeg -i temp.webm -f wav audio.wav', shell=True)


    def splitAudio(self):
        # use spleeter to separate vocals from background
        subprocess.run('spleeter separate -p spleeter:2stems -o output audio.wav', shell=True)

    def detectPitch(self):
        # run pitch detection on extracted vocals for further usage.
        # confidence of >80% seems pretty accurate
        # TODO clean up: remove pitch changes <X ms, combine same subsequent frequencys
        # TODO create pitch table FrequencyRange <-> MidiNote
        # TODO Write Pitch sequence in Ultrastar like format, maybe implement python script that plays the notes for reference.

        sr, audio = wavfile.read('output/audio/vocals.wav')
        time, frequency, confidence, activation = crepe.predict(audio, sr, viterbi=True)
        result = numpy.column_stack((time, frequency, confidence))
        numpy.savetxt('vocals.csv', result,['%.3f', '%.3f', '%.6f'],header='time,frequency,confidence', delimiter=';')
        pp = pprint.PrettyPrinter()
        pp.pprint(result)

    def cleanup(self):
        os.remove("temp.webm")
        os.remove("audio.wav")
        os.remove("output/audio/accompaniment.wav")
        os.remove("output/audio/vocals.wav")


# Test
if __name__ == "__main__":
    util = YoutubeUtil()

    # Outcomment steps to not repeat them for testing

    #util.cleanup()
    util.downloadYouTube("https://www.youtube.com/watch?v=EYBlP6BfaYY")
    util.splitAudio()
    util.detectPitch()