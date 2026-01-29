import tkinter as tk
from tkinterdnd2 import TkinterDnD, DND_FILES
from util import convert_format
from tkinter import font as tkFont
from tkinter import messagebox

from userConfig import load_settings, SettingsDialog, generate_css
from send2device import send_files_via_smtp, EmailSendError


class App:
    

    def __init__(self):
        
        self.root = TkinterDnD.Tk()
        self.root.title("ebook2kindle helper")
        self.root.geometry("600x600")
        
        self.settings = load_settings() 
        self.selected_files = []
        self.output_files = [] 
        self.create_widgets()

    def on_drop(self, event):
        self.selected_files.extend(list(self.root.tk.splitlist(event.data)))
        self.drag_label.config(text="Selected Files:\n" + "\n".join(self.selected_files),
                               wraplength=550, justify="left",
                               font=("Helvetica", 14), fg="black")

    def open_settings(self):
        def on_saved(updated_settings):
            self.settings = updated_settings
        SettingsDialog(self.root, settings=self.settings, on_saved=on_saved)


    def create_widgets(self):
        # Create a combined frame for drag-and-drop and display at the top of the window
        drag_frame = tk.Frame(self.root, bg="white", height=300)
        drag_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create a label inside the combined frame for dragging files
        self.drag_label = tk.Label(drag_frame, text="Drag and drop Your txt files", font=("Helvetica", 28), bg="white", fg="Grey", anchor="center")
        self.drag_label.pack(fill=tk.BOTH, expand=True, pady=10)

        # Bind the drag-and-drop event to the on_drop function
        self.drag_label.drop_target_register(DND_FILES)
        self.drag_label.dnd_bind('<<Drop>>', self.on_drop)

        # Create a frame to hold the buttons side by side
        button_frame = tk.Frame(self.root, height=10)
        button_frame.pack(pady=5)

        # button to start processing files
        process_button = tk.Button(button_frame, text="Start Conversion", command=self.click_process,
                                    relief=tk.FLAT, borderwidth=0, highlightthickness=0)

        # button for send2device
        send_button = tk.Button(button_frame, text = "Send2Device",
                                command = self.click_send,
                                relief=tk.FLAT, borderwidth=0, highlightthickness=0)
        
        # button to reset queues
        trash_button = tk.Button(drag_frame,  text= "🗑️", command = self.reset_app,
                                 relief=tk.FLAT, highlightbackground="white")
                                 #borderwidth=0, bg="white", highlightbackground="white", padx=0, pady=0)
        trash_button.pack(side=tk.RIGHT, padx = 3, pady=5)

        # button to reset email credentials
        helv24 = tkFont.Font(family='Helvetica', size=24)
        reset_button = tk.Button(button_frame, text="⚙", font=helv24, command=self.open_settings, 
                                 relief=tk.FLAT, bd=0, borderwidth=0)

        button_frame.columnconfigure(1, weight=1)
        process_button.grid(row=0, column=0, padx=40)
        send_button.grid(row=0, column=1, padx=40)
        reset_button.grid(row=0, column=5, padx=0)

        # Create a text widget to display command output
        self.output_text = tk.Text(self.root, height=5, wrap=tk.WORD, bg="black", fg="white", 
                            font=("Arial", 14), bd=0, highlightthickness=0)
        self.output_text.pack(side = tk.BOTTOM, fill=tk.BOTH, expand=False)
    
    def click_process(self):
        
        self.output_text.delete(1.0, tk.END)  # Clear the output text box

        if not self.selected_files:
            tk.messagebox.showwarning("Warning", "No files selected.")
            return
        
        self.settings = load_settings()

        # Read in CSS configuration
        css = generate_css(
            text_indent_em=self.settings.text_indent_em,
            paragraph_spacing_em=self.settings.paragraph_spacing_em,
        )

        for file_path in self.selected_files:
            try:
                # Display the content in the label (optional)
                self.drag_label.config(text=f"Processing file: {file_path}")
                result = convert_format(file_path=file_path, 
                                        output_display=self.output_text,
                                        css=css)
                self.output_files.append(result)
                # Update the label with success message
                self.drag_label.config(text=f"Conversion complete: {result}")
            
            except Exception as e:
                tk.messagebox.showerror("Error", f"Error processing {file_path}: {e}")
                return
        
        self.drag_label.config(text=f"output files: {self.output_files}")

    def reset_app(self):
        self.reset_input()
        self.output_files.clear()
        self.output_text.delete(1.0, tk.END)
    
    def reset_input(self):
        self.selected_files.clear()
        self.drag_label.event_delete    
        self.drag_label.config(text="Drag and drop files here", font=("Helvetica", 28), fg="Grey")

    # send file to device upon clicking the send button
    def click_send(self):
        # Reload settings in case user just updated them
        self.settings = load_settings()
        s = self.settings

        if not getattr(self, "output_files", None):
            messagebox.showwarning("Nothing to send", "No output files found. Convert something first.")
            return

        to_addr = (s.kindle_email or "").strip()
        smtp_user = (s.sender_email or "").strip()
        smtp_host = (s.smtp_host or "").strip()
        smtp_port = int(s.smtp_port or 587)

        # Basic validation
        if not to_addr:
            messagebox.showerror("Missing setting", "Please set your Kindle email in Settings.")
            return
        if not smtp_user:
            messagebox.showerror("Missing setting", "Please set your Sender email in Settings.")
            return
        if not getattr(s, "sender_pass_enc", ""):
            messagebox.showerror("Missing setting", "Please set your Sender password in Settings.")
            return
        if not smtp_host:
            messagebox.showerror("Missing setting", "Please set your SMTP host in Settings.")
            return

        try:
            smtp_password = s.get_sender_password()
            if not smtp_password:
                messagebox.showerror("Missing setting", "Sender password is empty. Please re-enter it in Settings.")
                return

            send_files_via_smtp(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                to_addr=to_addr,
                files=self.output_files,
                subject="Send to Kindle",
                body="Sent from ebook2kindle helper.",
                use_starttls=bool(s.smtp_use_tls),
            )

            messagebox.showinfo("Sent", f"Sent {len(self.output_files)} file(s) to:\n{to_addr}")

        except EmailSendError as e:
            messagebox.showerror("Send failed", str(e))
        except Exception as e:
            messagebox.showerror("Unexpected error", f"{e}")