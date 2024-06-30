import logging
import os

# Status of test result for querying.
TEST_RESULTS = {"SUCCESS", "FAILURE", "RETRY_LIMIT", "POST_FAILURE"}

LOGDIR = "logs"

def logger(logfile):
    os.makedirs(LOGDIR, exist_ok=True)
    logfile = "{}/{}.log".format(LOGDIR, logfile)
    logging.basicConfig(filename=logfile, level=logging.DEBUG)
    return logging
