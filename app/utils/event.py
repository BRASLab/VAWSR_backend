import asyncio
from threading import Thread

def start_new_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def thread_new_event_loop():
    loop = asyncio.new_event_loop()
    t = Thread(target=start_new_event_loop, args=(loop,))
    t.setDaemon(True)
    t.start()
    return loop
