#!/usr/bin/env python
import os
import sys

import datetime
import argparse
import soundfile as sf
import numpy as np

import sound_synchronization

parser = argparse.ArgumentParser(description="Gets error between sync file and input file")
parser.add_argument('-s', '--sync-file', type=str, help="Synchronization file with beeps in the beginning", required=True)
parser.add_argument('-i', '--input-file', type=str, help="Input file", required=True)

args = parser.parse_args()

if not os.path.exists(args.input_file):
    print("Input file {} does not exist.".format(args.input_file))
    sys.exit(1)

if not os.path.exists(args.sync_file):
    print("Master sync file {} does not exist.".format(args.sync_file))
    sys.exit(1)


duration = args.clip_duration
with sf.SoundFile(args.sync_file, 'r') as sync_file, sf.SoundFile(args.input_file, 'r') as input_sf:
    sync_signal = sync_file.read()
    singer_signal = input_sf.read()

    # add second channel if mono
    if len(singer_signal.shape) != 2:
        singer_signal = np.array((singer_signal, singer_signal)).transpose()

    # get error
    error_frames, delay = sound_synchronization.get_error(
        sync_signal, sync_file.samplerate,
        singer_signal, input_sf.samplerate
    )


if delay > 0:
    print("-", end='')

print(str(datetime.timedelta(seconds=abs(delay))), end='')
