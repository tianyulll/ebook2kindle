import os
from util import auto_close_messagebox
from tkinter import simpledialog, messagebox
from cryptography.fernet import Fernet
import json
import platformdirs

# Get a directory in the user's home or app data folder
def get_app_data_dir():
    app_dir = platformdirs.user_data_dir(appname="ebook2kindle", appauthor="emailConfig")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True) 
    return app_dir

# Encryption/Decryption utility functions
def load_key():
    """Load or generate a key for encryption/decryption."""
    
    app_data_dir = get_app_data_dir()
    key_path = os.path.join(app_data_dir, "ebook2kindle_email.key")
    
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        with open(key_path, "wb") as key_file:
            key_file.write(key)
    else:
        with open(key_path, "rb") as key_file:
            key = key_file.read()
    return key

def encrypt_password(password, key):
    fernet = Fernet(key)
    return fernet.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password, key):
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_password.encode()).decode()

# load a json path to store user credentials
def get_config_path():
    return os.path.join(get_app_data_dir(), "ebook2kindle_credential.json")

def get_key_path():
    return os.path.join(get_app_data_dir(), "ebook2kindle_email.key")

# save info into json
def save_credentials(email, kindle_email, password):
    key = load_key()
    encrypted_password = encrypt_password(password, key)
    config_path = get_config_path()
    with open(config_path, "w") as cred_file:
        json.dump({"email": email, "kindle_email": kindle_email, 
                   "password": encrypted_password}, cred_file)
    messagebox.showinfo(f'saving {config_path}')

def load_credentials():

    # write credentials into json
    if os.path.exists(get_config_path()):
        key = load_key()
        with open(get_config_path(), "r") as cred_file:
            creds = json.load(cred_file)
            email = creds["email"]
            kindle_email = creds["kindle_email"]
            password = decrypt_password(creds["password"], key)
            return email, kindle_email, password
    
    # pop-up window to write credentials
    else:
        email = simpledialog.askstring("Input", "Enter your sending email:")
        kindle_email = simpledialog.askstring("Input", "Enter your kindle email:")
        password = simpledialog.askstring("Input", "Enter your password:", show="*")

        if email and password and kindle_email:
            save_credentials(email, kindle_email, password)
            return email, kindle_email, password
        else:
            messagebox.showerror("Error", f"Failed to save credentials")

def remove_credentials():
    try:
        os.remove(get_config_path())
        os.remove(get_key_path())
    except Exception as e:
        auto_close_messagebox("Error", f"Failed to remove credentials. \
                              They might have been removed already. \
                              error:{e}")
        return
    auto_close_messagebox("Removed Email info", message="Please re-enter your email configuration")