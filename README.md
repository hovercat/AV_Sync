# AV_Sync

AV Sync can be used to sync multiple video files to one master video file.
Made for TU Wien Chor distance singing.

Master file (and all other files) must have a click track on the sound channels in the beginning of the videos to allow for synchronization.

## Requirements

- numpy
- scikit-learn
- soundfile
- pandas
- ffmpeg
- nextflow

## Usage

nextflow run videosync.nf --master MASTER_FILE --videos "INPUT_DIR/*" [--outdir OUTPUT_DIR]

or

./videosync.nf --master MASTER_FILE --videos "INPUT_DIR/*" [--outdir OUTPUT_DIR]
