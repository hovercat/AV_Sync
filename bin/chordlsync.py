#!/usr/bin/env python
import os
import sys

import argparse

import sound_synchronization

parser = argparse.ArgumentParser(description="Synchronisation für TU Chor Files")
parser.add_argument('-s', '--sync-file', type=str, help="Synchronization file with beeps in the beginning", required=True)
parser.add_argument('-o', '--output-dir', type=str, help="Output directory; default=./out", default="out")
parser.add_argument('-i', '--input-dir', type=str, help="Input directory", required=True)
parser.add_argument('-f', '--format', type=str, help="Output format; supported are flac and wav; default: flac", default="flac")
parser.add_argument('-j', '--jobs', type=int, help="Number of threads to use; default: 2", default=2)


#args = parser.parse_args(["-s", "unittests/resources/Master.ogg", "-i", "unittests/resources/sound_files", "-j", "2"])
args = parser.parse_args()

if os.path.exists(args.output_dir):
    print("Output folder {} already exists.".format(args.output_dir))
    sys.exit(1)
else:
    os.mkdir(args.output_dir)

if not os.path.exists(args.input_dir):
    print("Input folder {} does not exist.".format(args.input_dir))
    sys.exit(1)

if not os.path.exists(args.sync_file):
    print("Master sync file {} does not exist.".format(args.sync_file))
    sys.exit(1)

error_stats = sound_synchronization.synchronize_multiple(
    sync=args.sync_file,
    in_dir=args.input_dir,
    out_dir=args.output_dir,
    threads=args.jobs,
    out_format=args.format
)

if error_stats is None:
    print("Looks like i didn't synchronize at all?")