import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import scipy.signal as sps
import sklearn.preprocessing as skp
#import matplotlib.pyplot as plt
import soundfile as sf  # https://pysoundfile.readthedocs.io/en/latest/
import pandas as pd

def synchronize_multiple(sync, in_dir, out_dir, out_format="flac", threads=22, duration=10, resample_rate=48000,
                         error_resample_div=10):
    """ synchronize all files in in_dir and write to out_dir """

    with sf.SoundFile(sync, 'r') as sync_file:
        sync_signal = sync_file.read(duration * sync_file.samplerate)

        arguments = [
            (
                sync_signal,
                sync_file.samplerate,
                os.path.join(in_dir, x),
                os.path.join(out_dir, "{file}.{ext}".format(
                    file=os.path.splitext(os.path.basename(x))[0],
                    ext=out_format
                )),
                duration,
                error_resample_div)
            for x in os.listdir(in_dir)
        ]

        converted_dict = dict()
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = executor.map(_synchronize_helper, arguments)
            executor.shutdown(wait=True)

            for result in futures:
                converted_dict[result[0]] = result[1:]

        error_stats = pd.DataFrame.from_dict(converted_dict, orient="index")
        error_stats.columns = ["error_in", "delay", "out_file"]
        error_stats.to_csv(os.path.join(out_dir, "sync_stats.csv"))
    return error_stats


def _synchronize_helper(args):
    return synchronize(args[0], args[1], args[2], args[3], args[4], args[5])


def synchronize(sync_signal, sync_samplerate, input_file, out, duration=10, error_resample_div=10):
    """ synchronize file2 to file1 and write to out2 """

    resample_rate = 0
    error_frames = 0
    delay = 0
    error = 0

    with sf.SoundFile(input_file, 'r') as input_sf:
        # read first x seconds or whole file if shorter
        if input_sf.frames > input_sf.samplerate * duration:
            input_sync_signal = input_sf.read(input_sf.samplerate * duration)
        else:
            input_sync_signal = input_sf.read()

        # add second channel if mono
        if len(input_sync_signal.shape) != 2:
            input_sync_signal = np.array((input_sync_signal, input_sync_signal)).transpose()

        # find lower sample_rate
        if sync_samplerate < input_sf.samplerate:
            resample_rate = sync_samplerate
        else:
            resample_rate = input_sf.samplerate

        # get error
        error_frames, delay, error = get_error(sync_signal, sync_samplerate,
                                               input_sync_signal, input_sf.samplerate,
                                               resample_rate,
                                               error_resample_div)

    # Write out
    with sf.SoundFile(input_file, 'r') as input_sf:
        input_data = input_sf.read()
        input_resampled = sps.resample(input_data, int((input_data.shape[0] / input_sf.samplerate) * resample_rate))

        data_sync = input_resampled

        # check if signal is stereo
        if len(input_data.shape) == 2:
            if error_frames < 0:
                silence = np.zeros(((-1) * error_frames, 2))
                data_sync = np.concatenate((silence, data_sync))
            else:
                data_sync = data_sync[error_frames:, :]
        else:
            if error_frames < 0:
                silence = np.zeros((-1) * error_frames)
                data_sync = np.concatenate((silence, data_sync))
            else:
                data_sync = data_sync[error_frames:]

        sf.write(out, data_sync, resample_rate)

    return input_file, error, delay, out


def get_error(sync_signal, sync_samplerate, input_signal, input_samplerate, resample_rate, duration=10,
              error_resample_div=10):
    """ get time delay of signal """

    preprocessed_sync, preprocessed_input = _preprocess_signals(sync_signal, sync_samplerate,
                                                                input_signal, input_samplerate,
                                                                resample_rate,
                                                                error_resample_div)

    error_pos1, error1 = _shift_signals(preprocessed_sync, preprocessed_input, shift_width=10)
    error_pos2, error2 = _shift_signals(preprocessed_input, preprocessed_sync, shift_width=10)

    if error1 < error2:
        error = error1
        error_pos = error_pos1 * error_resample_div
    else:
        error = error2
        error_pos = error_pos2 * error_resample_div * (-1)

  #  print("Error: {}, Position: {}".format(
  #      error,
  #      error_pos / resample_rate
  #  ))

    return error_pos, error_pos / resample_rate, error


def _preprocess_signals(signal1, signal1_samplerate, signal2, signal2_samplerate, resample_rate,
                        error_resample_div):  # todo resampling of e.g 44.1khz
    p_sign1 = sps.resample(signal1, int(signal1.shape[0] * (resample_rate / signal1_samplerate) / error_resample_div),
                           axis=0)
    p_sign2 = sps.resample(signal2, int(signal2.shape[0] * (resample_rate / signal2_samplerate) / error_resample_div),
                           axis=0)

    if p_sign1.shape[0] != p_sign2.shape[0]:
        p_sign2 = np.concatenate((p_sign2, np.zeros((p_sign1.shape[0] - p_sign2.shape[0], 2))))

    p_sign1 = np.gradient(np.gradient(p_sign1, axis=0), axis=0)
    p_sign2 = np.gradient(np.gradient(p_sign2, axis=0), axis=0)

    B, A = sps.butter(4, 1/50, output='ba')
    p_sign1 = sps.filtfilt(B, A, np.abs(p_sign1), axis=0)
    p_sign2 = sps.filtfilt(B, A, np.abs(p_sign2), axis=0)

    p_sign1 = skp.maxabs_scale(p_sign1)
    p_sign2 = skp.maxabs_scale(p_sign2)

    p_sign1[p_sign1 < 0] = 0
    p_sign2[p_sign2 < 0] = 0

    return p_sign1, p_sign2


def _shift_signals(signal1, signal2, shift_width):
    """  """

    min_error = 1
    min_error_index = 0
    l = signal1.shape[0]

    signal1 = np.abs(signal1)
    signal2 = np.abs(signal2)

    for i in range(0, l, shift_width):
        error_overlap = np.sum(np.abs(signal1[0:i] - signal2[l - i:l]))
        error_rest1 = np.sum(signal1[i:l])
        error_rest2 = np.sum(signal2[0:l - i])
        error = np.square((error_overlap + error_rest1 + error_rest2) / (l + i))

        if error < min_error:
            min_error = error
            min_error_index = i

    min_error_position = l - min_error_index

    return min_error_position, min_error


#def _plot_signals(signal1, signal2):
#    plt.plot(signal1)
#    plt.plot(signal2)
#
#    plt.show()
