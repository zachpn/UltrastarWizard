import os
import pprint
import subprocess
import time
import speech_recognition as sr

import crepe
import librosa
import numpy
from pysinewave import SineWave
from scipy.io import wavfile
from pytube import YouTube
import re

# pitch table for conversions
pitch = ['C','C#','D','D#','E','F','F#','G','G#','A','A#', 'B']

# = Window size in ms for frequency detection
stepSize=50

##############################################################################################
### A Proof of Concept script to play around with automatic Ultrastar txt file generation  ###
##############################################################################################
    # Current Issues to solve:
    #  - Extracted vocals can contain instrumental frequencies (polution).
    #  - Words sung close together do not appear as separate notes
    #  - No lyrics generation
    #
    # While the pitch output of this example is not too bad, its far from perfect or usalbe for Ultrastar
    # The only way to resolve this would be a proper audio2text transcription:
      # 1. Transcribe lyrics from extracted vocals
      # 2. Improve transcription with accurate lyrics from the web
      # 3. Use transcription timestamps to lookup sung key from Frequency/Notes table

    # TODO: Find/Create a proper model for audio transcription that can recognize sung word


class YoutubeUtil:

    # This downloads video and audio from youtube
    # currently only audio is saved as temp.webm / audio.wav
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

    # This splits the audio.wav into a vocals.way and accompaniment.wav
    def splitAudio(self):
        subprocess.run('spleeter separate -p spleeter:2stems -o output audio.wav', shell=True)

    # This loads the vocals.wav and performs pitch detection
    # result is saved in vocals.csv
    def detectPitch(self):
        sr, audio = wavfile.read('output/audio/vocals.wav')
        time, frequency, confidence, activation = crepe.predict(audio, sr, viterbi=True, step_size=stepSize)
        result = numpy.column_stack((time, frequency, confidence))
        numpy.savetxt('vocals.csv', result,['%.3f', '%.3f', '%.6f'],header='time,frequency,confidence', delimiter=';')
        pp = pprint.PrettyPrinter()
        pp.pprint(result)

    # This post processes the vocals.csv:
    # Extract only notes with high confidence
    # Combine notes of same pitch and update timestamp, calculate duration
    # result is saved as vocals_filtered and vocals squashed
    def filterByConfidence(self):
        filteredArray = []
        array = numpy.genfromtxt('vocals.csv', delimiter=";", dtype=str)
        for element in array:
            if float(element[2]) > 0.80:
                note = str(librosa.hz_to_note(float(element[1])))
                row = numpy.array([element[0], element[1], element[2], note])
                filteredArray.append(row)

        sqashedArray = []
        timeStamp = 0
        duration = 0
        note = ""
        for element in filteredArray:
            duration = duration + stepSize
            newTs = int(element[0].replace('.', ''))
            newNote = element[3].replace('♯', '#')
            deltaTs = timeStamp + duration + stepSize
            if((deltaTs < newTs) or (note != newNote)):
                pitch = self.noteToPitch(note, 3)
                row = numpy.array([timeStamp, duration, note, pitch])
                sqashedArray.append(row)
                timeStamp = newTs
                duration = 0
                note = newNote

        numpy.savetxt('vocals-filtered.csv', filteredArray, fmt='%s', header='time,frequency,confidence,note', delimiter=';', encoding="utf-8")
        numpy.savetxt('vocals-squashed.csv', sqashedArray, fmt='%s', header='time,duration,note,pitch', delimiter=';', encoding="utf-8")
        self.playNotes(sqashedArray)

    # Helper method to convert a note to a pitch int.
    def noteToPitch(self, note: str, lowestOctave: int):
        if (note == ''):
            return

        octave = int(re.findall('\d', note)[0])
        basenote = note.replace(str(octave), '')
        index = pitch.index(basenote)
        return index + (octave - lowestOctave) * 12

    # dumb method to play those recognized notes... I could have invested time to build a midi file, but what for... this is a POC
    def playNotes(self, array):
        progress = 0
        for line in array:
            if (line[3] == None):
                continue
            time.sleep((int(line[0]) - progress)/1000)
            if (int (line[1]) > 100):
                sw = SineWave(int(line[3]), pitch_per_second=0)
                sw.play()
                print(line[3])
                time.sleep(int(line[1])/1000)
                sw.stop()
            progress = int(line[0]) + int(line[1])

# This doesn't work
    def recognizeLyrics(self):
        r = sr.Recognizer()
        with sr.AudioFile("output/audio/vocals.wav") as source:
            audio = r.record(source)  # read the entire audio file
            print("Transcription: " + r.recognize_google(audio))

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
    util.downloadYouTube("https://www.youtube.com/watch?v=M-mtdN6R3bQ")
    util.splitAudio()
    util.detectPitch()
    util.filterByConfidence()
    #util.recognizeLyrics()
