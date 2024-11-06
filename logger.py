import logging
import logging.config
from multiprocessing import SimpleQueue
import sys
from threading import Thread
import yaml


def dynamic_import(module_name: str, class_name: str):
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


def import_if_not_exists(module_name: str, class_name: str):
    if module_name not in sys.modules:
        return dynamic_import(module_name, class_name)
    return getattr(sys.modules[module_name], class_name)


class LogManager:
    def __init__(self,
                 configPath: str = 'logger.yaml',
                 loggerName: str = None,
                 logQueue: SimpleQueue = None,
                 logFilePath: str = None,) -> None:
        self.thread = None
        self.configPath = configPath
        self.loggerName = loggerName
        self.logQueue = logQueue
        self.logFilePath = logFilePath
        self.loadConfig()
        if self.logFilePath:
            self.addMultiProcessingFileHandler(self.logFilePath)

    def loadConfig(self) -> None:
        with open(self.configPath, 'r') as f:
            config = yaml.safe_load(f.read())
            logging.config.dictConfig(config)

    def getLogger(self, name=None) -> logging.Logger:
        return logging.getLogger(name if name else self.loggerName)

    def startLogListener(self) -> None:
        if not self.logQueue:
            raise ValueError("logQueue가 설정되지 않았습니다.")
        self.thread = Thread(target=self.processLogQueue, daemon=True)
        self.thread.start()

    def stopLogListener(self) -> None:
        if self.logQueue:
            self.logQueue.put(None)
        self.thread.join()
        print('로그 리스너 종료...')

    def processLogQueue(self) -> None:
        logger = self.getLogger()
        while True:
            try:
                record = self.logQueue.get()
                if record is None:
                    break
                logger.handle(record)
            except Exception:
                import sys
                import traceback
                print('리스너 문제 발생', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    def configureQueueHandler(self, logQueue: SimpleQueue = None) -> logging.Logger:
        if logQueue is None and self.logQueue is None:
            raise ValueError("logQueue가 설정되지 않았습니다.")
        elif self.logQueue is None:
            self.logQueue = logQueue
        queueHandler = logging.handlers.QueueHandler(self.logQueue)
        logger = logging.getLogger(self.loggerName)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(queueHandler)
        return logger

    def addMultiProcessingFileHandler(self, filePath: str = 'path_to_log_file.log') -> None:
        MultiProcessingFileHandler = import_if_not_exists('mpfhandler', 'MultiProcessingFileHandler')
        logger = self.getLogger()
        mpf_handler = MultiProcessingFileHandler(filePath)
        logger.addHandler(mpf_handler)
