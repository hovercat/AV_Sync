# AV_Sync

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
