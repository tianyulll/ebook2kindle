import tkinter as tk
import subprocess
import os
import sys

# automatically close the message box in 5 seconds
def auto_close_messagebox(title, message, duration=5000):
    msg_box = tk.Toplevel()
    msg_box.title(title)
    tk.Label(msg_box, text=message).pack(padx=20, pady=20)
    msg_box.after(duration, msg_box.destroy)

# Convert the format of the input files
def convert_format(file_path, output_display):
    
    input_dir = os.path.dirname(file_path)
    original_working_dir = os.getcwd()  
    
    output_file = str.split(os.path.splitext(os.path.basename(file_path))[0], sep="(")[0]
    
    # send-to-kindle accepts epub. No need conversion
    if os.path.splitext(file_path)[1] == ".epub":
        return os.path.abspath(file_path)

    if getattr(sys, 'frozen', False):
    # If the application is running as a bundled executable
        base_path = sys._MEIPASS
    else:
        # If the application is running in a development environment
        base_path = os.path.dirname(os.path.abspath(__file__))

    kaf_cli = os.path.join(base_path, 'kaf-cli')
    ebook_convert = os.path.join(base_path, 'ebook-converter')
    output_file = os.path.abspath(input_dir + "/" + output_file + ".epub")

    if os.path.splitext(file_path)[1] == ".txt":
        # calling kaf-cli for optimized txt2epub conversion 
        command = [kaf_cli,'-format', "epub",'-filename', file_path,
                   '-match', "第.{1,10}章",
                    '-out', output_file] 
    else:
        # calling calibre for other format conversion
        command = [ebook_convert, file_path, output_file]
    
    os.chdir(input_dir)
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        os.chdir(original_working_dir)
        raise Exception(result.stderr)
    
    # Print the output of the command in the output_text widget
    output_display.insert(tk.END, f"Output for {file_path}:\n{result.stdout}\n")
    if result.stderr != "": 
        output_display.insert(tk.END, f"Error (if any) for {file_path}:\n{result.stderr}\n")
    # Automatically scroll to the bottom
    output_display.yview_moveto(1.0)
    
    os.chdir(original_working_dir)
    return os.path.abspath(output_file)
