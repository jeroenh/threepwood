#!/usr/bin/env python

import Queue
import signal
from logging.handlers import TimedRotatingFileHandler
from threading import Thread
import libtorrent as lt
import time
from datetime import datetime, timedelta
import logging
import requests
import json
import ConfigParser
import sys

__author__ = 'cdumitru'

#number of tries for http requests before giving up
MAX_TRIES = 5
#lechuck will block on the result queue for QUEUE_TIMEOUT seconds
QUEUE_TIMEOUT = 10

#when true lechuck walks the plank
exit = False

def signal_handler(signal, frame):
    logging.getLogger('lechuck').critical("Interrupted! Stopping threads!")
    global exit
    exit = True


def request(type, url, data=None):
    """
    return json  decoded response
    """
    try_count = 0
    json_encoded_data = None
    logger = logging.getLogger("lechuck")
    response = {'success': False}

    if type == 'POST':
        json_encoded_data = DateTimeJSONEncoder().encode(data)

    while try_count < MAX_TRIES:
        try:
            if type == 'GET':
                response = requests.get(url)
            if type == 'POST':
                response = requests.post(url, data=json_encoded_data)

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


class Torrent(Thread):
    def __init__(self, libtorrent_session, torrent,settings, queue):
        Thread.__init__(self)
        self.libtorrent_session = libtorrent_session
        self.session_key = torrent['session_key']
        self.magnet = torrent['magnet']
        self.info_hash = torrent['info_hash']
        self.settings = settings
        self.logger = logging.getLogger("lechuck")
        self.peers = {}
        self.new_peers = []
        self.new_session = True
        self.queue = queue

    def send_peers(self, peers):
        to_send = {'peers': peers, 'metadata': self.metadata}
        self.queue.put((self.info_hash, to_send))

    def add_torrent(self):
        self.logger.debug("Adding torrent hash {0}".format(self.info_hash))
        info = lt.torrent_info(lt.big_number(self.info_hash.decode('hex')))
        # Add OpenBitTorrent trackers
        info.add_tracker('udp://tracker.openbittorrent.com:80', 0)
        info.add_tracker('udp://tracker.publicbt.com:80', 0)
        info.add_tracker('udp://tracker.ccc.de:80', 0)
        info.add_tracker('udp://tracker.istole.it:80', 0)
        self.logger.info("Adding hash {0} to session".format(self.info_hash))
        #        self.handle = self.libtorrent_session.add_torrent(info, './')
        self.handle = lt.add_magnet_uri(self.libtorrent_session, str(self.magnet),
            {'save_path': '/tmp',
             'storage_mode': lt.storage_mode_t.storage_mode_sparse,
             'paused':True
            })

        #wait for the download to start
        while not self.handle.status().state == self.handle.status().downloading:
            time.sleep(1)
        self.logger.debug("{0} changed state to  downloading".format(self.info_hash))


        #set all file prio to 0

        self.handle.prioritize_files([0 for i in self.handle.file_priorities()])

        #        for i in range(0, self.handle.get_torrent_info().num_pieces()):
        #            self.handle.piece_priority(i, 0)

        self.logger.debug("Done setting priority 0 for hash {0}".format(self.info_hash))

    def get_metadata(self):
        if self.handle.has_metadata():
            i = self.handle.get_torrent_info()
            files = []

            for f in i.files():
                files.append((f.path, f.size))
            self.metadata = {
                'name': i.name(),
                'size': i.total_size(),
                'files': files,
                'creator': i.creator(),
                'comment': i.comment()
            }

        self.logger.debug("Got metadata for hash {0}:{1}".format(self.info_hash, self.metadata['name']))

    def wait_and_report_peers(self):
        last_report = datetime.now()

        while self.active:
            if self.handle.is_valid() and self.handle.has_metadata():
                for peer in self.handle.get_peer_info():
                    if not self.peers.has_key(peer.ip[0]):
                        self.peers[peer.ip[0]] = peer.ip[0]
                        self.new_peers.append(peer.ip[0])
            else:
                self.logger.critical("Handle is not valid {0}".format(self.info_hash))
                self.active = False
                return

            if (datetime.now() - last_report > timedelta(seconds=self.settings['REPORT_INTERVAL']) or\
                len(self.new_peers) > self.settings['MAX_PEERS_THRESHOLD']) and len(self.new_peers) > 0:
                self.logger.debug("{0}: reporting {1} new peers".format(self.metadata['name'], len(self.new_peers)))
                last_report = datetime.now()
                self.send_peers(self.new_peers)
                self.new_peers = []
            time.sleep(5)

            #            self.logger.debug("{0}: total peers {1}".format(self.metadata['name'], len(self.peers.keys())))

    def cleanup(self):
        self.logger.debug("Removing torrent {0}".format(self.name))
        self.libtorrent_session.remove_torrent(self.handle)
        time.sleep(5)

    def run(self):
        self.logger.debug("Started thread for hash {0}".format(self.info_hash))

        while self.new_session:
            self.new_session = False
            self.peers.clear()
            self.active = True
            self.add_torrent()
            self.get_metadata()
            self.wait_and_report_peers()
            self.cleanup()


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



    logger = logging.getLogger("lechuck")
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




def get_libtorrent_session(config):
    logger = logging.getLogger("lechuck")
    logger.debug("Creating libtorrent session")
    session = lt.session()
    session.listen_on(6881, 6891)
    session.add_extension(lt.create_ut_metadata_plugin)
    session.add_extension(lt.create_ut_pex_plugin)
    logger.debug("Adding initial DHT routers")
    session.add_dht_router('dht.transmissionbt.com', 6881)
    session.add_dht_router('router.utorrent.com', 6881)
    session.add_dht_router('router.bittorrent.com', 6881)
    session.start_dht()
    session.set_download_rate_limit(int(config.get('global', 'download_rate')))
    session.set_upload_rate_limit(int(config.get('global', 'upload_rate')))

    return session


def main():
    global exit
    #TODO support command line options
    config_file = "lechuck.conf"

    try:
        config = ConfigParser.ConfigParser({'upload_rate': '32768', 'download_rate': '32768'})

        config.read(config_file)
    except:
        print "Error reading config file {0}. Exiting".format(config_file)
        sys.exit(0)

    settings= {
        'MAX_PEERS_THRESHOLD': 20,
        'REPORT_INTERVAL': 60,
        'CHECK_FOR_UPDATES_INTERVAL': 60
    }



    queue = Queue.Queue()
    session = get_libtorrent_session(config)

    signal.signal(signal.SIGINT, signal_handler)


    logger = init_logger(config)

    get_url = config.get('global', 'THREEPWOOD_GET_URL') + "?key="+ config.get('global', 'KEY') + "&version=libtorrent-"+lt.version
    post_url = config.get('global', 'THREEPWOOD_POST_URL')

    torrent_list = []

    last_heartbeat = datetime.now()
    response = request('GET', get_url)

    if response['success']:
        torrent_list = response['torrents']

    torrent_threads = {}
    if response.has_key('settings'):
        settings = response['settings']
    for torrent in torrent_list:
        info_hash = torrent['info_hash']
        torrent_threads[info_hash] = Torrent(session, torrent,settings, queue)
        torrent_threads[info_hash].daemon = True
        torrent_threads[info_hash].start()

    while not exit:
        result = None
        logger.debug("Total threads {0}".format(len(torrent_threads.keys())))
        try:
            result = queue.get(timeout=QUEUE_TIMEOUT)
        except Queue.Empty:
            pass
            #check for dead threads TODO
#            for key in torrent_threads.keys():
#                if not torrent_threads[key].active:
#                    logger.warning("Thread {0} is dead. Reaping! ".format(torrent_threads[key]))
#                    old_thread = torrent_threads[torrent]
##                    settings = torrent_threads[torrent]
#                    torrent_threads[torrent] = Torrent(session, torrent, queue)
#                    old_thread.join()

        if result:
            #if we got something from the queue  send it to threepwood
            info_hash, to_send = result
            #get the current session_key as the response might have lingered a bit in the queue
            #this *should* avoid any snowballs
            to_send['session_key'] = torrent_threads[info_hash].session_key
            logger.debug("Reporting {0} peers from {1}".format(len(to_send['peers']), to_send['metadata']['name']))

            response = request('POST', post_url, data=to_send)

            #only perform actions if the message is well formed
            if response['success']:
                if not response['client_active']:
                    logger.info("Client disabled. Exiting")
                    exit = True

                if not response['session_active'] and not exit:
                    logger.info("Torrent {0}:{1} disabled. Removing thread".format(info_hash,
                        torrent_threads[info_hash].metadata['name']))
                    torrent_threads[info_hash].active = False
                    torrent_threads[info_hash].join()
                    del torrent_threads[info_hash]
                print response['session_key']
                print to_send['session_key']
                if response['session_key'] != to_send['session_key'] and not exit:
                    logger.info("Got new session from threepwood.")
                    #ingnore previously disabled torrents
                    if torrent_threads[info_hash].active:
                        torrent_threads[info_hash].active = False
                        torrent_threads[info_hash].new_session = True
                        torrent_threads[info_hash].session_key = response['session_key']
                #sleep a bit not to overwhelm the server
                time.sleep(1)

        #TODO print session status

        #get fresh info
        if  datetime.now() - last_heartbeat > timedelta(
            seconds=settings['CHECK_FOR_UPDATES_INTERVAL']) and not exit:
            logger.debug("Getting fresh info from threepwood")
            response = request('GET', get_url)

            if response.has_key('settings'):
                settings = response['settings']

            last_heartbeat = datetime.now()


            #add new torrents

            if response['success']:
                #the response is a list of dicts each having keyes info_hash and session
                torrent_list = response['torrents']
                #select only those torrent ids that are not already under the control of lechuck
                torrents_to_add = [t for t in torrent_list if not t['info_hash'] in torrent_threads.keys()]

                #select torrent hashes managed by lechuck thare are not in the fresh list
                torrents_to_remove = [t for t in torrent_threads.keys() if
                                      t not in [h['info_hash'] for h in torrent_list]]

                logger.debug("Will add: {0} Will remove:{1} ".format(len(torrents_to_add), len(torrents_to_remove)))

                for t in torrents_to_add:
                    info_hash = t['info_hash']
                    logger.info("Adding torrent {0}".format(info_hash))
                    torrent_threads[info_hash] = Torrent(session, t,settings, queue)
                    torrent_threads[info_hash].daemon = True
                    torrent_threads[info_hash].start()
                for info_hash in torrents_to_remove:
                    torrent_threads[info_hash].active = False
                for info_hash in torrents_to_remove:
                    torrent_threads[info_hash].join()


            #TODO handle session rollover in GET

    #cleanup before exit
    for info_hash in torrent_threads.keys():
        torrent_threads[info_hash].active = False
    for info_hash in torrent_threads.keys():
        torrent_threads[info_hash].join()
    del session


    logger.info("Bye")

if __name__ == "__main__":
    main()