import logging
import logging.config
import sys
import paramiko
from config import Config

log = logging.getLogger(__name__)

class SshUtil():

    def __init__(self, node, user, pw, reboot_allowed=False):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.node = node
        self.client.connect(node,
                            username=user,
                            password=pw)
        self.reboot_allowed = reboot_allowed

    def run_cmd(self, cmd):
        log.debug("Running cmd({})".format(cmd))
        _, stdout, stderr = self.client.exec_command(cmd)
        return stdout.read().decode().strip(), stderr.read().decode().strip()

    def reboot(self):
        if self.reboot_allowed:
            log.info("Triggering a reboot on {}".format(self.node))
            self.client.exec_command('reboot')
        else:
            log.info("Can't stage reboot with one gateway. This would cause a stall in all I/O and wouldn't test the inteded failover. If you still want to do that. You can set the force_reboot option to True")
        

class Utils(object):

    def __init__(self, **kwargs):
        self.label = kwargs.get('label')
        self.spinner_gen = self._create_char_spinner()

    @staticmethod
    def _create_char_spinner():
        """Creates a generator yielding a char based spinner.
        """
        log.debug("Creating _create_char_spinner generator")
        while True:
            for c in '|/-\\':
                yield c

    def spinner(self):
        """log.infos label with a spinner.
        When called repeatedly from inside a loop this prints
        a one line CLI spinner.
        """
        sys.stdout.write("\r%s %s" % (self.label, next(self.spinner_gen)))
        sys.stdout.flush()


def _setup_logging():
    """
    Logging configuration
    """
    # change that to external import file
    cfg = Config()
    if cfg.LOG_LEVEL == "silent":
        return


    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'brief': {
                'format': '%(message)s'
            },
        },
        'handlers': {
            'file': {
                'level': cfg.LOG_LEVEL_FILE.upper(),
                'filename': cfg.LOG_FILE_PATH,
                'class': 'logging.FileHandler',
                'formatter': 'standard'
            },
            'console': {
                'level': cfg.LOG_LEVEL_CONSOLE.upper(),
                'formatter': 'brief',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout'
            },
        },
        'loggers': {
            'main': {
                'handlers': ['file', 'console'],
                'level': cfg.LOG_LEVEL.upper(),
                'propagate': True,
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['file', 'console']
        }
    })
    logging.getLogger("paramiko").setLevel(logging.WARNING)

