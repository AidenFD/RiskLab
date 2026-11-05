"""Single admitted job; immutable inputs and thread-safe cancellation token."""
import logging,threading,time
from PySide6.QtCore import QThread,Signal
from risklab.core.models import ProgressSnapshot

class Job(QThread):
    completed=Signal(int,object)
    failed=Signal(int,str,bool)
    advanced=Signal(int,object)
    def __init__(self,identity,function,parent=None):
        super().__init__(parent);self.identity=identity;self.function=function;self.token=threading.Event();self.last=0.
    def report(self,phase,n,total):
        now=time.monotonic()
        if now-self.last>.08 or n==total:
            self.advanced.emit(self.identity,ProgressSnapshot(phase,int(n),int(total)));self.last=now
    def run(self):
        try:
            value=self.function(self.token.is_set,self.report)
            self.completed.emit(self.identity,value)
        except InterruptedError as exc:self.failed.emit(self.identity,str(exc),True)
        except Exception as exc:
            logging.getLogger('risklab').exception('Job %s failed',self.identity)
            self.failed.emit(self.identity,str(exc),False)
