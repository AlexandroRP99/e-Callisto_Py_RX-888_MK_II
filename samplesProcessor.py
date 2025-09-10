import SoapySDR
import time
from SoapySDR import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os
import multiprocessing as mp
import sys
import argparse
from datetime import datetime
import subprocess
import threading
import collections

class SDRSamplesReader(threading.Thread):
    """
    Class to read samples from the SDR in its own thread and feed them into the processing pipeline.
    """

    def __init__(self, sdr, rxStream, buff, ring, stop_event, timeout_us=50000):
        super().__init__(daemon=True)
        self.sdr = sdr
        self.rxStream = rxStream
        self.buff = buff
        self.ring = ring
        self.stop_event = stop_event
        self.timeout_us = timeout_us
        self.reads_ok = 0
        self.reads_drop = 0
        self.total_time = 0
        self.total_iterations = 0   


    def run(self):
        """
        Reads continuously samples from the SDR and then stores them in a ring buffer.
        The ring (circular) buffer ensures most recent data is always available for processing.
        When the ring buffer is full, the oldest data is discarded.
        """

        # Continuous loop to read samples from the SDR
        while not self.stop_event.is_set():
            
            start_time = time.time()
            
            try:
                # Read samples from the SDR
                sr = self.sdr.readStream(self.rxStream, [self.buff], len(self.buff), timeoutUs=self.timeout_us)

                # Check if the read operation was successful or if an overflow condition has occurred
                if sr.ret == len(self.buff):
                    # Store valid samples in the ring buffer
                    self.ring.append(self.buff[:self.ring.maxlen].copy())
                    self.reads_ok += 1  # Count successful reads for debugging
                else:
                    self.reads_drop += 1  # Count dropped reads for debugging
            except Exception:
                # Avoids killing the process if any unexpected error occurs
                self.reads_drop += 1
                time.sleep(0.001)
            
            # Calculate iteration duration for debugging
            iteration_time = time.time() - start_time
            self.total_time += iteration_time
            self.total_iterations += 1


    def stats(self):
        """
        Returns statistics about the sample consumption for debugging.
        """
        avg_time = self.total_time / self.total_iterations if self.total_iterations > 0 else 0
        return {"ok": self.reads_ok, "drops": self.reads_drop, "avg_iteration_time": avg_time}

# ----------------------------------------------------------------------------------------------------------

def parse_arguments():
    """Parse command line arguments for the script"""

    parser = argparse.ArgumentParser(description='Captures the RX-888 MK II data and performs FFT processing')

    parser.add_argument('-i', '--integration', required=True,
                       help='Number of FFTs integrated')
    parser.add_argument('-t', '--schedule_time', required=True,
                       help='Schedule time')
    parser.add_argument('-d', '--data_transform_mode', required=False,
                        help='Data transformation mode')

    return parser.parse_args()


def store_samples(queue, path, schedule_time_previous):
    """Store samples in a file in parallel while receiving and processing them"""

    with open(path, 'wb') as f:
        while True:
            item = queue.get()
            if item is None:
                # Writes the last scheduled time to the config file for generationFits.py use
                subprocess.run(["sed", "-i", f"s|last_time_scheluded=[^#]*#|last_time_scheluded={schedule_time_previous}                            #|", "config.cfg"])  
                # Enable control flag to execute the generationFits.py script
                subprocess.run(["sed", "-i", "s\\control_external_generation=0\\control_external_generation=1\\", "config.cfg"])
                break
            f.write(item.tobytes())
            

def initialize_sdr(FFT_size):
    """Initialize the SDR device and return the device, stream, and buffer"""

    # Intercept and ignore SoapySDR log messages to avoid continuous overflow messages
    try:
        SoapySDR.registerLogHandler(lambda level, msg: None)
    except AttributeError:
        pass

    # Enumerate devices
    results = SoapySDR.Device.enumerate()
    # for result in results: print(result)

    # Create device instance
    sdr = SoapySDR.Device(results[0])

    # Apply settings
    sdr.setSampleRate(SOAPY_SDR_RX, 0, 130e6)

    # Setup a stream (complex floats)
    rxStream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_S16)
    # print(sdr.getStreamMTU(rxStream))  # Used for debugging
    sdr.activateStream(rxStream) # Start streaming

    # Create a re-usable buffer for rx samples
    buff = np.array([0]*FFT_size, np.int16)

    print('INFO: RX-888 MK II initialized')

    return sdr, rxStream, buff


def prepare_data_adquisition(path_freq, FFT_size):
    """Prepare some data required for the FFT analysis and store frequency data in a temporary file for the later FIT generation"""

    # Data needed for FFT
    n_freq = FFT_size
    hanning_window = np.hanning(n_freq)
    half = n_freq // 2
    fft_freq = np.fft.fftfreq(FFT_size, d=1/130e6)
    fft_freq_flipped = np.flipud(fft_freq[:half])  # Flip the frequency axis becuse later the data will be flipped in the Y axis

    # Store the frequency data in a file
    with open(path_freq, 'wb') as freq_file:
        freq_file.write(fft_freq_flipped.tobytes())

    return hanning_window, half


def pop_samples(ring):
    """Extract samples from the ring buffer in LIFO order"""
    try:
        return ring.pop()
    except IndexError:
        return None


def process_samples(store_queue, schedule_time, FFT_size, path_time, path_header, n_iter, n_integration, hanning_window, half):
    """Function to process samples from the SDR"""

    # Calculate the timestamps
    time_start = datetime.strptime(f'{schedule_time}.000' ,'%H:%M:%S.%f').time()
    date_start = datetime.now().date()
    t_start = datetime.combine(date_start, time_start)
    t_end = t_start + timedelta(minutes=((n_iter/(4*60))-1), seconds=59, milliseconds=750)
    t_list = [t_start + timedelta(milliseconds=250*i) for i in range(int((t_end - t_start).total_seconds() * 1000 // 250) + 1)]
    t_timestamps = np.array([dt.timestamp() for dt in t_list])

    # Store the time data in a temporary file for the later FIT generation
    with open(path_time, 'wb') as time_file:
        time_file.write(t_timestamps.tobytes())

    # Store data for the FIT header in a temporary file for the later FIT generation
    with open(path_header, 'w') as header_file:
        header_file.write(f"{datetime.strftime(t_start, '%Y/%m/%d')}\n")
        milliseconds = t_start.microsecond // 1000
        header_file.write(f"{t_start.strftime('%H:%M:%S')}.{milliseconds:03d}\n")
        header_file.write(f"{datetime.strftime(t_end, '%Y/%m/%d')}\n")
        milliseconds = t_end.microsecond // 1000
        header_file.write(f"{t_end.strftime('%H:%M:%S')}.{milliseconds:03d}\n")
        header_file.write(f"{t_start.hour * 3600 + t_start.minute * 60 + t_start.second}\n")

    # Wait until the scheduled time
    print(f'INFO: Waiting until {schedule_time} to start the acquisition...')
    target_time = datetime.strptime(schedule_time, "%H:%M:%S").time()
    target_datetime = datetime.combine(datetime.now().date(), target_time)
    sleep_seconds = (target_datetime - datetime.now()).total_seconds()  # Time calculated to sleep
    if sleep_seconds > 0:
        print(f'INFO: Sleeping for {sleep_seconds:.2f} seconds until {schedule_time}...')
        #time.sleep(sleep_seconds)
    
    print(f'INFO: Starting acquisition for {schedule_time}, lasting for 15 minutes...')

    start_loop_time = time.time()  # Used as time reference for iteration timing (absolute timing)
    times = []  # Used to store the duration of each iteration and evaluate it tightness

    # Loops for 3600 times, with the timing equivalent to 15 minutes
    for n in range(n_iter):

        # Reset the start time to measure the duration of each iteration
        start_time = time.time()

        # Print time of the execution
        if (n+1) % 4 == 0:
            elapsed_time = int((n+1)/4 - 1)
            minutes, seconds = divmod(elapsed_time, 60)
            print(f'\rINFO: {minutes:02}:{seconds:02}   ', end='', flush=True)
            flag_warning_print_jump = True

        # Make the loop sleep to adquire a set of samples every 0.25 ms
        iter_start_time = start_loop_time + n * 0.25
        now = time.time()
        sleep_time = iter_start_time - now
        if sleep_time > 0:
            time.sleep(sleep_time)

        # Used to keep track of empty and not empty ring buffer states
        empty_ring_counter = 0
        not_empty_ring_counter = 0

        # Extract samples from the ring buffer as many times as the integration value selected
        for i in range(n_integration):

            # Extract samples from the ring buffer
            block = pop_samples(ring)
            # Check the state of the buffer
            if block is None:
                empty_ring_counter += 1
                continue
            else:
                not_empty_ring_counter += 1
                
            # Store the received samples
            if i == 0:
                buff_matrix = np.zeros((n_integration, FFT_size), dtype=np.int16)
                pos_index = 0
            buff_matrix[pos_index, :] = block
            pos_index += 1
 
        pos_index = 0

        # Notifies if the ring buffer was empty at some point and reshapes buff_matrix for a correct processing
        if empty_ring_counter > 0:
            if flag_warning_print_jump:
                print()
                flag_warning_print_jump = False
            print(f"WARNING: Not enough resources to perform the {n_integration} FFTs integration. Perfforming a {not_empty_ring_counter} FFTs integration instead.")
            # Remove rows that are completely zeros
            non_zero_rows = np.any(buff_matrix != 0, axis=1)
            buff_matrix = buff_matrix[non_zero_rows]
            
        # -------- FFT processing --------

        # Remove DC offset
        time_data_mean = np.mean(buff_matrix, axis=1, keepdims=True)
        buff_matrix_dc_removed = buff_matrix - np.round(time_data_mean).astype(np.int16)
        # Apply Hanning window
        buff_matrix_windowed = buff_matrix_dc_removed * hanning_window
        # Perform FFT        
        fft_data = np.fft.fft(buff_matrix_windowed, axis=1)
        # Keep only the positive frequencies and obtain the magnitude
        fft_data_abs = np.abs(fft_data[:, :half]).astype(np.float32)  # Convert to float32 to save memory
        # Integrate the FFT data
        fft_data_integrated = np.mean(fft_data_abs[:], axis=0)
        # Invert Y axis: flip data
        fft_data_abs_flipped = np.flipud(fft_data_integrated.T)

        # Transform RX-888 MK II linear data to scaled CALLISTO receiver linear data to make the output comparable
        if args.data_transform_mode == '0':
            fft_callisto_formated_lin = 89958.629068 * fft_data_abs_flipped  # Linear scaling
        elif args.data_transform_mode == '1':
            fft_callisto_formated_lin = 566080346 * (np.exp(7.32e-05*fft_data_abs_flipped) - 1)  # Exponential scaling
        elif args.data_transform_mode == '2':
            fft_callisto_formated_lin = 192944935 * (np.exp(1.15e-04*fft_data_abs_flipped) - 1)  # Exponential scaling with fixed lower values

        # Clip values to the equivalent in lineal to values between 0 and 255 in digits
        fft_callisto_formated_lin = np.clip(fft_callisto_formated_lin, 1, 6958564947.100452)

        # Transform to dB scale
        fft_callisto_formated_dB = 10 * np.log10(fft_callisto_formated_lin)

        # Transform to digits scale and convert to uint8 (the format used in CALLISTO)
        fft_callisto_formated_digits = np.round(fft_callisto_formated_dB * 255 * 25.4 / 2500).astype(np.uint8)

        # Input the samples in the queue to be stored by the storing process
        store_queue.put(fft_callisto_formated_digits)

        # Store the elapsed time for this iteration
        elapsed = time.time() - start_time
        times.append(elapsed)

    # Inserting None into the queue makes its corresponding fft data storing process to finish
    store_queue.put(None)

    # Statistics of times
    times_np = np.array(times)
    print("\n")
    print("\nINFO: Statistics of times per iteration:")
    print(f"Mean   : {times_np.mean():.6f} s")
    print(f"Median : {np.median(times_np):.6f} s")
    print(f"Minimum  : {times_np.min():.6f} s")
    print(f"Maximum  : {times_np.max():.6f} s")
    print("\n")
# --------------------------------------------------------------------------------------

if __name__ == "__main__":

    # Set FFT size
    FFT_size = 512

    # Loop to receive samples
    # n_iter = 120  # Used for debugging
    n_iter = 3600 # 3600 seconds equivalent to 15 minutes

    # Parse input arguments
    args = parse_arguments()

    # Initialize the RX-888 MK II
    sdr, rxStream, buff = initialize_sdr(FFT_size)

    ring = collections.deque(maxlen=25000)
    stop_event = threading.Event()
    reader = SDRSamplesReader(sdr, rxStream, buff, ring, stop_event)
    reader.start()

    # Wait for the reader to store enough data in the ring at least for the first iteration
    time.sleep(1)

    # Number of FFTs to integrate
    n_integration = int(args.integration)

    # Path to store frequency data temporarily
    path_freq = f"temp_data/freq.bin"

    # Prepare for the data adquisition
    hanning_window, half = prepare_data_adquisition(path_freq, FFT_size)

    # Array to store the ongoing processes
    processes = []

    # Loop through the scheduled times
    for schedule_time in args.schedule_time.split(','):
        
        # Path to store fft, time, and header data temporarily during the adquisition
        path_fft = f"temp_data/fft_data_{schedule_time}.bin"
        path_time = f"temp_data/time_{schedule_time}.bin"
        path_header = f"temp_data/header_{schedule_time}.txt"

        os.makedirs(os.path.dirname(path_fft), exist_ok=True)

        # Initialize the process to store samples
        queue = mp.Queue(maxsize=10)
        process = mp.Process(target=store_samples, args=(queue, path_fft, schedule_time, ))
        processes.append((process, queue))
        processes[-1][0].start()

        process_samples(processes[-1][1], schedule_time, FFT_size, path_time, path_header, n_iter, n_integration, hanning_window, half)

    # Makes sure all the processes have finished before the end of the script 
    while processes:
        for process, queue in processes[:]:
            if process.is_alive():
                  process.join()
                  processes.remove((process, queue))
            else:
                processes.remove((process, queue))
                
    # Shutdown the stream
    sdr.deactivateStream(rxStream) #stop streaming
    sdr.closeStream(rxStream)

    # Stop the reader thread
    # print(reader.stats())  # Used for debugging
    stop_event.set()
    time.sleep(1)  # Give some time to the reader thread to finish
