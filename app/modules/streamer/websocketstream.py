from six.moves import queue

class WebsocketStream(object):
    def __init__(self):
        self._buff = queue.Queue()
        self.closed = False
    
    def end(self):
        self.closed = True

    def write(self, in_data):
        self._buff.put(in_data)

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            
            yield chunk
