import subprocess
import os


def install_package(package):
    try:
        subprocess.check_call(["pip", "install", package, "--ignore-installed"])
        print(f"Successfully installed {package}")
    except subprocess.CalledProcessError:
        print(f"Failed to install {package}, skipping...")

#TODO Change this to your path 
requirements_path = "/Users/fgv/Documents/Coding/repos/risk_pylibrary/requirements.txt"


with open(requirements_path, "r") as f: 
    for line in f:
        package_name = line.strip()
        install_package(package_name)