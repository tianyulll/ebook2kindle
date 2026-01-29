from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from .setting import Settings, save_settings


class SettingsDialog(tk.Toplevel):
    def __init__(self, master, settings: Settings, on_saved=None):
        super().__init__(master)
        self.title("Settings")
        self.transient(master)
        self.grab_set()

        self.settings = settings
        self.on_saved = on_saved

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        # --- Layout (CSS) ---
        css_frame = ttk.LabelFrame(container, text="Layout (CSS)", padding=10)
        css_frame.pack(fill="x")

        ttk.Label(css_frame, text="Paragraph text indent (em):").grid(row=0, column=0, sticky="w")
        self.indent_var = tk.DoubleVar(value=float(self.settings.text_indent_em))
        ttk.Spinbox(
            css_frame, from_=0.0, to=6.0, increment=0.1,
            textvariable=self.indent_var, width=8
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))

        ttk.Label(css_frame, text="Paragraph spacing (em):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.spacing_var = tk.DoubleVar(value=float(self.settings.paragraph_spacing_em))
        ttk.Spinbox(
            css_frame, from_=0.0, to=3.0, increment=0.1,
            textvariable=self.spacing_var, width=8
        ).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(8, 0))

        css_frame.columnconfigure(0, weight=1)

        # --- Email (Send to Kindle) ---
        mail_frame = ttk.LabelFrame(container, text="Email (Send to Kindle)", padding=10)
        mail_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(mail_frame, text="Kindle email:").grid(row=0, column=0, sticky="w")
        self.kindle_email_var = tk.StringVar(value=self.settings.kindle_email)
        ttk.Entry(mail_frame, textvariable=self.kindle_email_var, width=40).grid(
            row=0, column=1, sticky="w", padx=(10, 0)
        )

        ttk.Label(mail_frame, text="Sender email:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.sender_email_var = tk.StringVar(value=self.settings.sender_email)
        ttk.Entry(mail_frame, textvariable=self.sender_email_var, width=40).grid(
            row=1, column=1, sticky="w", padx=(10, 0), pady=(8, 0)
        )

        # Sender password (encrypted at save time)
        ttk.Label(mail_frame, text="Sender password:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.sender_pass_var = tk.StringVar(value="")

        self.sender_pass_entry = ttk.Entry(
            mail_frame, textvariable=self.sender_pass_var, width=40, show="•"
        )
        self.sender_pass_entry.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(8, 0))
        
        # Show password toggle
        self.show_pass_var = tk.BooleanVar(value=False)

        def _toggle_show_password() -> None:
            self.sender_pass_entry.configure(show="" if self.show_pass_var.get() else "•")

        ttk.Checkbutton(
            mail_frame,
            text="Show password",
            variable=self.show_pass_var,
            command=_toggle_show_password,
        ).grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(4, 0))
        
        # Hint (blank keeps existing)
        has_saved_pw = bool(getattr(self.settings, "sender_pass_enc", "") or "")
        hint = "Leave blank to keep the saved password." if has_saved_pw else "Enter an app password (recommended)."
        ttk.Label(mail_frame, text=hint).grid(row=4, column=1, sticky="w", padx=(10, 0), pady=(4, 0))

        ttk.Label(mail_frame, text="SMTP host:").grid(row=5, column=0, sticky="w", pady=(8, 0))
        self.smtp_host_var = tk.StringVar(value=self.settings.smtp_host)
        ttk.Entry(mail_frame, textvariable=self.smtp_host_var, width=30).grid(
            row=4, column=1, sticky="w", padx=(10, 0), pady=(8, 0)
        )

        ttk.Label(mail_frame, text="SMTP port:").grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.smtp_port_var = tk.IntVar(value=int(self.settings.smtp_port))
        ttk.Spinbox(
            mail_frame, from_=1, to=65535, increment=1,
            textvariable=self.smtp_port_var, width=8
        ).grid(row=5, column=1, sticky="w", padx=(10, 0), pady=(8, 0))

        self.smtp_tls_var = tk.BooleanVar(value=bool(self.settings.smtp_use_tls))
        ttk.Checkbutton(mail_frame, text="Use STARTTLS (recommended)", variable=self.smtp_tls_var).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        mail_frame.columnconfigure(0, weight=1)

        # --- Buttons ---
        btns = ttk.Frame(container)
        btns.pack(fill="x", pady=(14, 0))

        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Save", command=self._save).pack(side="right", padx=(0, 10))

        self.geometry("560x480")

    def _save(self):
        # Validate numeric CSS values
        try:
            indent = float(self.indent_var.get())
            spacing = float(self.spacing_var.get())
        except Exception:
            messagebox.showerror("Invalid value", "Indent/spacing must be numeric.")
            return

        if not (0.0 <= indent <= 6.0):
            messagebox.showerror("Invalid value", "Indent must be between 0 and 6 (em).")
            return
        if not (0.0 <= spacing <= 3.0):
            messagebox.showerror("Invalid value", "Spacing must be between 0 and 3 (em).")
            return

        # Email settings (light validation; keep it permissive)
        kindle_email = (self.kindle_email_var.get() or "").strip()
        sender_email = (self.sender_email_var.get() or "").strip()
        sender_password = (self.sender_pass_var.get() or "").strip()
        smtp_host = (self.smtp_host_var.get() or "").strip()
        try:
            smtp_port = int(self.smtp_port_var.get())
        except Exception:
            messagebox.showerror("Invalid value", "SMTP port must be an integer.")
            return

        if smtp_host == "":
            smtp_host = "smtp.gmail.com"

        if not (1 <= smtp_port <= 65535):
            messagebox.showerror("Invalid value", "SMTP port must be between 1 and 65535.")
            return

        # Apply
        self.settings.text_indent_em = indent
        self.settings.paragraph_spacing_em = spacing

        self.settings.kindle_email = kindle_email
        self.settings.sender_email = sender_email
        self.settings.smtp_host = smtp_host
        self.settings.smtp_port = smtp_port
        self.settings.smtp_use_tls = bool(self.smtp_tls_var.get())

        # Encrypt+store password only if user entered one
        if sender_password:
            try:
                self.settings.set_sender_password(sender_password)
            except Exception as e:
                messagebox.showerror("Password error", f"Could not store password securely:\n{e}")
                return
        # else: leave existing sender_pass_enc unchanged

        # Persist
        try:
            save_settings(self.settings)
        except Exception as e:
            messagebox.showerror("Save failed", f"Could not save settings:\n{e}")
            return

        if callable(self.on_saved):
            self.on_saved(self.settings)

        self.destroy()
