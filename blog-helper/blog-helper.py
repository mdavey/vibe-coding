#!/usr/bin/env python3
"""
blog-helper/blog-helper.py
Simple Markdown editor using tkinter.
Usage: python blog-helper/blog-helper.py
The file dialogs start in the Hugo content directory by default.
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, simpledialog, messagebox, font

# Default Hugo content directory
CONTENT_DIR = r"C:\Users\Matthewd\Documents\GitHub\project-2501.net\content\post"
IMAGEMAGICK_BIN=r"C:\Program Files\ImageMagick-7.1.0-Q16-HDRI\magick.exe"

class MarkdownEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Blog Helper - Untitled")
        self.current_file = None
        self.dirty = False

        self._setup_ui()
        self._bind_shortcuts()

    def _setup_ui(self):
        # Main frame
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Text widget with scrollbar
        text_frame = ttk.Frame(self.root)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        mono = font.nametofont("TkFixedFont")
        mono.configure(size=11)

        self.text = tk.Text(text_frame, wrap="word", undo=True, font=mono)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.insert("1.0", "")
        self.text.edit_modified(False)

        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=vsb.set)

        # Status bar
        self.status = ttk.Label(self.root, text="Untitled — L:1 C:1", anchor="w")
        self.status.grid(row=1, column=0, sticky="ew")

        # Menus
        self._build_menus()

        # Bind events
        self.text.bind("<<Modified>>", self._on_text_modified)
        self.text.bind("<KeyRelease>", self._on_cursor_moved)
        self.text.bind("<ButtonRelease>", self._on_cursor_moved)

    def _build_menus(self):
        menubar = tk.Menu(self.root)
        # File menu
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_file_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        # Insert menu
        insert_menu = tk.Menu(menubar, tearoff=False)
        insert_menu.add_command(label="Insert Image...", command=self.insert_image)
        insert_menu.add_command(label="Insert Youtube Link...", command=self.insert_youtube_link)
        menubar.add_cascade(label="Insert", menu=insert_menu)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label="Render with Hugo", state="disabled")
        tools_menu.add_command(label="Preview with Hugo", state="disabled")
        menubar.add_cascade(label="Tools", menu=tools_menu)

        self.root.config(menu=menubar)

    def _bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-N>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-O>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-S>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_file_as())
        self.root.bind("<Control-q>", lambda e: self.on_exit())
        self.root.bind("<Control-Q>", lambda e: self.on_exit())

    def _on_text_modified(self, event=None):
        if self.text.edit_modified():
            self.dirty = True
            self._update_status()
            # reset modified flag
            self.text.edit_modified(False)

    def _on_cursor_moved(self, event=None):
        self._update_status()

    def _update_status(self):
        # filename or Untitled
        name = os.path.basename(self.current_file) if self.current_file else "Untitled"
        # line and column
        idx = self.text.index("insert")
        line, col = idx.split(".")
        col = str(int(col) + 1)
        dirty_mark = " *" if self.dirty else ""
        status_text = f"{name}{dirty_mark} — L:{line} C:{col}"
        self.status.config(text=status_text)
        # also update window title with full path if available
        if self.current_file:
            self.root.title(f"Blog Helper - {self.current_file}")
        else:
            self.root.title("Blog Helper - Untitled")

    def _prompt_save_if_dirty(self):
        if not self.dirty:
            return True
        res = messagebox.askyesnocancel("Save changes?", "You have unsaved changes. Save now?")
        if res is None:
            # cancel
            return False
        if res:
            return self.save_file()
        return True

    def new_file(self):
        ok = self._prompt_save_if_dirty()
        if not ok:
            return
        self.text.delete("1.0", "end")
        self.current_file = None
        self.dirty = False
        self.text.edit_modified(False)
        self._update_status()

    def open_file(self):
        ok = self._prompt_save_if_dirty()
        if not ok:
            return
        initial = CONTENT_DIR if os.path.isdir(CONTENT_DIR) else os.getcwd()
        path = filedialog.askopenfilename(initialdir=initial, title="Open Markdown file", filetypes=[("Markdown files", "*.md;*.markdown"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file:\n{e}")
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", data)
        self.current_file = path
        self.dirty = False
        self.text.edit_modified(False)
        self._update_status()

    def save_file(self):
        if not self.current_file:
            return self.save_file_as()
        try:
            data = self.text.get("1.0", "end-1c")
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(data)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{e}")
            return False
        self.dirty = False
        self.text.edit_modified(False)
        self._update_status()
        return True

    def save_file_as(self):
        initial = CONTENT_DIR if os.path.isdir(CONTENT_DIR) else os.getcwd()
        path = filedialog.asksaveasfilename(initialdir=initial, title="Save Markdown file", defaultextension=".md", filetypes=[("Markdown files", "*.md;*.markdown"), ("All files", "*.*")])
        if not path:
            return False
        try:
            data = self.text.get("1.0", "end-1c")
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{e}")
            return False
        self.current_file = path
        self.dirty = False
        self.text.edit_modified(False)
        self._update_status()
        return True

    def insert_image(self):
        # This command only works after the current markdown file has been saved
        if not self.current_file:
            messagebox.showinfo("Insert Image", "This command only works after the current file has a name. Please save the file first.")
            return

        initial = CONTENT_DIR if os.path.isdir(CONTENT_DIR) else os.getcwd()
        path = filedialog.askopenfilename(
            initialdir=initial,
            title="Select image",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.webp;*.gif;*.avif"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            base = os.path.splitext(os.path.basename(path))[0]
            dest_dir = os.path.dirname(self.current_file)

            web_name = f"{base}_web.webp"
            thumb_name_no_ext = f"{base}_web_thumb"
            thumb_name = f"{thumb_name_no_ext}.webp"

            web_path = os.path.join(dest_dir, web_name)
            thumb_path = os.path.join(dest_dir, thumb_name)

            # Ensure destination directory exists
            os.makedirs(dest_dir, exist_ok=True)

            # Build ImageMagick commands.
            # Use IMAGEMAGICK_BIN (expected to be path to magick.exe) and let it resize while preserving aspect ratio.
            # Full size: fit inside 1920x1080, good quality.
            cmd_full = [IMAGEMAGICK_BIN, path, "-resize", "1920x1080>", "-quality", "90", web_path]
            # Thumbnail: max width 600px, average quality.
            cmd_thumb = [IMAGEMAGICK_BIN, path, "-resize", "400x>", "-quality", "70", thumb_path]

            # Run conversions
            subprocess.run(cmd_full, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(cmd_thumb, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        except FileNotFoundError:
            messagebox.showerror("Error", f"ImageMagick binary not found: {IMAGEMAGICK_BIN}")
            return
        except subprocess.CalledProcessError as e:
            stderr = ""
            try:
                stderr = e.stderr.decode("utf-8") if getattr(e, "stderr", None) else str(e)
            except Exception:
                stderr = str(e)
            messagebox.showerror("Error", f"ImageMagick failed:\n{stderr}")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process image:\n{e}")
            return

        # Insert the Hugo shortcodes template with the generated filenames.
        insert_text = '[ {{< webp ' + thumb_name_no_ext + ' >}} ]( {{< static "' + web_name + '" >}} )'
        self.text.insert("insert", insert_text)
        self.dirty = True
        self._update_status()

    def insert_youtube_link(self):
        url = simpledialog.askstring("Insert Youtube Link", "Enter YouTube URL:")
        if not url:
            return
        self.text.insert("insert", url)
        self.dirty = True
        self._update_status()

    def on_exit(self):
        ok = self._prompt_save_if_dirty()
        if not ok:
            return
        self.root.destroy()

def main():
    root = tk.Tk()
    root.geometry("900x700")
    app = MarkdownEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()