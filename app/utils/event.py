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

def start_run_untile_complete(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coro)
    loop.close()

def thread_run_until_complete(coro):
    t = Thread(target=start_run_untile_complete, args=(coro, ))
    t.setDaemon(True)
    t.start()
    return t
