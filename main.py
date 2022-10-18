"""
Nigel Bazzeghin
CIT2553
Lab 5 - Steganography

 Notes:
     This script requires 3 Windows CLI tools to accomplish the task as well as the pywin32 library and python magic
     library to determine file type from headers.
     1) stegbreak.exe
     2) stegdetect.exe
     3) jpseek.exe (CLI version of Jphswin seek function)
"""

import mimetypes
import re
import time
import os
import win32com.client
from pathlib import Path
from subprocess import run, Popen, PIPE, STDOUT, STARTUPINFO, STARTF_USESHOWWINDOW
from winmagic import magic
from hashlib import md5
from datetime import datetime

# Used to pass keystrokes to JPSeek
shell = win32com.client.Dispatch("WScript.Shell")

start_info = STARTUPINFO()
start_info.dwFlags |= STARTF_USESHOWWINDOW

# Found using command: find . -type f -name '*.*' | sed 's|.*\.||' | sort -u
file_extensions = [".jpg", ".jpeg", ".JPG"]

# Set the path to where your CLI tools reside
tools_location = "..\StegoTools"

# List of files that have had steganography broken out of them
broken_files = []


class Stego:
    def __int__(self, md5hash, filename, password, detect):
        self.md5hash = md5hash
        self.filename = filename
        self.password = password
        self.detect = detect


def extract(input_file, password):
    out_file = f'out\\{input_file.parts[1]}--{input_file.name}--out'
    file = Popen([f"{tools_location}\\jpseek.exe", f"{input_file}", out_file],
                 stdout=PIPE, stdin=PIPE, stderr=PIPE)
    # send the password to the input of jpseek
    shell.SendKeys(f'{password}{{ENTER}}')

    # wait for jpseek to extract file
    while file.poll() is None:
        time.sleep(0.2)

    mime = magic.from_file(out_file, mime=True)
    print(f'JPSeek Extracted file type {mime} from {input_file}')
    file_type = mimetypes.guess_extension(mime)
    if not Path(f'{out_file}{file_type}').is_file():
        os.rename(out_file, f'{out_file}{file_type}')


def getmd5(input_file):
    file_hash = md5()
    with open(input_file, "rb") as f:
        # Read file in 4k blocks, so we can md5 large files
        for byte_block in iter(lambda: f.read(4096), b""):
            file_hash.update(byte_block)
    return file_hash.hexdigest().upper()


def stegdetect(input_file):
    file = Popen([f"{tools_location}\\stegdetect.exe", "-tjpoi", "-s5", f"{input_file}"], stdin=PIPE, stdout=PIPE,
                 stderr=PIPE, startupinfo=start_info)
    file.wait()
    output, error = file.communicate()
    return output.decode('utf-8').strip().split(':')[1]


def stegbreak(input_dir):
    count = 0
    with Popen([f"{tools_location}\\stegbreak.exe", "-r", f"{tools_location}\\rules.ini", "-f",
                f"{tools_location}\\words", f"{input_dir}"], stdin=PIPE, stdout=PIPE, stderr=PIPE,
               startupinfo=start_info) as p:
        print(f'---Starting Stegbreak for files in [{input_dir}]')

        for line in p.stdout:
            output = line.decode().strip().split(':')
            if "(" in output[1]:
                with open("files.txt", "a") as report:
                    report.write(f'{output}\n')
                file = Stego()
                file.filename = output[0]
                file.password = re.search("\((.+?)\)", output[1]).group(1)
                broken_files.append(file)
                count += 1
                print(f'count: {count}')
            if count >= 5:
                p.kill()

        print(f'---Complete')


def main():
    # Folder containing all the images.
    # target_dir = "bs"
    target_dir = "stego.cyber.rose.edu"

    # TODO: Something did not work correctly when targeting the large directory
    # for subdir, dirs, files in os.walk(target_dir):
    #     stegbreak(subdir)

    with open("files.txt", "r") as f:
        lines = [line.rstrip().split(':') for line in f]
        for line in lines:
            file = Stego()
            file.filename = line[0]
            file.password = re.search("\((.+?)\)", line[1]).group(1)
            broken_files.append(file)

    for i, item in enumerate(broken_files):
        item.md5hash = getmd5(item.filename)
        item.detect = stegdetect(item.filename)
        extract(Path(item.filename), item.password)
        broken_files[i] = item

    with open("report.txt", "a") as report:
        now = datetime.now()
        dt_string = now.strftime("%m/%d/%Y %H:%M:%S")
        print(f"\n###### {dt_string} ######")
        report.write(f"\n###### {dt_string} ######\n")
        for bf in broken_files:
            print(f'{bf.md5hash:<35} {bf.filename:<70} {bf.password:<25} {bf.detect:<10}')
            # report.write(f'{bf.md5hash:<35} {bf.filename:<70} {bf.password:<25} {bf.detect:<10}\n')
            report.write(f'{bf.md5hash},{bf.filename},{bf.password},{bf.detect}\n')


if __name__ == '__main__':
    main()
