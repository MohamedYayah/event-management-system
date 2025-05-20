# Moved to tests/tkinter_test.py tkinter as tk

root = tk.Tk()
root.title("Tkinter Test")
root.geometry("300x200")
label = tk.Label(root, text="If you see this, Tkinter works!")
label.pack(pady=50)
root.mainloop()
