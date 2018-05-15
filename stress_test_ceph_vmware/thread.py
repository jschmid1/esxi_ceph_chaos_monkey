import threading
import time
import sys
from cephops import CephOps

class BaseThread(threading.Thread):
    def __init__(self, callback=None, callback_args=None, *args, **kwargs):
        target = kwargs.pop('target')
        super(BaseThread, self).__init__(target=self.target_with_callback, *args, **kwargs)
        self.callback = callback
        self.method = target
        self.callback_args = callback_args

    def target_with_callback(self):
        self.method()
        if self.callback is not None:
            self.callback(*self.callback_args)

ALL_GOOD=True

def health_ok():
    if not CephOps().wait_for_health_ok():
        ALL_GOOD=False

def my_stupid_callback(arg1, arg2):
    if not ALL_GOOD:
        print("Life is not all good")
        sys.exit(1)
    print("Life is all good")
            

def start_thread():
    return BaseThread(name='test',
                      target=health_ok,
                      callback=my_stupid_callback,
                      callback_args=('huan', 'juan'))
