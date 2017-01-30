#!/usr/bin/env python3
import sys
import tkinter as tk

sys.path.append("..")
from handy.tkinter_tools import BindableTextArea
from netmem import UdpConnector
from netmem.network_memory import NetworkMemory


# logging.basicConfig(level=logging.ERROR)
# logging.basicConfig(level=logging.DEBUG)


# logging.getLogger(__name__).setLevel(logging.DEBUG)



class NetMemApp():
    def __init__(self, root, connector):
        self.window = root
        root.title("NetMem {}".format(str(connector)))

        # Data
        self.netmem = NetworkMemory()
        self.key_var = tk.StringVar()
        self.val_var = tk.StringVar()
        self.data_var = tk.StringVar()

        # View / Control
        self.create_widgets()

        # Connections
        self.netmem.add_listener(self.memory_updated)
        self.netmem.connect(connector)

        self.key_var.set("pet")
        self.val_var.set("cat")

    def create_widgets(self):
        lbl_key = tk.Label(self.window, text="Key:")
        lbl_key.grid(row=0, column=0, sticky=tk.E)
        txt_key = tk.Entry(self.window, textvariable=self.key_var)
        txt_key.grid(row=0, column=1, sticky=tk.W + tk.E)
        txt_key.bind('<Return>', lambda x: self.update_button_clicked())

        lbl_val = tk.Label(self.window, text="Value:")
        lbl_val.grid(row=1, column=0, sticky=tk.E)
        txt_val = tk.Entry(self.window, textvariable=self.val_var)
        txt_val.grid(row=1, column=1, sticky=tk.W + tk.E)
        txt_val.bind('<Return>', lambda x: self.update_button_clicked())

        lbl_score = tk.Label(self.window, text="Also demonstrate, bound to key 'score':")
        lbl_score.grid(row=2, column=0, sticky=tk.E)
        txt_score = tk.Entry(self.window, textvariable=self.netmem.tk_var("score"))
        txt_score.grid(row=2, column=1, sticky=tk.W + tk.E)

        btn_update = tk.Button(self.window, text="Update Memory", command=self.update_button_clicked)
        btn_update.grid(row=3, column=0, columnspan=2)

        txt_data = BindableTextArea(self.window, textvariable=self.data_var, width=30, height=5)
        txt_data.grid(row=4, column=0, columnspan=2)

    def update_button_clicked(self):
        key = self.key_var.get()
        val = self.val_var.get()
        with self.netmem:
            self.netmem.set(key, val)
            if key == "exit":
                self.netmem.close()

    def memory_updated(self, var, key, old_val, new_val):
        self.data_var.set(str(self.netmem))


def main():
    tk1 = tk.Tk()
    program1 = NetMemApp(tk1, UdpConnector(local_addr=("225.0.0.1", 9991),
                                           remote_addr=("225.0.0.2", 9992),
                                           new_thread=True))

    tk2 = tk.Toplevel()
    program2 = NetMemApp(tk2, UdpConnector(local_addr=("225.0.0.2", 9992),
                                           remote_addr=("225.0.0.1", 9991),
                                           new_thread=True))

    tk1.mainloop()


if __name__ == "__main__":
    main()
