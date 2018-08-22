#!/usr/bin/env python3
# From https://stackoverflow.com/questions/47895765/use-asyncio-and-tkinter-together-without-freezing-the-gui
import threading
from functools import partial
from tkinter import *
from tkinter import messagebox
import asyncio
import random


# Please wrap all this code in a nice App class, of course

def _run_aio_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
aioloop = asyncio.new_event_loop()
threading.Thread(target=partial(_run_aio_loop, aioloop), daemon=True).start()

buttonT = None

def do_freezed():
    """ Button-Event-Handler to see if a button on GUI works. """
    messagebox.showinfo(message='Tkinter is reacting.')

def do_tasks():
    """ Button-Event-Handler starting the asyncio part. """
    buttonT.configure(state=DISABLED)
    asyncio.run_coroutine_threadsafe(do_urls(), aioloop)

async def one_url(url):
    """ One task. """
    sec = random.randint(1, 3)
    await asyncio.sleep(sec)
    return 'url: {}\tsec: {}'.format(url, sec)

async def do_urls():
    """ Creating and starting 10 tasks. """
    tasks = [one_url(url) for url in range(3)]
    completed, pending = await asyncio.wait(tasks)
    results = [task.result() for task in completed]
    print('\n'.join(results))
    buttonT.configure(state=NORMAL)  # Tk doesn't seem to care that this is called on another thread


if __name__ == '__main__':
    root = Tk()

    buttonT = Button(master=root, text='Asyncio Tasks', command=do_tasks)
    buttonT.pack()
    buttonX = Button(master=root, text='Freezed???', command=do_freezed)
    buttonX.pack()

    root.mainloop()