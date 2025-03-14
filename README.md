# Transcriber

## Overview

`transcriber.py` is a script that extracts and transcribes audio from video files using `ffmpeg` and OpenAI's Whisper API. It can optionally trim the video before transcription and split large audio files into smaller chunks for processing.

## Features

- Validates timestamps in `HH:MM:SS` format against the video's duration
- Extracts audio from video files using `ffmpeg`
- Optionally trims the audio before extraction
- Splits large audio files (>25MB) into smaller chunks
- Uses OpenAI's Whisper API to transcribe audio to text
- Saves the transcription to a `.txt` file

## Dependencies

Make sure you have the following installed:

- `python3`
- `ffmpeg`
- `pymediainfo`
- `wave`
- `openai` Python package
- `pathlib`
- `subprocess`
- `re`
- `math`
- `sys`
- `contextlib`

Install missing dependencies via:

```sh
pip install pymediainfo openai

