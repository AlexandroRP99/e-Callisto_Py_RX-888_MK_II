# e-Callisto_Py_RX-888_MK_II
### This project provides system to use the SDR RX-888 MK II as a receiver for the e-CALLISTO network.

## Previous work used

As a basis for the development of this project for the RX-888 MK II, the project developed as a Master's Thesis by the user [@alexmfz](https://github.com/alexmfz) for the SDR HackRF One has been used.

[Link to the code for HackRF One](https://github.com/alexmfz/hackrf/tree/main/executables)

## Installation and use

The steps for its use and installation are the following:

• **Step 1.** Having downloaded the project folder from the repository, the first step is to carry out the installation of all the dependencies and prior configurations required. For this purpose, the Bash script “install.sh” is provided. We must locate ourselves in the root directory of the project from any terminal in order to execute the script using the command: ./install.sh. For its execution to start, first we will be asked for the user password in order to execute certain commands with sudo. If at this step any error occurs due to possible conflicts with other installed software, it is recommended instead to run this program on a clean installation of Ubuntu, in which, according to the tests carried out, it is guaranteed to work.

• **Step 2.** If the execution of the previous step has been successful, we must proceed with the configuration files. The first of them will be config.cfg. In the file itself the utility of each of the parameters is defined by the comment that accompanies it, being very important to respect that the parameters in which it is indicated at the end of their comment must not be edited. Most of the parameters are used to define the content of the headers of the FITS files; however, there are three parameters that directly adjust the operation of the system. These are: “integration”, which allows adjusting the number of FFTs to integrate; “data_transform_mode”, which selects the function used for the transformation of the data format; and, finally, “period_time”, which adjusts the moment at which the scheduled times will be read again. For this last parameter it is recommended that it be configured at least one minute before the first scheduled time so that there is enough time for the SDR to reinitialize and resume the data acquisition.

• **Step 3.** The second configuration file that must be edited is “scheduler.cfg”. In this file the times at which the start of each data acquisition will take place are defined. When editing this file it is very important to respect two conditions: that the minimum separation between each time be 15 minutes and that the file must contain at the end the comment “END SCHEDULING”, as shown in Figure 4.31. In addition, it is also important that the times are written each on their own line and that there are no blank lines between them.

• **Step 4.** After having made the changes to the configuration files, the final step is to verify that the SDR is connected to the Raspberry Pi and execute the command: ./runProgram. This will launch the execution of the program, leaving only to wait for the creation of the FITS files. As they are generated, they will be stored in the “Results” folder located in the main directory of the project. The program runs infinitely and periodically every day, therefore, if we wish to stop the execution, it is enough to press the key combination “ctrl+C” in the terminal.
