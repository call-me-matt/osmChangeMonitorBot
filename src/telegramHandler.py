#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import threading
import time
import logging
import requests
import gettext
from datetime import datetime, time
from xml.etree import ElementTree

import databaseHandler

from telegram.ext import CallbackContext

from telegram.ext import Updater
from telegram.ext import CommandHandler, ConversationHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import JobQueue

TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
WATCHDOG_INTERVAL_MIN = 4*60

STATE_FOLLOWS, STATE_UNFOLLOWS = range(2)

REQUEST_HEADERS = {
    'User-Agent': 'osmChangesetBot https://t.me/osmChangesetBot',
    'From': 'https://github.com/call-me-matt/osmChangeMonitorBot'
}

# i18n
def get_translator(lang: str = "en"):
    trans = gettext.translation('osm-telegram-bot', localedir='./locales', languages=(lang,), fallback=True)
    return trans.gettext


logging.basicConfig(format='[%(levelname)s] %(name)s: %(message)s',level=logging.DEBUG)
logger = logging.getLogger("telegram-handler")

class telegramHandler (threading.Thread):

    def register(self, update, context):
        _ = get_translator(update.message.from_user.language_code)
        context.bot.send_message(chat_id=update.message.chat_id, text=(_("Hello, %s. I can request the number of changes for OSM users. Just send me a message saying /report. Add OSM users by writing a /follow message, or remove them with /unfollow") % (update.message.from_user.first_name)))
        databaseHandler.addUser(update.message.from_user.name, update.message.chat_id, update.message.from_user.language_code)

    def stop(self, update, context):
        _ = get_translator(update.message.from_user.language_code)
        context.bot.send_message(chat_id=update.message.chat_id, text=_("Stopping. To reactivate, just send me a /start"))
        databaseHandler.removeUser(update.message.from_user.name)

    def check_input(self, userInput):
        # check its a valid OSM User
        request = requests.get('https://www.openstreetmap.org/api/0.6/changesets?display_name=' + userInput, headers=REQUEST_HEADERS)
        if request.status_code != 200:
            logger.warning(userInput + ' seems not a valid OSM user')
            return False
        # everything seems fine
        return True

    def follow(self, update, context):
        _ = get_translator(update.message.from_user.language_code)
        update.message.reply_text(_('OK, you want to add a follower. Please tell me now the OSM user name:'))
        return STATE_FOLLOWS
    
    def followUser(self, update, context):
        _ = get_translator(update.message.from_user.language_code)
        if (self.check_input(update.message.text)):
            if not databaseHandler.isUserRegistered(update.message.from_user.name):
                databaseHandler.addUser(update.message.from_user.name,update.message.chat_id, update.message.from_user.language_code)
            context.bot.send_message(chat_id=update.message.chat_id, text=(_("Allright. I will add %s to the list.") % (update.message.text)))
            databaseHandler.addWatcher(update.message.from_user.name, str(update.message.text))
            self.report(update, context)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=_("Sorry, I could not find this OSM user. Please note that capitalization is important."))
        return ConversationHandler.END
        
    def unfollow(self, update, context):
        _ = get_translator(update.message.from_user.language_code)
        update.message.reply_text(_('OK, you want to remove a follower. Please tell me now the OSM user name:'))
        return STATE_UNFOLLOWS

    def unfollowUser(self, update, context):
        _ = get_translator(update.message.from_user.language_code)
        if update.message.text in databaseHandler.getOsmUsers(update.message.from_user.name):
            context.bot.send_message(chat_id=update.message.chat_id, text=(_("Allright. I will remove %s from the list.") % (update.message.text)))
            databaseHandler.removeWatcher(update.message.from_user.name, str(update.message.text))
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=(_("Sorry, this seems not to be a Username from your list.")))
        return ConversationHandler.END

    def cancel(self, update, context):
        """Cancels and ends the conversation."""
        _ = get_translator(update.message.from_user.language_code)
        user = update.message.from_user
        logger.info("User " + user.first_name + " canceled the conversation.")
        update.message.reply_text(
            _('Bye!'), reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    def report(self, update, context):
        _ = get_translator(update.message.from_user.language_code)
        context.bot.send_message(chat_id=update.message.chat_id, text=_("Hold on, I am retrieving latest numbers..."))
        osmUsers = databaseHandler.getOsmUsers(update.message.from_user.name)
        self.getOsmChanges(context, osmUsers)
        stats = databaseHandler.getStats(update.message.from_user.name)
        if stats == "":
            stats = _("You need to follow OSM users by writing a /follow message first.")
        context.bot.send_message(chat_id=update.message.chat_id, text=str(stats))

    def echo(self, update, context):
        _ = get_translator(update.message.from_user.language_code)
        if not databaseHandler.isUserRegistered(update.message.from_user.name):
            logger.warning('unknown user')
            self.register(update, context)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=_("🤓🙄 Please don't disturb me. I am observing OSM stats."))

    def feedback(self, update, context):
        _ = get_translator(update.message.from_user.language_code)
        context.bot.send_message(chat_id=update.message.chat_id, text=_("For questions or feedback you can contact @KeinplanMAJORAN ."))

    def queryOsmApi(self, user, startdate=""):
        count = {'changesets':0, 'changes':0}
        time = datetime.today().strftime("%Y-%m-01T00:00")
        if startdate != "":
            time = time + "," + startdate
        osmApiCall = "https://www.openstreetmap.org/api/0.6/changesets?time=" + time + "&closed=true&display_name="
        response = requests.get(osmApiCall + user, headers=REQUEST_HEADERS)
        result = ElementTree.fromstring(response.content)
        for changeset in result:
            count['changesets'] += 1
            count['changes'] += int(changeset.attrib['changes_count'])
        if count['changesets'] and count['changesets'] % 100 == 0:
            count2 = self.queryOsmApi(user, startdate=changeset.attrib['created_at'])
            count['changesets'] += count2['changesets']
            count['changes'] += count2['changes']
        return count

    def getOsmChanges(self, context: CallbackContext, osmUsers=databaseHandler.getOsmUsers()):
        for user in osmUsers:
            logger.debug("updating stats for " + user)
            count = {'changesets':0, 'changes':0}
            countBefore = 0
            try:
                count = self.queryOsmApi(user)
                countBefore = databaseHandler.updateStats(user,str(count['changes']),str(count['changesets']))
            except:
                logger.warning ("could not retrieve stats for: " + user)
            alertChanges = [100000,10000,5000,1000,300]
            for number in alertChanges:
                if int(countBefore) > 0 and int(countBefore) < number and count['changes'] >= number:
                    self.sendAlert(context, user, number)
                    break

    def sendAlert(self, context, user, number):
        logger.info(("%s has achieved more than %s changes!") % (user, str(number)))
        chatIds = databaseHandler.getWatcher(user)
        for chatId,lang in chatIds:
            _ = get_translator(lang)
            alert = (_("🥳 %s has achieved more than %s changes!") % (user, str(number)))
            context.bot.send_message(chat_id=chatId, text=alert)

    def __init__(self):
        global TOKEN
        global WATCHDOG_INTERVAL_MIN

        logger.info('starting telegram-handler')
        threading.Thread.__init__(self)

        logger.debug("initializing telegram bot")
        self.updater = Updater(token=TOKEN, use_context=True)
        self.dispatcher = self.updater.dispatcher

        logger.debug("initializing registration database")
        databaseHandler.init()

        logger.debug('creating stats-watchdog')
        watchdog = self.updater.job_queue.run_repeating(self.getOsmChanges, interval=WATCHDOG_INTERVAL_MIN*60, first=30)
        #watchdog = self.updater.job_queue.run_daily(self.getOsmChanges, time(hour=12, minute=00))

    def run(self):
        start_handler = CommandHandler('start', self.register)
        self.dispatcher.add_handler(start_handler)

        stop_handler = CommandHandler('stop', self.stop)
        self.dispatcher.add_handler(stop_handler)

        follow_handler = ConversationHandler(
            entry_points=[CommandHandler('follow',self.follow)],
            states={
                STATE_FOLLOWS: [MessageHandler(Filters.text & ~Filters.command, self.followUser)]
            },
            fallbacks=[CommandHandler('cancel',self.cancel)],
        )
        self.dispatcher.add_handler(follow_handler)
 
        unfollow_handler = ConversationHandler(
            entry_points=[CommandHandler('unfollow',self.unfollow)],
            states={
                STATE_UNFOLLOWS: [MessageHandler(Filters.text & ~Filters.command, self.unfollowUser)]
            },
            fallbacks=[CommandHandler('cancel',self.cancel)],
        )
        self.dispatcher.add_handler(unfollow_handler)
        
        unfollow_handler = CommandHandler('unfollow', self.unfollow, pass_args=True)
        self.dispatcher.add_handler(unfollow_handler)

        report_handler = CommandHandler('report', self.report, pass_args=True)
        self.dispatcher.add_handler(report_handler)

        echo_handler = MessageHandler(Filters.text, self.echo)
        self.dispatcher.add_handler(echo_handler)

        unknown_handler = MessageHandler(Filters.command, self.feedback)
        self.dispatcher.add_handler(unknown_handler)

        self.updater.start_polling()
        #TODO: replace polling by webhook:
        #self.updater.start_webhook(listen='127.0.0.1', port=88, url_path='', cert=None, key=None, clean=False, bootstrap_retries=0, webhook_url=None, allowed_updates=None)

