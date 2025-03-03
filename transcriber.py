#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 21:31:52 2025

"""

from openai import OpenAI
import re
import wave
import os
import sys
import subprocess
from pathlib import Path
import math
from pymediainfo import MediaInfo
import contextlib

class ValidationError(Exception):
    pass
        
class VideoTimestamp:
    """Class contains string timestamp in HH:MM:SS format, the path of the 
    video to which it refers and its equivalent in seconds. Its"""
    
    def __init__(self, ui_timestamp, video_path):
        self.hhmmss = ui_timestamp
        self.video = video_path
        self.inseconds = None
        self.validator()

    def validator(self):
        """Validates if a timestamp is in correct format and within the video 
        file duration. If it is, populates the inseconds attribute."""
        
        pattern_match = re.search(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})", self.hhmmss)
   
        if pattern_match:
            ts_dict = pattern_match.groupdict()
        
            # Convert string values to integers
            hours = int(ts_dict["h"])
            minutes = int(ts_dict["m"])
            seconds = int(ts_dict["s"])
           
            # Validate time values
            if hours > 23 or minutes > 59 or seconds > 59:
                raise ValidationError("Timestamp inputted is incorrect.")
           
            # Calculate total seconds
            self.inseconds = hours * 3600 + minutes * 60 + seconds
        
            try:
                # Get video duration
                video_info = MediaInfo.parse(str(self.video))
                # MediaInfo returns duration in milliseconds
                duration = float(video_info.tracks[0].duration) / 1000
                
                if self.inseconds > duration:
                    raise ValidationError("Timestamp inputted is incorrect.")
            except (FileNotFoundError, ValueError, OSError, IOError) as e:
                # Handle file-related errors
                raise ValidationError(f"Error reading video file: {e}")
            
        else:
            raise ValidationError("Timestamp inputted does not match hh:mm:ss pattern.")
            
            
def get_valid_input(prompt, validator_func, error_message="Invalid input. Please try again."):
    """
    Generic function to get and validate user input.
    
    Args:
        prompt (str): The prompt to display to the user
        validator_func (callable): A function that takes the input and returns True if valid
        error_message (str): The message to display on validation failure
    
    Returns:
        The validated user input
    """
    while True:
        user_input = input(prompt)
        try:
            if validator_func(user_input):
                return user_input
        except Exception:
            pass
        print(error_message)

def is_valid_file(path_str):
    """Check if the path exists and is a file."""
    return Path(path_str).is_file()

def is_valid_yes_no(response):
    """Check if response is a valid yes/no answer."""
    return response.lower() in ['y', 'n']

def get_timestamp(prompt, video_path):
    """Get and validate a timestamp for the given video."""
    while True:
        ui_timestamp = input(prompt)
        try:
            timestamp_obj = VideoTimestamp(ui_timestamp, video_path)
            return timestamp_obj
        except ValidationError as e:
            print(f"Timestamp error: {e}")

def rip_audio(video_path, trim_check, flag_ss, flag_to):
    """Extract .wav audio file from video, trimming if needed. Returns the path
    of the new audio file"""
    audio_path = video_path.with_suffix(".wav")
    
    rip_command=['ffmpeg', '-y', '-report', '-i', str(video_path), '-vn', str(audio_path)]
    
    if trim_check:
        rip_command[5:5] = ['-ss',  flag_ss.hhmmss, '-to', flag_to.hhmmss]
    
    try:
        subprocess.run(rip_command, check=True)
        return audio_path
    except Exception as e:
        print(f"Error ripping with ffmpeg: {e}")
        sys.exit()  


def get_track_duration(audio_path):
    """ Returns audio track duration in seconds"""
    
    with contextlib.closing(wave.open(str(audio_path))) as a:
        frames = a.getnframes()
        rate = a.getframerate()
        duration = frames / float(rate)
        print("Track duration is " + str(duration) + " seconds.")
        return duration

def transcribe(audio_path, transcript_file):
    
    client = OpenAI()

    audio_file= open(str(audio_path), "rb")
    
    try:
        transcription = client.audio.transcriptions.create(
            el="whisper-1",
            ponse_format="text",
            e=audio_file
    	)
        
    except Exception as e:
        print(f"Couldn't transcribe {str(audio_path)}: {e}")
    
    with open(transcript_file,"a") as text_file:
        print(f"Now appending transcription of {str(audio_path)}")
        text_file.write(transcription)


def split_audio_file(audio_path, number_chunks, file_list):
    """Splits audio file into equal sized wav chunks"""
    duration = get_track_duration(audio_path)
         
    filename_stem = str(audio_path.parents[0]) + "/" + str(audio_path.stem)       
    
    chunk_duration = math.ceil(duration / number_chunks)
    
    start_time = 0
    for i in range (1, number_chunks + 1): 
        
        output_filename = filename_stem + str(i) + ".wav"
        
        split_command = ['ffmpeg', '-y', '-i', str(audio_path), '-ss', str(start_time), '-t', 
                        str(chunk_duration), '-c', 'copy', output_filename]
        
        try:
            subprocess.run(split_command)
            print("Wrote " + str(output_filename))
        except Exception as e: 
            print(f"Could not split audio file: {e}")
            sys.exit()
        
        file_list.append(output_filename)
        
        start_time += chunk_duration
    
    
    
def main(video_path, trim_check, ss_flag, to_flag):
    
    # Rip audio and get file size
    audio_path = rip_audio(video_path, trim_check, ss_flag, to_flag)

    audio_size = os.path.getsize(str(audio_path))
    print("Ripped audio file is " + str(round(audio_size/1000000)) + " Mb.") 
    
    file_list = []
    
    # If file size >25Mb, split file into overlapping chunks. 
    size_limit=25000000
    
    if audio_size <= size_limit:      
        file_list.append(str(audio_path))
        
    else:
        number_chunks = math.ceil(audio_size/size_limit)
        split_audio_file(audio_path, number_chunks, file_list)
            
    transcript_file = str(audio_path.parents[0]) + "/" + str(audio_path.stem) + ".txt"                                 
    
    for f in file_list:
        transcribe(f, transcript_file)
            

if __name__ == '__main__':
    # Get video path
    video_path_str = get_valid_input(
        "Please paste in full path to source video: ",
        is_valid_file,
        "File not found. Please correct your input and try again."
    )
    video_path = Path(video_path_str)
    print(f"Will run on {video_path}")
    
    # Get trimming boolean
    trim_response = get_valid_input(
        "Do you want to trim this clip? (y/n): ",
        is_valid_yes_no,
        "Please enter 'y' or 'n'."
    )
    trim_check = trim_response.lower() == 'y'
    
    # Get timestamps if trimming
    ss_flag = None
    to_flag = None
    
    if trim_check:
        ss_flag = get_timestamp("When should track start? Enter in hh:mm:ss format: ", video_path)
        to_flag = get_timestamp("When should track end? Enter in hh:mm:ss format: ", video_path)
    
    # Execute actual mission
    main(video_path, trim_check, ss_flag, to_flag)
