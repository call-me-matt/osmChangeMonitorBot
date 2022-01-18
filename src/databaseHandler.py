#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import datetime

logging.basicConfig(format='[%(levelname)s] %(name)s: %(message)s',level=logging.DEBUG)
logger = logging.getLogger("database-handler")

def init():
    logger.info("initializing database")
    con = sqlite3.connect('registration.db')
    db = con.cursor()
    db.execute("CREATE TABLE IF NOT EXISTS users( \
                    user TINYTEXT PRIMARY KEY, \
                    chatid TINYTEXT, \
                    language TINYTEXT \
               )")
    con.commit()
    db.execute("CREATE TABLE IF NOT EXISTS osmStats( \
                user TINYTEXT PRIMARY KEY, \
                changes TINYTEXT, \
                changesets TINYTEXT \
           )")
    con.commit()
    db.execute("CREATE TABLE IF NOT EXISTS watchers( \
                telegramUser TINYTEXT, \
                osmUser TINYTEXT \
           )")
    con.commit()
    con.close()

def addUser(username, chatid, lang):
    logger.info("adding telegram user " + username + " to database")
    con = sqlite3.connect('registration.db')
    db = con.cursor()
    db.execute("INSERT OR IGNORE INTO users (user,chatid,language) VALUES (?,?,?)",([username,chatid,lang]))
    con.commit()
    con.close()
        
def removeUser(username):
    logger.info("removing telegram user " + username + " from database")
    con = sqlite3.connect('registration.db')
    db = con.cursor()
    db.execute("DELETE FROM users WHERE user=?",([username]))
    db.execute("DELETE FROM watchers WHERE telegramUser=?",([username]))
    db.execute("DELETE FROM osmStats WHERE user not in (SELECT DISTINCT osmUser from watchers)")
    con.commit()
    con.close()

def isUserRegistered(telegramUser):
    con = sqlite3.connect('registration.db')
    db = con.cursor()
    db.execute("SELECT chatid FROM users WHERE user=?",([telegramUser]))
    entries = db.fetchall()
    con.close()
    if entries == None or entries == []:
        return False
    return True

def addWatcher(telegramUser, osmUser):
    logger.info("adding follower " + telegramUser + " for " + osmUser + " to the database")
    con = sqlite3.connect('registration.db')
    db = con.cursor()
    #TODO: only if not existing
    db.execute("INSERT INTO watchers (telegramUser,osmUser) VALUES (?,?)",([telegramUser,osmUser]))
    con.commit()
    con.close()

def getWatcher(osmUser):
    con = sqlite3.connect('registration.db')
    db = con.cursor()
    db.execute("SELECT chatid,language FROM users WHERE user in (SELECT DISTINCT telegramUser FROM watchers WHERE osmUser=?)",([osmUser]))
    entries = db.fetchall()
    con.close()
    result = []
    for entry in entries:
        result.append(entry)
    return result

def removeWatcher(telegramUser, osmUser):
    logger.info("removing follower " + telegramUser + " for " + osmUser + " from the database")
    con = sqlite3.connect('registration.db')
    db = con.cursor()
    db.execute("DELETE FROM watchers WHERE telegramUser=? AND osmUser=?",([telegramUser,osmUser]))
    db.execute("DELETE FROM osmStats WHERE user not in (SELECT DISTINCT osmUser from watchers)")
    con.commit()
    con.close()

def getOsmUsers(telegramUser=None):
    con = sqlite3.connect('registration.db')
    con.row_factory = sqlite3.Row
    db = con.cursor()
    if telegramUser:
        db.execute("SELECT DISTINCT osmUser from watchers WHERE telegramUser=?",([telegramUser]))
    else:
        db.execute("SELECT DISTINCT osmUser from watchers")
    entries = db.fetchall()
    con.close()
    result = []
    for entry in entries:
        result.append(entry['osmUser'])
    logger.debug('Users: ' + str(result))
    return result
    
def getStats(watcher):
    logger.debug("getStats for " + str(watcher))
    con = sqlite3.connect('registration.db')
    con.row_factory = sqlite3.Row
    db = con.cursor()
    db.execute("SELECT user,changes,changesets FROM osmStats WHERE user in (SELECT osmUser from watchers WHERE telegramUser=?)",([watcher]))
    entries = db.fetchall()
    con.close()
    result = ""
    for (user,changes, changesets) in entries:
        result += user + ": " + str(changes) + " (" + str(changesets) + " sets) \n"
    return result

def updateStats(user, changes, changesets):
    logger.debug('updating stats for ' + user + ': ' + str(changes) + ' (' + str(changesets) + ' changesets)')
    con = sqlite3.connect('registration.db')
    con.row_factory = sqlite3.Row
    db = con.cursor()
    db.execute("SELECT changes FROM osmStats WHERE user=?",([user]))
    counterOld = db.fetchone()
    db.execute("INSERT INTO osmStats (user, changes, changesets) VALUES(?,?,?) ON CONFLICT(user) DO UPDATE SET (changes,changesets)=(?,?)",([user,changes,changesets,changes,changesets]))
    con.commit()
    con.close()
    if counterOld == None:
        return -1
    else:
        return counterOld[0]

def migrate(user, lang):
    #FIXME: this function stores the user language if registered before i18n was introduced.
    logger.debug('migrating ' + user + ': ' + str(lang))
    con = sqlite3.connect('registration.db')
    con.row_factory = sqlite3.Row
    db = con.cursor()
    db.execute("UPDATE users SET language=? WHERE USER=?",([lang, user]))
    con.commit()
    con.close()

