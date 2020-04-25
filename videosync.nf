#!/usr/bin/env nextflow


master_ch = Channel.fromPath(params.master)
video_ch = Channel.fromPath(params.videos)

params.clip_duration = 30
params.resample_div = 10
params.bitrate = 48000


process extract_audio {
    input:
        file(video) from video_ch
    output:
        tuple file(video), file("audio.flac"), val(extension) into video_audio_ch

    script:
    extension = video.name.substring(video.name.lastIndexOf('.')+1)
    """
        ffmpeg -i $video -vn -f flac -ab 48000 audio.flac
    """
}

process get_error {
    echo true
    input:
        tuple file(video), file("audio.flac"), val(extension) from video_audio_ch
        each file(master) from master_ch
    output:
        tuple file(video), file("audio.flac"), val(extension), stdout into get_error_ch

    script:
    """
        chordlsync_geterror.py -s ${master} -i audio.flac --clip-duration ${params.clip_duration} --resample-div ${params.resample_div}
    """
}

process synchronize_video {
    echo true
    publishDir params.outdir, \
        mode: "copy", \
        overwrite: true, \
        pattern: "out.vid.*", \
        saveAs: { fn -> video.name }

    publishDir params.outdir, \
        mode: "copy", \
        overwrite: true, \
        pattern: "out.audio.*", \
        saveAs: { fn -> "${video.name.take(video.name.lastIndexOf('.'))}.flac" }

    input:
        tuple file(video), file("audio.flac"), val(extension), val(error_val) from get_error_ch
    output:
        tuple file("out.vid.*"), file("out.audio.flac") into synced_ch

    script:
    error_d = Double.valueOf(error_val)
//    error_d = 5.0
    if (error_d > 0)
        """
            ffmpeg -ss 00:00:${error_d} -i ${video} -c copy out.vid.${extension}
            ffmpeg -i out.vid.${extension} -vn -f flac -ab ${params.bitrate} out.audio.flac
        """
    else
        """
            ffmpeg -i ${video} -itsoffset ${error_d} -i ${video} -map 0:a -map 1:v -c copy tempfile.${extension}
            ffmpeg -i tempfile.${extension} -itsoffset ${error_d} -i ${video} -map 0:v -map 1:a -c copy out.vid.${extension}
            ffmpeg -i out.vid.${extension} -vn -f flac -ab ${params.bitrate} out.audio.flac

            rm tempfile.${extension}

        """
}

synced_ch.println()
