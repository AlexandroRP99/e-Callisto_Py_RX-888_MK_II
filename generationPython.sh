#!/bin/bash
originalPath=$(pwd) # Base path
cd $originalPath

# Activate conda environment (ARP adition)
source "$HOME/miniforge3/bin/activate" env_RX-888_MK_II

parameter_file='config.cfg' # File with parameters of the program to be executed
scheduler_file='scheduler.cfg' # File with scheduling times

content_scheduling=$(cat $scheduler_file) # Content of file name with times
content_parameter=$(cat $parameter_file) # Content of file name with times

check_comment=$(cat $scheduler_file | grep "END SCHEDULING") # Checks if exists comment in filename
check_format_1="^[0-1][0-9]:[0-5][0-9]:[0-5][0-9]" # Checks times from 00:00:00 to 19:59:59
check_format_2="^[2][0-3]:[0-5][0-9]:[0-5][0-9]" # Checks times from 20:00:00 to 23:59:59

time_now=$(date +%H%M%S) # Time at this moment
logger=1 # Variable to show waiting message

# Checks config file content
if [[ -z "$content_parameter" && -s $parameter_file ]]
then
	echo "File parameters.cfg empty"
	echo "...Exiting..."
	exit 1
fi

# Take parameters to set as input and check that are not empty
# ARP The parameters have been changed to adapt to the new ones and to the removal of the old ones not used now
station_name=$(head -n 3 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^station_name=].*' | tr -d '[:space:]')
focus_code=$(head -n 4 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^focus_code=].*' | tr -d '[:space:]')
gain=$(head -n 5 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^gain=].*' | tr -d '[:space:]')
longitude=$(head -n 6 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^longitude=].*' | tr -d '[:space:]')
longitude_code=$(head -n 7 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^longitude_code=].*' | tr -d '[:space:]')
latitude=$(head -n 8 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^latitude=]*' | tr -d '[:space:]')
latitude_code=$(head -n 9 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^latitude_code=].*' | tr -d '[:space:]')
altitude=$(head -n 10 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^altitude=].*' | tr -d '[:space:]')
object=$(head -n 11 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^object=].*' | tr -d '[:space:]')
content=$(head -n 12 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^content=].*' | tr -d '[:space:]')
control_external_generation=$(head -n 13 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^control_external_generation=].*' | tr -d '[:space:]')
last_time_scheduled=$(head -n 15 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^last_time_scheduled=].*' | tr -d '[:space:]')

# Checks parameters of execution and run it if everything is ok
if  [[ -z "$station_name" || "$station_name" == "$empty" ||
       -z "$focus_code" || $focus_code == $empty ||
       -z "$gain" || $gain == $empty ||
       -z "$longitude" || $longitude == $empty ||       
       -z "$longitude_code" || $longitude_code == $empty ||
       -z "$latitude" || $latitude == $empty ||
       -z "$latitude_code" || $latitude_code == $empty ||
       -z "$altitude" || $altitude == $empty || 
       -z "$object" || $object == $empty ||
       -z "$content" || $content == $empty || 
       -z "$control_external_generation" || $control_external_generation == $empty ||
       -z "$last_time_scheduled" || $last_time_scheduled == $empty
      ]]
then
    echo "File parameters are empty"
    echo "...Exiting..."
    exit 1
else
    # Scheduling.cfg is readed and sw is executed
    # ARP now the FITs generator is in python mode by default, so no variable checking is needed to control it
      
    while [ $control_external_generation -ne 2 ]
    do
        control_external_generation=$(head -n 13 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^control_external_generation=].*')
        if [ $control_external_generation -eq 1 ]
        then
            # Update last_time_scheduled in config.cfg
            last_time_scheduled=$(head -n 15 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^last_time_scheduled=].*' | tr -d '[:space:]')
            # execute generation with python
            python3 generationFits.py $station_name $focus_code $latitude $latitude_code $longitude $longitude_code $altitude $object $content $last_time_scheduled
            
            if [ -f "$originalPath/temp_data/fft_data_$last_time_scheduled.bin" ]; then
                rm "$originalPath/temp_data/fft_data_$last_time_scheduled.bin"
            fi
            if [ -f "$originalPath/temp_data/time_$last_time_scheduled.bin" ]; then
                rm "$originalPath/temp_data/time_$last_time_scheduled.bin"
            fi
            if [ -f "$originalPath/temp_data/header_$last_time_scheduled.txt" ]; then
                rm "$originalPath/temp_data/header_$last_time_scheduled.txt"
            fi

            # Create Result directory if it doesn't exist
            if [ ! -d "Result" ]; then
                mkdir -p Result
            fi

            mv *.fit Result
            mv *_logs.txt Result
                            
            # Disable control flag to not execute python script again
            sed -i 's\control_external_generation=1\control_external_generation=0\' $parameter_file
            logger=1
        else

            if [[ $logger -eq 1 && $control_external_generation -ne 2 ]]
            then
                echo "INFO: Waiting for the data acquisition to finish to generate the FIT file..."
                logger=0                
            fi

        fi 
    done



fi

exit 0
