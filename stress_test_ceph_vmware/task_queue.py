import logging
import time
from config import Config
from utils import Utils
from colorama import Fore, Style

log = logging.getLogger(__name__)


class Queue(Config):

    def __init__(self):
        Config.__init__(self)
        self.tasks = []
        self.utl = Utils(label='Waiting for task to complete')

    def task_type(self):
        # purpose is to limit queue_depth to certain tasks
        # i.e. vmware tasks and ceph tasks to add more chaos
        pass

    def pop_task(self):
        """ Pop task with index 0.
        #UNUSED#
        """
        log.debug("Popping task")
        return self.tasks.pop(0) if self.tasks else None

    def cancel_all_tasks(self):
        for task in self.tasks:
            self.cancel_task(task)

    def cancel_task(self, task):
        task.CancelTask()

    @property
    def queue_free(self):
        if self.task_count < self.max_tasks:
            return True
        return False

    def push_task(self, task):
        self.clean_finished_tasks()
        log.info('{}Pushing task {} to queue{}'.format(Fore.GREEN, task, Style.RESET_ALL))
        log.debug("Tasks in queue: {}".format(self.task_count))
        if self.task_count < self.max_tasks:
            self.tasks.append(task)
        else:
            info = "(Running in {} mode)".format(self.mode)
            log.info(Fore.YELLOW + "Max queue depth reached {}".format(info))
            if self.mode == 'sync':
                self.wait_for_task(task)
            else:
                self.wait_for_any_finished_task()

    @property
    def task_count(self):
        return len(self.tasks)

    def wait_for_any_finished_task(self):
        while self.task_count >= self.max_tasks:
            self.utl.spinner()
            self.clean_finished_tasks(silent=True)

    def clean_finished_tasks(self, silent=False):
        # That could be run in background
        if not silent:
            log.info(Style.DIM + "Checking for finished tasks")
        for task in self.tasks:
            if task.info.state == 'success':
                self.tasks.remove(task)
                info = ""
                if self.task_count > self.max_tasks:
                    info = "{} to go".format(self.task_count - self.max_tasks)
                log.info("Task ended successfully - {} tasks still in queue. {}".format(self.task_count, info))
            if task.info.state == 'error':
                # What to do best in that case?
                # Sum them up and fail on a certain count?
                self.tasks.remove(task)
                log.info("\n")
                log.info(Fore.RED + "Encoutered an error in task {}".format(task))

    def wait_for_task(self, task):
        """ wait for a vCenter task to finish """
        task_done = False
        while not task_done:
            self.utl.spinner()
            time.sleep(0.2)
            
            if task.info.state == 'success':
                return task.info.result

            if task.info.state == 'error':
                log.info("\n")
                log.info(Fore.RED + "Encoutered an error in task {}".format(task))
                task_done = True
