import logging

# create logger
logger = logging.getLogger('coolqbot')
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create file handler and set level to info
fh = logging.FileHandler('coolqbot.log')
fh.setLevel(logging.WARNING)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(lineno)s - %(levelname)s - %(message)s')

# add formatter to handler
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)
logger.addHandler(fh)
