#!/bin/bash

# Mantain sudo pasword active while the script runs
sudo -v
while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &

originalPath=$(pwd)
cd $originalPath/install_files

echo ""
echo "-----------------------------------"
echo ""

# Download Miniforge
if [ ! -f "Miniforge3-$(uname)-$(uname -m).sh" ]; then
  echo "INFO: Miniforge installer not found. Downloading..."
  wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
  echo "INFO: Miniforge installer downloaded."
else
  echo "INFO: Miniforge installer already exists; skipping download."
fi

echo ""
echo "-----------------------------------"
echo ""

# Install Miniforge
if [ -f "$HOME/miniforge3/bin/conda" ] || [ -f "$HOME/Miniforge3/bin/conda" ]; then
  echo "INFO: Miniforge is already installed; skipping installation."
else
  chmod +x ./Miniforge3-$(uname)-$(uname -m).sh
  echo "INFO: Installing Miniforge..."
  ./Miniforge3-$(uname)-$(uname -m).sh -b
  echo "INFO: Miniforge installed"
fi

export PATH="$HOME/miniforge3/bin:$PATH"

echo ""
echo "-----------------------------------"
echo ""

cd $originalPath

# Install conda, create and activate an environment
if conda info --envs | grep -q "^env_RX-888_MK_II "; then
  echo "INFO: Conda environment 'env_RX-888_MK_II' already exists; skipping creation."
else
  echo "INFO: Creating conda environment..."
  conda create --name env_RX-888_MK_II python=3.12 -y
  echo "INFO: Conda environment created."
fi

echo "INFO: Activating conda environment..."
source "$HOME/miniforge3/bin/activate" env_RX-888_MK_II
echo "INFO: conda environment activated."

echo ""
echo "-----------------------------------"
echo ""

# Install SoapySDR dependencies

# List of required dependencies
packages=(cmake g++ libpython3-dev python3-numpy swig)

# Check and install missing dependencies
missing=()
for pkg in "${packages[@]}"; do
  dpkg -s "$pkg" &> /dev/null || missing+=("$pkg")
done

if [ ${#missing[@]} -ne 0 ]; then
  echo "INFO: Installing missing SoapySDR dependencies: ${missing[*]}"
  sudo apt-get update
  sudo apt-get install -y "${missing[@]}"
  echo "INFO: SoapySDR dependencies installed."
else
  echo "INFO: All SoapySDR dependencies are already installed, skipping installation."
fi

echo ""
echo "-----------------------------------"
echo ""

cd $originalPath/install_files/SoapySDR

# Build and install SoapySDR
if [ -d "/usr/local/lib/python3.12/site-packages/SoapySDR" ] || [ -f "/usr/local/lib/python3.12/site-packages/SoapySDR.py" ]; then
  echo "INFO: SoapySDR is already installed; skipping build and install."
else
  echo "INFO: Building and installing SoapySDR..."
  mkdir build
  cd build
  cmake ..
  make -j"$(nproc)"
  sudo make install -j"$(nproc)"
  sudo ldconfig # Needed on debian systems
  cd ..
  echo "INFO: SoapySDR installed successfully."
fi

echo ""
echo "-----------------------------------"
echo ""

# Install librx888 dependencies

# List of required dependencies
packages=(pkg-config libusb-1.0-0-dev)

# Check and install missing dependencies
missing=()
for pkg in "${packages[@]}"; do
  dpkg -s "$pkg" &> /dev/null || missing+=("$pkg")
done

if [ ${#missing[@]} -ne 0 ]; then
  echo "INFO: Installing missing librx888 dependencies: ${missing[*]}"
  sudo apt-get install -y "${missing[@]}"
  echo "INFO: librx888 dependencies installed."
else
  echo "INFO: All librx888 dependencies are already installed, skipping installation."
fi

echo ""
echo "-----------------------------------"
echo ""

cd $originalPath/install_files/librx888

# Check if the patch for RX-888 MK II compatibility is already applied
if patch --dry-run -p1 < ../RX888_MKII_patch.patch | grep -q "patching file"; then
  echo "INFO: Applying patch for RX-888 MK II compatibility..."
  patch -p1 < ../RX888_MKII_patch.patch
  echo "INFO: Patch applied successfully."
else
  echo "INFO: Patch for RX-888 MK II compatibility is already applied; skipping."
fi

echo ""
echo "-----------------------------------"
echo ""

# Build and install librx888
if [ -f "/usr/local/lib/librx888.so" ] || [ -f "/usr/local/lib64/librx888.so" ]; then
  echo "INFO: librx888 is already installed; skipping build and install."
else
  echo "INFO: Building and installing librx888..."
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  echo "INFO: librx888 built successfully."
fi

echo ""
echo "-----------------------------------"
echo ""

cd $originalPath/install_files/SoapyRX888

# Build and install SoapyRX888
if SoapySDRUtil --info 2>/dev/null | grep -q "/usr/local/lib/SoapySDR/modules0.8-3/librx888Support.so"; then
  echo "INFO: SoapyRX888 is already installed; skipping build and install."
else
  echo "INFO: Building and installing SoapyRX888..."
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  echo "INFO: SoapyRX888 built successfully."
fi

echo ""
echo "-----------------------------------"
echo ""

cd $originalPath/install_files/rx888_test

# Build rx888_test
if [ -f "my_usb_example" ]; then
  echo "INFO: Executable 'my_usb_example' already exists; skipping build."
else
  echo "INFO: Building 'my_usb_example'..."
  make
  echo "INFO: 'my_usb_example' built successfully."
fi

echo ""
echo "-----------------------------------"
echo ""

# Create symbolic links for SoapySDR in the conda environment if they do not exist
echo "INFO: Checking symbolic links for SoapySDR in the conda environment..."

SOAPYSDR_PY_SRC=$(find /usr/local/lib/python3.12/ -type f -name "SoapySDR.py" | grep -E "site-packages|dist-packages" | head -n1)
SOAPYSDR_SO_SRC=$(find /usr/local/lib/python3.12/ -type f -name "_SoapySDR.so" | grep -E "site-packages|dist-packages" | head -n1)
ENV_SITE_PACKAGES="$HOME/miniforge3/envs/env_RX-888_MK_II/lib/python3.12/site-packages"

SOAPYSDR_PY_LINK="$ENV_SITE_PACKAGES/SoapySDR.py"
SOAPYSDR_SO_LINK="$ENV_SITE_PACKAGES/_SoapySDR.so"

if [ ! -L "$SOAPYSDR_PY_LINK" ]; then
  ln -sf "$SOAPYSDR_PY_SRC" "$SOAPYSDR_PY_LINK"
  echo "INFO: Created symbolic link for SoapySDR.py"
else
  echo "INFO: Symbolic link for SoapySDR.py already exists; skipping."
fi

if [ ! -L "$SOAPYSDR_SO_LINK" ]; then
  ln -sf "$SOAPYSDR_SO_SRC" "$SOAPYSDR_SO_LINK"
  echo "INFO: Created symbolic link for _SoapySDR.so"
else
  echo "INFO: Symbolic link for _SoapySDR.so already exists; skipping."
fi

echo ""
echo "-----------------------------------"
echo ""

# Create udev rules for RX-888 MK II in DFU mode (bootloader) and SDR mode (loaded firmware)
RULES_FILE="/etc/udev/rules.d/99-rx888.rules"
DFU_RULE='SUBSYSTEM=="usb", ATTR{idVendor}=="04b4", ATTR{idProduct}=="00f3", MODE="0666"'
SDR_RULE='SUBSYSTEM=="usb", ATTR{idVendor}=="04b4", ATTR{idProduct}=="00f1", MODE="0666"'

create_rules=false

if [ -f "$RULES_FILE" ]; then
  if ! grep -qF "$DFU_RULE" "$RULES_FILE" || ! grep -qF "$SDR_RULE" "$RULES_FILE"; then
    create_rules=true
  fi
else
  create_rules=true
fi

if [ "$create_rules" = true ]; then
  echo "INFO: Creating udev rules for RX-888 MK II..."
  sudo tee "$RULES_FILE" > /dev/null <<EOF
$DFU_RULE
$SDR_RULE
EOF
  sudo udevadm control --reload-rules
  sudo udevadm trigger
  echo "INFO: udev rules created and reloaded."
else
  echo "INFO: udev rules for RX-888 MK II already exist; skipping creation."
fi

echo ""
echo "-----------------------------------"
echo ""

# Install Python dependencies if not already installed
echo "INFO: Checking Python dependencies..."

missing_py_pkgs=()
python -c "import numpy" 2>/dev/null || missing_py_pkgs+=("numpy")
python -c "import astropy" 2>/dev/null || missing_py_pkgs+=("astropy")
python -c "import matplotlib" 2>/dev/null || missing_py_pkgs+=("matplotlib")

if [ ${#missing_py_pkgs[@]} -eq 0 ]; then
  echo "INFO: Python dependencies already installed; skipping installation."
else
  echo "INFO: Installing missing Python dependencies: ${missing_py_pkgs[*]}"
  pip install "${missing_py_pkgs[@]}"
  echo "INFO: Python dependencies installed."
fi

echo ""
echo "-----------------------------------"
echo ""

echo "INFO: Installation completed successfully!"
echo ""
