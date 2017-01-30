#!/usr/bin/env python3
import logging
import tkinter as tk

from handy.tkinter_tools import BindableTextArea
from netmem.network_memory import NetworkMemory


# logging.basicConfig(level=logging.ERROR)
logging.basicConfig(level=logging.DEBUG)
# logging.getLogger(__name__).setLevel(logging.DEBUG)



class NetMemApp():
    def __init__(self, root, local_addr=None, remote_addr=None):
        self.window = root
        root.title("NetMem {}".format(local_addr))

        # Data
        self.netmem = NetworkMemory()
        self.key_var = tk.StringVar()
        self.val_var = tk.StringVar()
        self.data_var = tk.StringVar()

        # View / Control
        self.create_widgets()

        # Connections
        self.netmem.add_listener(self.memory_updated)
        self.netmem.connect_on_new_thread(local_addr=local_addr, remote_addr=remote_addr)
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

        lbl_score = tk.Label(self.window, text="Bound to 'score':")
        lbl_score.grid(row=4, column=0, sticky=tk.E)
        txt_score = tk.Entry(self.window, textvariable=self.netmem.tk_var("score"))
        txt_score.grid(row=4, column=1, sticky=tk.W + tk.E)

        btn_update = tk.Button(self.window, text="Update Memory", command=self.update_button_clicked)
        btn_update.grid(row=2, column=0, columnspan=2)

        txt_data = BindableTextArea(self.window, textvariable=self.data_var, width=30, height=5)
        txt_data.grid(row=3, column=0, columnspan=2)

    def update_button_clicked(self):
        print("update_button_clicked")
        key = self.key_var.get()
        val = self.val_var.get()
        with self.netmem:
            self.netmem.set(key, val)
            if key == "exit":
                self.netmem.close()
            # self.netmem["foo"] = "bar"
            # self.netmem["answer"] = 42
            # if "arr" not in self.netmem:
            #     self.netmem["arr"] = []
            # self.netmem["arr"].append(len(self.netmem["arr"]))
            # self.netmem.trigger_notification("arr")

    def memory_updated(self, var, key, old_val, new_val):
        print("memory_updated", var, key, old_val, new_val)
        self.data_var.set(str(self.netmem))



def main():
    tk1 = tk.Tk()
    # tk2 = tk.Toplevel()
    program1 = NetMemApp(tk1,
                         local_addr=("225.0.0.1", 9991),
                         remote_addr=("225.0.0.2", 9992))
    # program2 = NetMemApp(tk2,
    #                      local_addr=("225.0.0.2", 9992),
    #                      remote_addr=("225.0.0.1", 9991))

    tk1.mainloop()


if __name__ == "__main__":
    main()
