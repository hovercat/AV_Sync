#!/usr/bin/env python
import os
import sys

import argparse
import soundfile as sf
import numpy as np

import sound_synchronization

parser = argparse.ArgumentParser(description="Gets error between sync file and input file")
parser.add_argument('-s', '--sync-file', type=str, help="Synchronization file with beeps in the beginning", required=True)
parser.add_argument('-i', '--input-file', type=str, help="Input file", required=True)
parser.add_argument('--clip-duration', type=int, help="Duration of synchronization to take from every input file; default: 10s", default=10)
parser.add_argument('--resample-div', type=int, help="Influences the accuracy. The original sample rate is divided by this value for error detection; default: 10", default=10)


#args = parser.parse_args(["-s", "unittests/resources/enjoy/Master.ogg", "-i", "unittests/resources/enjoy/andi.flac"])
args = parser.parse_args()

if not os.path.exists(args.input_file):
    print("Input file {} does not exist.".format(args.input_file))
    sys.exit(1)

if not os.path.exists(args.sync_file):
    print("Master sync file {} does not exist.".format(args.sync_file))
    sys.exit(1)


duration = args.clip_duration
with sf.SoundFile(args.sync_file, 'r') as sync_file, sf.SoundFile(args.input_file, 'r') as input_sf:
    sync_signal = sync_file.read(duration * sync_file.samplerate)
    # read first x seconds or whole file if shorter
    if input_sf.frames > input_sf.samplerate * duration:
        input_sync_signal = input_sf.read(input_sf.samplerate * duration)
    else:
        input_sync_signal = input_sf.read()

    # add second channel if mono
    if len(input_sync_signal.shape) != 2:
        input_sync_signal = np.array((input_sync_signal, input_sync_signal)).transpose()

    # find lower sample_rate
    if sync_file.samplerate < input_sf.samplerate:
        resample_rate = sync_file.samplerate
    else:
        resample_rate = input_sf.samplerate

    # get error
    error_frames, delay, error = sound_synchronization.get_error(sync_signal, sync_file.samplerate,
                                           input_sync_signal, input_sf.samplerate,
                                           resample_rate,
                                           args.resample_div)

print(
    "{delay}".format(
        delay=delay
    ),
    end=''
)
