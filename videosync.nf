#!/usr/bin/env nextflow

master_ch = Channel.fromPath(params.master)
video_ch = Channel.fromPath(params.videos)


video_ch.into{ video_ch1; video_ch2 }

process extract_audio {
    executor 'local'
    echo true
    publishDir "${params.outdir}/720p", \
        mode: "copy", \
        overwrite: true, \
        pattern: "*.mp4"

    
    input:
        file(video) from video_ch2
    output:
//       ttuple file("${video.baseName}.720p.mp4"), file("${video.baseName}.720p.h.mp4"), file("audio.flac"), val(extension) into video_audio_ch
        tuple file("*d.mp4"), file("audio.flac"), val(extension) into video_audio_ch

    script:
    extension = video.name.substring(video.name.lastIndexOf('.')+1)
    """
        height=\$(ffprobe2 -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 $video)
        width=\$(ffprobe2 -v error -select_streams v:0 -show_entries stream=width -of csv=s=x:p=0 $video)


        if [[ \$((height > width)) == 1 ]]; then
            temp="\$height"
            height="\$width"
            width="\$temp"
        fi
	
        width=\$(ffprobe2 -v error -select_streams v:0 -show_entries stream=width -of csv=s=x:p=0 out.mp4)   
        output_file="${video.baseName}.\${width}x\${height}d.mp4"
        mv $video "\$output_file"
        
        ffmpeg2 -threads 2 -i "\$output_file" -vn -f flac -ab 48000 audio.flac
    """
}

/*process get_error {
    echo true
//    queueSize 20

    input:
        tuple file(video), file("audio.flac"), val(extension) from video_audio_ch
        each file(master) from master_ch
    output:
        tuple file(video), file("audio.flac"), val(extension), stdout into get_error_ch

    script:
    """
        chordlsync_geterror.py -s ${master} -i audio.flac
    """
}*/

process synchronize_video {
    echo true

    publishDir "${params.outdir}/sync", \
        mode: "copy", \
        overwrite: true, \
        pattern: "*sync.mp4" \

    input:
        tuple file(video), file("audio.flac"), val(extension) from video_audio_ch
        each file(master) from master_ch
    output:
        tuple file("*.sync.mp4"), file(video), env(error) into synced_ch

    script:
    """    
        error=\$(chordlsync_geterror.py -s ${master} -i audio.flac)

        if [ \$error = -* ]; then
            error=\${error//-}
            ffmpeg2 -i $video -movflags faststart -itsoffset \$error -i '${video}' -map 0:a -map 1:v -c copy 'tempfile.${extension}'
            ffmpeg2 -i tempfile.${extension} -movflags faststart -itsoffset \$error -i '${video}' -map 0:v -map 1:a -c copy '${video.baseName}.sync.mp4'
            rm tempfile.${extension}
        else
            ffmpeg2 -i $video -movflags faststart -ss \$error -c:v libx264 -map 0 '${video.baseName}.sync.mp4'
        fi
    """
}

synced_ch.println()
