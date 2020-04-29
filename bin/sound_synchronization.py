import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import scipy.signal as sps
from scipy.signal import fftconvolve, correlate
import sklearn.preprocessing as skp
#import matplotlib.pyplot as plt
import soundfile as sf  # https://pysoundfile.readthedocs.io/en/latest/
import pandas as pd
import logging

def synchronize_multiple(sync, in_dir, out_dir, out_format="flac", threads=4):
    """ synchronize all files in in_dir and write to out_dir """

    with sf.SoundFile(sync, 'r') as sync_file:
        #sync_signal = sync_file.read(duration * sync_file.samplerate)
        sync_signal = sync_file.read()

        arguments = [
            (
                sync_signal,
                sync_file.samplerate,
                os.path.join(in_dir, in_file),
                os.path.join(out_dir, "{file}.{ext}".format(
                    file=os.path.splitext(os.path.basename(in_file))[0],
                    ext=out_format
                )))
            for in_file in os.listdir(in_dir)
        ]

        converted_dict = dict()
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = executor.map(_synchronize_helper, arguments)
            executor.shutdown(wait=True)

            for result in futures:
                converted_dict[result[0]] = result[1:]

        error_stats = pd.DataFrame.from_dict(converted_dict, orient="index")
        error_stats.columns = ["error_frames", "delay", "out_file"]
        error_stats.to_csv(os.path.join(out_dir, "sync_stats.csv"))
    return error_stats


def _synchronize_helper(args): #sync_signal, sync_samplerate, input_file, out_file):
    sync_signal = args[0]
    sync_samplerate = args[1]
    input_file = args[2]
    out_file = args[3]

    with sf.SoundFile(input_file, 'r') as input_sf:
        try:
            error_frames_input, delay, out = synchronize(sync_signal, sync_samplerate, input_sf.read(), input_sf.samplerate, out_file)
            print("{input_file}: {delay}s".format(
                input_file=input_file,
                delay=delay),
                file=sys.stdout
            )
        except Exception as ex:
            logging.error(ex)

        return input_file, error_frames_input, delay, out_file


def synchronize(sync_signal, sync_samplerate, input_signal, input_samplerate, out):
    """ synchronize file2 to file1 and write to out2 """

    is_mono = len(input_signal.shape) != 2

    # add second channel if mono
    if is_mono:
        input_signal = np.array((input_signal, input_signal)).transpose()

    resample_rate = min(input_samplerate, sync_samplerate)

    # get error
    error_frames, delay = get_error(sync_signal, sync_samplerate,
                                           input_signal, input_samplerate)
    error_frames = error_frames * (-1)
    error_frames_input = int(error_frames / resample_rate * input_samplerate)


    # check if signal is stereo
    if error_frames_input < 0:
        if is_mono:
            input_signal = input_signal[0,:]
            synced_signal = np.concatenate((input_signal, np.zeros(((-1) * error_frames_input))))
        else:
            synced_signal = np.concatenate((np.zeros(((-1) * error_frames_input, 2)), input_signal))
    else:
        if is_mono:
            synced_signal = input_signal[error_frames_input:]
        else:
            synced_signal = input_signal[error_frames_input:,:]

    sf.write(out, synced_signal, input_samplerate)

    return error_frames_input, delay, out


def get_error(input1, input1_samplerate, input2, input2_samplerate):
    """ get time delay of signal """
    if input1_samplerate != input2_samplerate:
        input2 = sps.resample(input2, int(input2.shape[0] / input2_samplerate) * input1_samplerate, axis=0)

    input1 = np.gradient(np.gradient(input1, axis=0), axis=0)
    input2 = np.gradient(np.gradient(input2, axis=0), axis=0)

    input1 = np.abs(input1)
    input2 = np.abs(input2)

    input1 = skp.maxabs_scale(input1)
    input2 = skp.maxabs_scale(input2)
    #
   # B, A = sps.butter(4, 1/50, output='ba')
  #  input1 = sps.filtfilt(B, A, np.abs(input1), axis=0)
   # input2 = sps.filtfilt(B, A, np.abs(input2), axis=0)


    error_frame = _shift_signals_cross_corr(input1, input2)

    return error_frame, error_frame / input1_samplerate


def _shift_signals_cross_corr(signal1, signal2, rate_drop_frequency=1, step_width=1):
    """ Using cross correlation and fft to detect delay in audio signals """
    #correlation = fftconvolve(signal2[:,0], signal1[:,0][::-1], mode='full', axes=0)

    #max_correlation = np.argmax(correlation, axis=0)
    #delay = max_correlation
    signal1 = signal1[:, 0] #* signal1[:,1]
    signal2 = signal2[:, 0] #* signal2[:,1]

    corr = correlate(signal1, signal2)#[::-1])
    #max_corr = np.argmax(sps.medfilt(corr, kernel_size=7))
    max_corr = np.argmax(corr, axis=0)

    frame = max_corr - len(signal2)

    return frame


def _plot_signals(signal1, signal2):
    plt.plot(signal1)
    plt.plot(signal2)

    plt.show()
