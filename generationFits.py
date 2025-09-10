import logging as logger

from astropy.io import fits
import numpy as np

from io import open

import os
import sys
import datetime as dt

error_code = "ERROR"
success_code = "OK"
hdul = None
min_value = None
max_value = None
fits_name = None


def create_image():
    """
    Creates a fits image as primary extension with the dimensions of nChannels and triggeringTimes

    @return: Result of the function was succesfull or not (OK | ERROR)
    """

    global hdul
    global max_value
    global min_value

    # input data (samples ordered) of SDR as byte
    logger.info("generationFits | createImage() | Creation of fits image")
    logger.info("generationFits | createImage() | Reading fft data from SDR")

    fft_data = read_fft_data()
    if isinstance(fft_data, str) and fft_data == error_code:
        logger.error("generationFits | create_image() | Error at reading fft data")
        return error_code

    # Before inserting data into img save max and min values of fft data for headers
    max_value = fft_data.max()
    min_value = fft_data.min()

    # Reverse array to start from max freq to min freq. Samples must be reversed too
    # fft_data.reverse() #ARP data already reversed

    # Insert data into image es primary HDU in fit file
    # ARP u1 es para datos de 0 a 255, pero los datos de SDR son float32, cambiar si es necesario depués
    # image_data = np.ones((n_channels, triggering_times), dtype='u1')
    
    # ARP Creo qque insert_data_image no es necesario ya que fft_data ya es un array 2D
    # image_data = np.ones((n_channels, triggering_times), dtype='np.float32')
    # image_data = insert_data_image(image_data, fft_data)

    # if image_data is None:
    #     logger.error("generationFits | createImage() | Was not possible to read data")
    #     return error_code

    # Create PrimaryHDU to encapsulate the data
    image = fits.PrimaryHDU(data=fft_data)
    if image is None:
        logger.error("generationFits | createImage() | Was not possible to create the image")
        return error_code

    # Create an HDUList to contain the newly created PrimaryHDU and write to a new file
    hdul = fits.HDUList([image])
    if hdul is None:
        logger.error("generationFits | createImage() | Was not possible to create the Primary HDU")

    logger.info("generationFits | createImage() | Execution Success")
    return success_code


def read_header_data():
    """
    Read header extra info (dates and times) from header_times.txt

    @return: Header data as an array.
             If the file cannot be opened, return "ERROR"
    """

    header_data = []

    logger.info("generationFits | read_header_data() | Reading headers extra data")

    header_file = open(f"temp_data/header_{sys.argv[10]}.txt", "r")
    if header_file is None:
        logger.error("generationFits | read_header_data() | Error at reading header file")
        return error_code

    header_not_formated = header_file.readlines()
    for header in header_not_formated:
        header_data.append(header.replace("\n", ""))

    header_file.close()

    logger.info("generationFits | read_header_data() | Execution Success")
    return header_data


def update_headers_image():
    """
    Update headers image to adapt to fit standar header. Some headers are extract from header_times.txt

    @return: Result of the function was succesfull or not (OK | ERROR)
    """

    global hdul
    global max_value
    global min_value
    bscale = 1.
    bzero = 0.
    header_data = read_header_data()
    if header_data == "ERROR":
        logger.error("generationFits | update_headers_image() | Error at reading header file")
        return error_code

    logger.info("generationFits 1 UpdateHeadersImage() | Updating headers of fits image")
    len_headers = len(hdul[0].header)

    # Update headers
    hdul[0].header.append(("DATE", header_data[0].replace("/", "-"), "Time of observation"))
    hdul[0].header.append(("CONTENT", sys.argv[9], "Title"))

    hdul[0].header.append(("INSTRUME", "HACKRF One", "Name of the instrument"))
    hdul[0].header.append(("OBJECT", sys.argv[8], "Object name"))

    hdul[0].header.append(("DATE-OBS", header_data[0], "Date observation starts"))
    hdul[0].header.append(("TIME-OBS", header_data[1], "Time observation starts"))
    hdul[0].header.append(("DATE-END", header_data[2], "Date Observation ends"))
    hdul[0].header.append(("TIME-END", header_data[3], "Time observation ends"))

    hdul[0].header.append(("BZERO", bzero, "Scaling offset"))
    hdul[0].header.append(("BSCALE", bscale, "Scaling factor"))

    hdul[0].header.append(("BUNIT", "digits", "Z - axis title"))

    hdul[0].header.append(("DATAMAX", max_value, "Max pixel data"))
    hdul[0].header.append(("DATAMIN", min_value, "Min pixel data"))

    hdul[0].header.append(("CRVAL1", header_data[4], "Value on axis 1 [sec of day]"))
    hdul[0].header.append(("CRPIX1", 0, "Reference pixel of axis 1"))
    hdul[0].header.append(("CTYPE1", "TIME [UT]", "Title of axis 1"))
    hdul[0].header.append(("CDELT1", 0.25, "Step between first and second element in x-axis"))

    hdul[0].header.append(("CRVAL2", min(read_frequencies()), "Value on axis 2 "))
    hdul[0].header.append(("CRPIX2", 0, "Reference pixel of axis 2"))
    hdul[0].header.append(("CTYPE2", "Frequency [MHz]", "Title of axis 2"))
    hdul[0].header.append(("CDELT2", -1, "Step samples"))

    hdul[0].header.append(("OBS_LAT", sys.argv[3], "Observatory latitude in degree"))
    hdul[0].header.append(("OBS_LAC", sys.argv[4], "Observatory latitude code {N, S}"))
    hdul[0].header.append(("OBS_LON", sys.argv[5], "Observatory longitude in degree"))
    hdul[0].header.append(("OBS_LOC", sys.argv[6], " Observatory longitude code {E, W}"))
    hdul[0].header.append(("OBS_ALT", sys.argv[7], "Observatory altitude in meter"))
    
    if len_headers == len(hdul[0].header):
        return error_code

    logger.info("generationFits | UpdateHeadersImage() | Execution Success")
    return success_code


def create_binary_table():
    """
    Create a binary table formed by 2 columns (frequencies and times).
    This data is read from frequencies.txt and times.txt

    @return: Result of the function was successful or not (OK | ERROR)
    """

    global hdul

    frequencies = np.arange(n_channels)
    frequencies = read_frequencies()
    if isinstance(frequencies, str) and frequencies == error_code:
        logger.error("generationFits | create_binary_table() | Error at reading frequency file")
        return error_code

    times = np.arange(triggering_times)
    times = read_times()
    if isinstance(times, str) and times == error_code:
        logger.error("generationFits | create_binary_table() | Error at reading times file")
        return error_code

    # Create binary table
    logger.info("generationFits | createBinaryTable() | Creating binary table of dimensions 1x2")
    c1 = fits.Column(name="Time", array=np.array([times]), format=f'{triggering_times}D8.3')
    c2 = fits.Column(name="Frequency", array=np.array([frequencies]), format=f'{n_channels}D8.3')
    binary_table = fits.BinTableHDU.from_columns([c1, c2])

    hdul.append(binary_table)

    if binary_table is None or len(hdul) == 1:
        logger.error("generationFits | createBinaryTable() | Was not possible to create binary table")
        return error_code

    logger.info("generationFits | createBinaryTable() | Execution Success")
    return success_code


def generate_dynamic_name():
    """
    Generate the name of the fit file in a dynamic way
    @return: name of the fits
    """

    global hdul
    global fits_name

    extension = ".fit"
    date_obs = hdul[0].header["DATE-OBS"].replace("/", "") + "_"
    start_date = hdul[0].header["TIME-OBS"]
    logger.info("Start date" + start_date)
    format_date = start_date[:3].replace(":", "") + start_date[3:6].replace(":", "") + start_date[6:8]

    fits_name = sys.argv[1] + "_" + date_obs + format_date + "_" + sys.argv[2] + extension

    logger.info("generationFits | generate_dynamic_name() | File generated with name: " + fits_name)
    return fits_name


def read_fft_data():
    """
    Read fft samples from fft_data.bin which is the output of executing samples_processor.py (ARP mod)

    return: If OK: Return the fft data read from fft_data.bin as an array and reformated.
            If there is an error: Return "ERROR
    """

    logger.info("generationFits | read_fft_data() | Reading fft data")

    try:
        path_fft = f"temp_data/fft_data_{sys.argv[10]}.bin"
    
        # Verify if the file exists
        if not os.path.exists(path_fft):
            logger.error(f"generationFits | read_fft_data() | File not found: {path_fft}")
            return error_code
    
        fft_data_flat = np.fromfile(path_fft, dtype=np.uint8)

        # Verify if the file is empty
        if fft_data_flat.size == 0:
            logger.error("generationFits | read_fft_data() | Empty file")
            return error_code        

        # Reconstruct the 2D array from the flattened data
        columns = []
        for n in range(triggering_times):
            columns.append(fft_data_flat[n*n_channels:((n+1)*n_channels)])
        fft_data = np.column_stack(columns)

        logger.info("generationFits | read_fft_data() | Execution Success")

        return fft_data

    except Exception as e:
        logger.error(f"generationFits | read_fft_data() | Error reading file: {str(e)}")
        return error_code    


def insert_data_image(image_data, power_sample):
    """
    Insert data to the image taking it from the previous ones read

    @param image_data: Initial data of img (which is 2 full arrays of ones
    @param power_sample: Power samples read
    @return: image data created
    """

    i = 0  # iterator of samples

    j = 0  # Aux iterator
    z = 0  # Aux iterator
    y = 0  # Aux iterator
    image_data_2 = np.ones((n_channels, triggering_times), dtype='u1')

    logger.info("generationFits | insert_data_image() | Inserting data into image")

    for times in range(triggering_times):
        for frequencies in range(n_channels):
            image_data_2[frequencies][times] = np.array(power_sample[i]).astype("u1")
            i += 1

    # Values should be entered in ordered so there is a need of regroup
    for element in range(n_channels * triggering_times):
        if element % n_channels == 0 and element != 0:
            j += 1
            z = 0
        power_sample[element] = image_data_2[z][triggering_times - j - 1]
        z += 1

    i = 0  # restart iterator
    for times in range(triggering_times):
        for frequencies in range(n_channels):
            image_data[frequencies][times] = np.array(power_sample[i]).astype("u1")
            i += 1

    logger.info("generationFits | insert_data_image() | Execution Success")
    return image_data


def read_frequencies():
    """
    Read frequencies from freq.bin which is the output of executing samples_processor.py (ARP mod)

    return: If OK: Return the frequencies read from freq.bin as an array.
            If there is an error: Return "ERROR
    """

    logger.info("generationFits | read_frequencies() | Reading frequencies as output of SDR")

    try:
        path_freq = f"temp_data/freq.bin"
    
        # Verify if the file exists
        if not os.path.exists(path_freq):
            logger.error(f"generationFits | read_frequencies() | File not found: {path_freq}")
            return error_code
    
        freq_data = np.fromfile(path_freq, dtype=np.float64)

        # Verify if the file is empty
        if freq_data.size == 0:
            logger.error("generationFits | read_frequencies() | Empty file")
            return error_code        

        logger.info("generationFits | read_frequencies() | Execution Success")

        # Convert from Hz to MHz
        freq_data = freq_data / 1e6  

        return freq_data

    except Exception as e:
        logger.error(f"generationFits | read_frequencies() | Error reading file: {str(e)}")
        return error_code    


def read_times():
    """
    Read times from times.txt which is the output of executing samples_processor.py (ARP mod)

    return: If OK: Return the times read from time.bin as an array and reformated.
            If there is an error: Return "ERROR
    """

    logger.info("generationFits | read_times() | Reading times as output of SDR")

    try:
        path_time = f"temp_data/time_{sys.argv[10]}.bin"
    
        # Verify if the file exists
        if not os.path.exists(path_time):
            logger.error(f"generationFits | read_times() | File not found: {path_time}")
            return error_code
    
        time_data_epoch = np.fromfile(path_time, dtype=np.float64)

        # Verify if the file is empty
        if time_data_epoch.size == 0:
            logger.error("generationFits | read_times() | Empty file")
            return error_code        

        # ARP este formato se usaría si se quisiera devolver un array de strings con el formato HH:MM:SS.ssssss
        """
        # Convert epoch timestamps to datetime objects and then to strings
        time_data_object = [dt.datetime.fromtimestamp(ts) for ts in time_data_epoch]  # Convert epoch timestamps to datetime objects
        time_data = [dt.datetime.strftime(ts,"%H:%M:%S.%f") for ts in time_data_object]  # Format datetime objects to string
        """
        # ARP este formato se usaría si se quisiera devolver un array con los segundos pasados desde el inicio de la captura de datos

        time_data = time_data_epoch - time_data_epoch[0]

        logger.info("generationFits | read_times() | Execution Success")

        return time_data

    except Exception as e:
        logger.error(f"generationFits | read_times() | Error reading file: {str(e)}")
        return error_code    


def print_fits_info():
    """
    Test function to check data

    @return: None
    """

    global hdul
    # FIT-file structure
    print(hdul.info())

    logger.info("----------Image data----------")
    logger.info(hdul[0].data)  # sdr data

    logger.info("----------Headers image data----------")
    logger.info(hdul[0].header)

    logger.info("----------Binary table data----------")
    logger.info(hdul[1].data)  # times and frequency datas

    logger.info("----------Headers binary table data----------")
    logger.info("Headers bin table", hdul[1].header)  # ok


def generate_fits():
    """
    Main functions which creates the fits file formed by an image and a binary table wich dimensions 3600x200

    @param n_channels: Nº of frequencies
    @param triggering_times: Nº of shots
    @return: Result of the function was successful or not (OK | ERROR)
    """

    global hdul

    logger.info("generationFits | Initializing generation of fits file through python")
    logger.info("generationsFits | Dimensions Fits file: " + str(n_channels) + "x" + str(triggering_times))

    # Create image from data received as output of SDR as a .txt
    if create_image() != success_code or hdul is None:
        return error_code

    # Update headers of image
    if update_headers_image() != success_code:
        return error_code

    # Create binary table with frequency and times columns
    if create_binary_table() != success_code:
        return error_code

    # Create the fits file
    hdul.writeto(generate_dynamic_name(), overwrite=True)

    logger.info("generationFits | generateFits() | Execution Success")
    return success_code


if __name__ == "__main__":

    print('Generando FIT')

    triggering_times = 3600  # ARP poner a 3600
    #triggering_times = 120  # ARP para debug
    n_channels = int(512/2)
    
    
    logger.basicConfig(filename='fits.log', filemode='w', level=logger.INFO)
    if generate_fits() != success_code:
        logger.info("generationFits | " + error_code)

    logger.info("generationFits | Execution Success")
    logger.info(dt.datetime.now())
    logger.shutdown()

    # Rename fits.log with the name of the data
    old_name = r"fits.log"
    new_name = fits_name.replace(".fit", "_python_logs.txt")

    # Renaming the file
    os.rename(old_name, new_name)
    
    """
    # print fits data to debug
    print_fits_info()
    """
