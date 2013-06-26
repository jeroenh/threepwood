#!/usr/bin/env python
__author__ = 'jeroenh'

import json
import logging
from logging.handlers import TimedRotatingFileHandler
import requests
import ConfigParser
import sys
import os.path
from collections import defaultdict
import time
from datetime import datetime, timedelta

#number of tries for http requests before giving up
MAX_TRIES = 5
#lechuck will block on the result queue for QUEUE_TIMEOUT seconds
QUEUE_TIMEOUT = 10

def init_logger(config):
    """
        Initializes and returns a logger object
    """
    LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL}

    logfile = config.get('global', 'LOG_FILE')
    loglevel_console = config.get('global', 'LOG_LEVEL_CONSOLE')
    loglevel_file = config.get('global', 'LOG_LEVEL_FILE')

    logger = logging.getLogger("murray")
    logger.setLevel(logging.DEBUG)
    fh = TimedRotatingFileHandler(logfile, when='D', interval=1,
        backupCount=5)
    fh.setLevel(LEVELS[loglevel_file])
    ch = logging.StreamHandler()
    ch.setLevel(LEVELS[loglevel_console])
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - " +
                                  "%(message)s")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

def request(type, url, data=None):
    """
    return json  decoded response
    """
    try_count = 0
    json_encoded_data = None
    logger = logging.getLogger("murray")
    response = {'success': False}

    if type == 'POST':
        json_encoded_data = DateTimeJSONEncoder().encode(data)

    while try_count < MAX_TRIES:
        try:
            if type == 'GET':
                response = requests.get(url,verify=False)
            if type == 'POST':
                response = requests.post(url, data=json_encoded_data,verify=False)

            if response.status_code != 200:
                logger.critical("Threepwood server error. Status code:{0}".format(response.status_code))
                raise Exception('status code')
            if not response.json()['success']:
                logger.critical("Threepwood service error: {0}".format(str(response.json()['message'])))
                raise Exception('failed')

            return response.json()

        except Exception as e:
            try_count += 1
            logger.critical("Unable to connect: {0}. {1} tries left".format(e, MAX_TRIES - try_count))
            time.sleep(1)
            response = {'success': False}

    return response

class DateTimeJSONEncoder(json.JSONEncoder):
    """
    Extends the default json encoder to support date time serializing
    Verbatim paste from
    http://stackoverflow.com/questions/455580/json-datetime-between-python-and-javascript
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return super(DateTimeJSONEncoder, self).default(obj)
            
           


def sendStuff(peers,metadata,session_key):
    # to_send['session_key'] = torrent_threads[info_hash].session_key
    metadata = {
        'name': i.name(),
        'size': i.total_size(),
        'files': files,
        'creator': i.creator(),
        'comment': i.comment()
    }
    to_send = {'peers': peers, 'metadata': self.metadata, 'session_key': session_key}
    logger.debug("Reporting {0} peers from {1}".format(len(to_send['peers']), to_send['metadata']['name']))
    post_url = config.get('global', 'THREEPWOOD_POST_URL')
    response = request('POST', post_url, data=to_send)
    
def main():
    global exit
    #TODO support command line options
    config_file = "murray.conf"

    try:
        config = ConfigParser.ConfigParser()
        config.read(config_file)
    except:
        print "Error reading config file {0}. Exiting".format(config_file)
        sys.exit(0)

    settings= {
        'MAX_PEERS_THRESHOLD': 20,
        'REPORT_INTERVAL': 60,
        'CHECK_FOR_UPDATES_INTERVAL': 60
    }
    get_url = config.get('global', 'THREEPWOOD_GET_URL') + "?key="+ config.get('global', 'KEY')
    post_url = config.get('global', 'THREEPWOOD_POST_URL')
    print get_url
    logger = init_logger(config)
    # registerTorrents()
    submitTorrents(get_url=get_url)

def getTorrentName(logname):
    if logname.endswith(".os3.ip.log"):
        return logname[:-11]
    elif logname.endswith("-jer.ip.log"):
        return logname[:-11]
    elif logname.endswith("-nl-full.ip.log"):
        return logname[:-15]
    elif logname.endswith("-jer-nl.ip.log"):
        return logname[:-14]
    elif logname.endswith("-nl-full2.ip.log"):
        return logname[:-16]
    elif logname.endswith(".ip.log"):
        return logname[:-7]
    else:
        raise Exception("Unknown name %s" % (logname))

def submitTorrent(torrents,dirname,fnames):
    logger = logging.getLogger("murray")
    root="/Users/jeroen/Projects/torrent/results"
    fnames = filter(lambda x:not(x.startswith("proc")) and x.endswith(".log"),fnames)
    for fname in fnames:
        torrentname = getTorrentName(fname)
        peers = list(set(open(os.path.join(root,dirname,fname)).read().splitlines()))
        for t in torrents:
            if t["magnet"] == torrentname:
                to_send = {'peers': peers, 'session_key': t["session_key"]}
                logger.debug("Reporting {0} peers on {1}".format(len(to_send['peers']),torrentname))
                post_url = "https://apricot.studlab.os3.nl:444/collector/post_peers/"
                # post_url = config.get('global', 'THREEPWOOD_POST_URL')
                response = request('POST', post_url, data=to_send)
                break
        
def submitTorrents(root="/Users/jeroen/Projects/torrent/results",get_url=None):
    response = request('GET', get_url)
    if response['success']:
        torrent_list = response['torrents']
    os.path.walk(root,submitTorrent,torrent_list)
        
# Below was used for registering all torrents
def processLogDir(torrents,dirname,fnames):
    fnames = filter(lambda x:not(x.startswith("proc")) and x.endswith(".log"),fnames)
    for fname in fnames:
        torrentname = getTorrentName(fname)
        torrents[torrentname].append(dirname)

def registerTorrents(root="/Users/jeroen/Projects/torrent/results"):
    torrents = defaultdict(list)
    os.path.walk(root,processLogDir,torrents)
    x = 0
    for name in torrents:
        x += 1
        data = {"torrent": name, "hash":x}
        res = request('POST',"https://apricot.studlab.os3.nl:444/collector/post_torrents/",data)
        print "Registered %s as %s" % (name,res["hash"])

    
if __name__ == "__main__":
    main()
    
# TODO: Register old torrents
# TODO: Parse old torrent files and match with old torrents (use comment?)
