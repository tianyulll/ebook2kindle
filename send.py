import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from tkinter import messagebox
import os
from util import auto_close_messagebox

# Send an email 
# if gmail, the app password needs to be set up
def send_email(sender_email, sender_password, recipient_email, subject, attachment_paths, body=""):
    # Create a multipart message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Attach the body with the msg instance
    msg.attach(MIMEText(body, 'plain'))

    if not attachment_paths:
        messagebox.showerror("Error", "No file in the queue")
        return

    # Attach each file in the attachment_paths list
    for attachment_path in attachment_paths:
        
        if not os.path.isfile(attachment_path):
            messagebox.showerror("Error", f"File {attachment_path} does not exist or cannot be accessed.")
            continue

        with open(attachment_path, "rb") as attachment:
            # Instance of MIMEBase and named as part
            part = MIMEBase('application', 'octet-stream')

            # To change the payload into encoded form
            part.set_payload(attachment.read())

            # Encode into base64
            encoders.encode_base64(part)

            # Add header with the name of the file
            file_name = os.path.basename(attachment_path)
            part.add_header('Content-Disposition', 'attachment', filename=str(Header(file_name, 'utf-8')))

            # Attach the instance 'part' to instance 'msg'
            msg.attach(part)

    # Create SMTP session for sending the mail
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)  # Use the appropriate SMTP server and port
        server.starttls()  # Enable security
        server.login(sender_email, sender_password)  # Log in to your email account
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)  # Send the email
        auto_close_messagebox("Success", f"Email sent to {recipient_email} successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to send email. Error: {e}")
    finally:
        server.quit()  # Close the connection

