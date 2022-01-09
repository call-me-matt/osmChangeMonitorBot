#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import sys
import time
import threading

import telegramHandler

logging.basicConfig(format='[%(levelname)s] %(name)s: %(message)s',level=logging.INFO)
logger = logging.getLogger("main")

logger.info('starting osmChangesetsBot')

logger.debug('creating telegram-handler thread')
telegramThread = telegramHandler.telegramHandler()
telegramThread.daemon = True
telegramThread.start()

while True:
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        logger.info('Exiting...')
        sys.exit()
    except:
        raise

