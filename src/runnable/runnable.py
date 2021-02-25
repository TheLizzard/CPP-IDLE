from tkinter import filedialog
from functools import partial
import tkinter as tk
import subprocess
import platform
import time
import sys
import os

from .terminal import TkTerminal
from constants.settings import settings


DEFAULT_ARGS = ()


def get_os_bits() -> int:
    return 8 * struct.calcsize("P")

def get_os() -> int:
    os = platform.system()
    result = os.lower()
    if result in ("windows", "linux"):
        return result
    else:
        raise OSError("Can't recognise the OS type.")

OS = get_os()
PATH = os.path.dirname(os.path.realpath(__file__))
if OS == "windows":
    PATH_EXECUTABLE = settings.compiler.win_path_executable.format(path=PATH)
    COMPILE_COMMAND = settings.compiler.win_compile.format(out=PATH_EXECUTABLE,
                                                           _in="{_in}")
    RUN_COMMAND = settings.compiler.win_run_command.format(file=PATH_EXECUTABLE)
if OS == "linux":
    PATH_EXECUTABLE = settings.compiler.lin_path_executable.format(PATH)
    COMPILE_COMMAND = settings.compiler.lin_compile.format(out=PATH_EXECUTABLE)
    RUN_COMMAND = settings.compiler.win_lin_command.format(file=PATH_EXECUTABLE)


FILE_TYPES = (("C++ file", "*.cpp"),
              ("Text file", "*.txt"),
              ("All types", "*"))


class RunnableText:
    def __init__(self, text_widget):
        self.terminal = None
        self.text = text_widget
        self.saved_text = None
        self.file_name = None
        self.set_up_bindings()

    def set_up_bindings(self):
        self.text.bind("<Control-s>", self.save)
        self.text.bind("<Control-S>", self.save)
        self.text.bind("<Control-Shift-s>", self.saveas)
        self.text.bind("<Control-Shift-S>", self.saveas)
        self.text.bind("<Control-o>", self.open)
        self.text.bind("<Control-O>", self.open)

        self.text.bind("<F5>", self.run)
        self.text.bind("<Shift-F5>", self.run_with_command)

    def run_with_command(self, event=None):
        global DEFAULT_ARGS
        input_box = Question("What should the args be?")
        input_box.set(DEFAULT_ARGS)
        input_box.wait()
        inputs = input_box.get()
        input_box.destroy()
        if inputs is None:
            return None
        DEFAULT_ARGS = tuple(inputs)
        self.run(event, inputs)

    def run(self, event=None, args=None):
        if (self.terminal is None) or self.terminal.closed:
            self.terminal = TkTerminal()

        self.terminal.clear()
        self.terminal.text.focus_force()

        # Check if the file is saved
        work_saved = self.saved_text == self.text.get("0.0", "end").rstrip()
        if (not work_saved) or (self.file_name is None):
            msg = "You need to first save the file."
            self.terminal.stderr_write(msg, add_padding=True)
            return None

        # Create the compile instuction
        command = COMPILE_COMMAND.format(_in=self.file_name)

        msg = "Compiling the program"
        self.terminal.stdout_write(msg, add_padding=True)

        error = self.terminal.run(command, callback=self.text.update)
        msg = "Process exit code: %s" % str(error)
        self.terminal.stdout_write(msg, add_padding=True)
        if isinstance(error, Exception):
            return None
        if error == 0:
            # Run the program if compiled
            msg = "Running the program"
            self.terminal.stdout_write(msg, add_padding=True)
            if args is None:
                command = RUN_COMMAND
            else:
                command = RUN_COMMAND + " " + " ".join(args)
            error = self.terminal.run(command, callback=self.text.update)
            msg = "Process exit code: %s" % str(error)
            self.terminal.stdout_write(msg, add_padding=True)

    def save(self, event=None):
        if self.file_name is None:
            self.saveas()
        else:
            self._save(self.file_name)

    def open(self, event=None):
        file = filedialog.askopenfilename(filetypes=FILE_TYPES)
        if (file != "") and (file != ()):
            self.file_name = file
            self._open(file)

    def _open(self, filename):
        with open(filename, "r") as file:
            text = file.read().rstrip()
            self.saved_text = text
            self.text.delete("0.0", "end")
            self.text.insert("end", text)
            self.text.see("end")
        #self.root.title(os.path.basename(filename))

    def saveas(self, event=None):
        file = filedialog.asksaveasfilename(filetypes=FILE_TYPES,
                                            defaultextension=FILE_TYPES[0][1])
        if file != "":
            self.file_name = file
            self.save(file)

    def _save(self, filename):
        text = self.text.get("0.0", "end")
        with open(filename, "w") as file:
            file.write(text)
            self.saved_text = text.rstrip()
        #self.root.title(os.path.basename(filename))


class Question:
    def __init__(self, question):
        self.force_quit = False
        self.input_boxes = []
        self.root = tk.Toplevel()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.label = tk.Label(self.root, text=question)
        self.answer_frame = tk.Frame(self.root)
        self.done_button = tk.Button(self.root, text="Done", command=self.done)
        self.cancel_button = tk.Button(self.root, text="Cancel",
                                       command=self.on_closing)

        self.label.grid(row=1, column=1, columnspan=2, sticky="news")
        self.answer_frame.grid(row=2, column=1, columnspan=2, sticky="news")
        self.done_button.grid(row=3, column=1, sticky="news")
        self.cancel_button.grid(row=3, column=2, sticky="news")

        self.add_input_box()

    def on_closing(self):
        self.force_quit = True
        self.root.quit()
        self.root.destroy()

    def done(self):
        self.root.quit()

    def minus(self, entry):
        if len(self.input_boxes) == 1:
            return None
        del self.input_boxes[self.get_number_from_entry(entry)]
        self.regrid()

    def plus(self, entry):
        self.add_input_box(self.get_number_from_entry(entry)+1)

    def add_input_box(self, pos="last"):
        entry = tk.Entry(self.answer_frame)
        entry.focus()

        command = partial(self.minus, entry)
        button_min = tk.Button(self.answer_frame, text=" - ", command=command)

        command = partial(self.plus, entry)
        buton_plus = tk.Button(self.answer_frame, text=" + ", command=command)

        if pos == "last":
            number = len(self.input_boxes)
            entry.grid(row=number, column=1, sticky="news")
            button_min.grid(row=number, column=2, sticky="news")
            buton_plus.grid(row=number, column=3, sticky="news")
            self.input_boxes.append((entry, button_min, buton_plus))
        else:
            self.input_boxes.insert(pos, (entry, button_min, buton_plus))
            self.regrid()

    def regrid(self):
        for child in self.answer_frame.winfo_children():
            child.grid_forget()
        for i, (entry, button_min, buton_plus) in enumerate(self.input_boxes):
            entry.grid(row=i, column=1, sticky="news")
            button_min.grid(row=i, column=2, sticky="news")
            buton_plus.grid(row=i, column=3, sticky="news")

    def get_number_from_entry(self, target_entry):
        for i, (entry, _, _) in enumerate(self.input_boxes):
            if target_entry == entry:
                return i
        raise IndexError("Entry not found!")

    def wait(self):
        self.root.mainloop()

    def get(self):
        if self.force_quit:
            return None
        output = []
        for entry, _, _ in self.input_boxes:
            output.append(entry.get())
        return output

    def set(self, values):
        for value in values:
            self.add_input_box()
            entry, _, _ = self.input_boxes[len(self.input_boxes)-1]
            entry.insert("end", value)
        self.minus(self.input_boxes[0][0])

    def destroy(self):
        if not self.force_quit:
            self.root.destroy()