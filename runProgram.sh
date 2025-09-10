#!/bin/bash

originalPath=$(pwd) # Base path
cd $originalPath

# ARP Activate conda environment
source "$HOME/miniforge3/bin/activate" env_RX-888_MK_II

# ARP Function to handle Ctrl+C
cleanup() {
    
    echo "INFO: Ctrl+C detected. Terminating processes..."
    # Find and kill processes related to generationPython.sh
    ps aux | grep -i generationPython.sh | grep -v grep | awk '{print $2}' | xargs -r kill -9
    echo "INFO: Processes generationPython.sh terminated."

    # Restore the original scheduler file
    if [[ -f original.tmp ]]; then
        cp original.tmp $scheduler_file
        rm original.tmp
    fi

    exit 0
}

# Configure the handler for Ctrl+C
trap cleanup SIGINT

# Load the firmware
# ARP adapted to the RX-888 MK II
echo "INFO: Loading RX-888 MK II firmware..."
cd $originalPath/install_files/rx888_test
./my_usb_example SDDC_FX3.img 2>&1 | while read line; do  
    if [[ "$line" == *"Firmware upload done."* ]]; then
        echo "INFO: Firmware loaded successfully."
        pkill -f "my_usb_example"
        break
    fi
    if [[ "$line" == *"Error or device could not be found"* ]]; then
        echo "INFO: Firmware already loaded."
        pkill -f "my_usb_example"
        break
    fi
done
sleep 1
cd $originalPath

# Load the configuration and scheduler files
parameter_file='config.cfg'  # Configuration file name
scheduler_file='scheduler.cfg'  # Scheduler file name
content_parameter=$(cat $parameter_file)  # Content of the configuration file
content_scheduling=$(cat $scheduler_file)  # Content of the scheduler file

check_comment=$(cat $scheduler_file | grep "END SCHEDULING") # Checks if exists the final comment at the end of the scheduler file
check_format_1="^[0-1][0-9]:[0-5][0-9]:[0-5][0-9]" # Checks times from 00:00:00 to 19:59:59
check_format_2="^[2][0-3]:[0-5][0-9]:[0-5][0-9]" # Checks times from 20:00:00 to 23:59:59

time_iterator=0  # Used later to check the scheduler content format

# Checks the scheduler file content and notifies if it is not well formattes
cp $scheduler_file original.tmp
sed -i '/END SCHEDULING/,$d' $scheduler_file  # ARP avoids problems with possible blank lines after the end comment

if [[ ! -z "$content_scheduling" && -s $scheduler_file ]]  # Checks if the file is not empty and has content
then
	if [ -z "$check_comment" ]  # Checks if the last line is the expected comment
	then
		echo "ERROR: File not empty, but not well formated.
		Must include this exact comment at the end:
		########### END SCHEDULING ###########"
		echo "...Exiting..."
        cp original.tmp $scheduler_file
        rm original.tmp
		exit 1
	fi

	while read schedule_time  # Reads each line of the scheduler file
	do
		check_time_1=$(echo $schedule_time | grep $check_format_1)
		check_time_2=$(echo $schedule_time | grep $check_format_2)
    
        if [[ $time_iterator -eq 0 ]]
        then
            schedule_time_prev=$(date -d "$schedule_time" +"%H%M%S" | sed 's/^0*//')
        else
            schedule_time_prev=$schedule_time_next
        fi

        schedule_time_next=$(date -d "$schedule_time" +"%H%M%S" | sed 's/^0*//')  
        value_time_prev=$schedule_time_prev 
        value_time_next=$schedule_time_next 

        differenceTime=$(($value_time_next-$value_time_prev))
    
        if [[ $differenceTime -lt 1500 && $time_iterator > 0 ]]  # Checks if the time difference between two consecutive times is less than 15 minutes (1500 seconds)
        then
            echo "ERROR: Window time minor than 15 minutes"
            echo "...Exiting..."
            cp original.tmp $scheduler_file
            rm original.tmp
            exit 1
        fi

        time_iterator=$(($time_iterator+1))
        
        if [[ -z $check_time_1 && -z $check_time_2 ]]  # Checks if the time format is correct
        then
            echo "ERROR: Time not well formated"
            echo "...Exiting..."
            cp original.tmp $scheduler_file
            rm original.tmp
            exit 1
        fi

	done < $scheduler_file

else
	echo "ERROR: File empty"
	echo "Example (comment must be included):
	20:00:00
	20:15:00
	########### END SCHEDULING ###########"
	echo "...Exiting..."
    cp original.tmp $scheduler_file
    rm original.tmp
	exit 1
fi	

cp original.tmp $scheduler_file
rm original.tmp

# ARP logic to check if the config file is empty or not has been changed
# Verify if the config file exists and is not empty
if [[ -f $parameter_file && ! -s $parameter_file ]]
then
    echo "ERROR: File config.cfg empty"
    echo "...Exiting..."
    exit 1
fi

# Verify the content of the config file
if [[ -z "$content_parameter" ]]
then
    echo "ERROR: File config.cfg empty or unreadable"
    echo "...Exiting..."
    exit 1
fi

# Take parameters to set as input and check that are not empty
integration=$(head -n 1 $parameter_file | grep -o '^[^#]*' | grep -o '[^integration=]*' | tr -d '[:space:]')

data_transform_mode=$(head -n 2 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^data_transform_mode=].*' | tr -d '[:space:]')

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

# Periodity part 
period_time=$(head -n 14 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^period_time=].*')
check_time_3=$(echo $period_time | grep $check_format_1)		
check_time_4=$(echo $period_time | grep $check_format_2)

if [[ -z $check_time_3 && -z $check_time_4 ]]  # Checks if the period time format is correct
    then
        echo "ERROR: Time periodity not well formated. Check it at config.cfg"
        echo "...Exiting..."
        exit 1
fi

time_check_repetition=$(date -d "$period_time" +"%H%M%S"  | tr -d '[:space:]' | sed 's/^0*//')

enable_repetition=0 # Control flag periodicity
control_log=1 # Log control flag
first_execution=0 # Control flag first execution
empty=""

# Checks parameters of execution and run it if everything is ok
if  [[ -z "$integration" || $integration == $empty ||
       -z "$data_transform_mode" || $data_transform_mode == $empty ||
       -z "$station_name" || "$station_name" == "$empty" ||
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
       -z "$time_check_repetition" || $time_check_repetition -eq $empty 
      ]]
then
    echo "ERROR: It was not possible to execute."
    echo "Check config.cfg"
    echo "...Exiting..."
    exit 1

else

    # ARP Check that integration is a positive integer
    if ! [[ "$integration" =~ ^[0-9]+$ ]] || [ "$integration" -le 0 ]; then
        echo "ERROR: Invalid integration value. It must be a positive integer."
        echo "...Exiting..."
        exit 1
    fi

    # ARP Check that data_transform_mode is 0, 1 or 2
    if ! [[ "$data_transform_mode" =~ ^[0-2]$ ]]; then
        echo "ERROR: Invalid data_transform_mode value. It must be 0, 1, or 2."
        echo "...Exiting..."
        exit 1
    fi

    # Periodically execution
    while [ 1 ]
    do
        time_now=$(date +%H%M%S | sed 's/^0*//') # Update time

        # Checks Control log to show log at 2nd or consecutive executions 
        if [[ $control_log -eq 1 && $first_execution -eq 1 ]]
        then 

            # If a .bin remains, it is removed
            if ls $originalPath/temp_data/*.bin 1> /dev/null 2>&1; then
                rm $originalPath/temp_data/*.bin
            fi

            period_time=$(head -n 14 $parameter_file | tail -n 1 | grep -o '^[^#]*' | grep -o '[^period_time=].*')
            check_time_3=$(echo $period_time | grep $check_format_1)		
            check_time_4=$(echo $period_time | grep $check_format_2)

            if [[ -z $check_time_3 && -z $check_time_4 ]]
            then
                echo "ERROR: Time periodity not well formated. Check it at config.cfg"
                echo "...Exiting..."
                cp original.tmp $scheduler_file
                rm original.tmp
                exit 0
            fi

            time_check_repetition=$(date -d "$period_time" +"%H%M%S"  | tr -d '[:space:]' | sed 's/^0*//') # Period time formated

            echo "INFO: Program will be executed again at $period_time"
            sleep 1
            
            control_log=0
        fi

        # Execute functionality at first execution or when times are equals in the following ones
        if [[ $first_execution -eq 0 || ($time_now -eq $time_check_repetition && $enable_repetition -eq 0) ]]
        then
            enable_repetition=1
            first_execution=1
            cp $scheduler_file original.tmp
            sed -i '/END SCHEDULING/,$d' $scheduler_file  # ARP avoids problems with possible blank lines after the end comment

            # Write 0 always at beginning to avoid generation at beginning
            sed -i 's\control_external_generation=1\control_external_generation=0\' $parameter_file
            sed -i 's\control_external_generation=2\control_external_generation=0\' $parameter_file
  
            # ARP now the FITs generator is in python mode by default, so no variable checking is needed to control it
            echo "INFO: Executing fits generator in background"
            ./generationPython.sh &
            
            if [ $enable_repetition -eq 1 ]
            then

                # Read the content of the scheduler file and discard the already passed times
                while read schedule_time;
                do
                    schedule_time_formated=$(date -d "$schedule_time" +"%H%M%S" | sed 's/^0*//')
                    if [ $time_now -gt $schedule_time_formated ]
                    then
                        echo "WARNING. The time $schedule_time has already passed. Skipping execution."
                        continue
                    else
                        schedule_time_list="${schedule_time_list:+$schedule_time_list,}$schedule_time"
                    fi
                done < $scheduler_file

                if [[ -n "$schedule_time_list" ]]; then
                    execution_argument="-i$integration -t$schedule_time_list -d$data_transform_mode"
                    echo "INFO: Running Program"

                    # ARP now the FITs generator is in python mode by default, so no variable is needed to control it
                    # ARP the iteration over the scheduled times has been moved  inside samplesProcessor.py
                    python3 samplesProcessor.py $execution_argument  
                fi

                cp original.tmp $scheduler_file
                rm original.tmp

                # Kill generationPython.sh
                sleep 4
                sed -i 's\control_external_generation=1\control_external_generation=2\' $parameter_file 
                sed -i 's\control_external_generation=0\control_external_generation=2\' $parameter_file 
                
                echo -e "INFO: Program Finished For Today. Waiting until next execution\n"
                #echo "...Opening JavaViewer..."
                #cd Result/LastResult/
                #java -jar RAPPViewer.jar
                
            fi

            #end
            enable_repetition=0 # disable repetition until time_now == time_check_repetition
            control_log=1 # Enable log of future executions
        fi	
    done  
fi
