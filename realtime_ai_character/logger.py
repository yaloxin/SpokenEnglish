import logging


formatter = "%(asctime)s - %(funcName)s - %(filename)s - %(levelname)s - %(message)s"

'''
日志记录器函数 get_logger(logger_name)，它接受一个参数 logger_name，用于指定日志记录器的名称。
该函数配置了一个日志记录器，设置了日志级别为 DEBUG，并将日志信息输出到控制台
'''
def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to debug
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    ch_format = logging.Formatter(formatter)
    console_handler.setFormatter(ch_format)

    logger.addHandler(console_handler)

    return logger
