#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib import kodi_db
from threading import Lock

from .. import db, variables as v

PLEXDB_LOCK = Lock()

SUPPORTED_KODI_TYPES = (
    v.KODI_TYPE_MOVIE,
    v.KODI_TYPE_SHOW,
    v.KODI_TYPE_SEASON,
    v.KODI_TYPE_EPISODE,
    v.KODI_TYPE_ARTIST,
    v.KODI_TYPE_ALBUM,
    v.KODI_TYPE_SONG
)


class PlexDBBase(object):
    """
    Plex database methods used for all types of items.
    """
    def __init__(self, plexconn=None, lock=False, copy=False):
        # Allows us to use this class with a cursor instead of context mgr
        self.plexconn = plexconn        
        self.lock = lock
        self.copy = copy

    def __enter__(self):
        if self.lock:
            PLEXDB_LOCK.acquire()
        ##if self.plexconn.dbtype == "mysql":
        ##    self.plexconn = db.connect('plex' if self.copy else 'plex')
        ##else:
        self.plexconn = db.connect('plex-copy' if self.copy else 'plex')
                
        return self

    def __exit__(self, e_typ, e_val, trcbak):
        try:
            if e_typ:
                # re-raise any exception
                return False
            self.plexconn.commit()
        finally:
            self.plexconn.disconnect()
            if self.lock:
                PLEXDB_LOCK.release()

    def is_recorded(self, plex_id, plex_type):
        """
        FAST method to check whether a plex_id has already been recorded
        """
        data = self.plexconn.select(plex_type, ("plex_id", ),"WHERE plex_id = %s" % (plex_id,))
        return len(data)>0

    def item_by_id(self, plex_id, plex_type=None):
        """
        Returns the item for plex_id or None.
        Supply with the correct plex_type to speed up lookup
        """
        answ = None
        if plex_type == v.PLEX_TYPE_MOVIE:
            answ = self.movie(plex_id)
        elif plex_type == v.PLEX_TYPE_EPISODE:
            answ = self.episode(plex_id)
        elif plex_type == v.PLEX_TYPE_SHOW:
            answ = self.show(plex_id)
        elif plex_type == v.PLEX_TYPE_SEASON:
            answ = self.season(plex_id)
        elif plex_type == v.PLEX_TYPE_SONG:
            answ = self.song(plex_id)
        elif plex_type == v.PLEX_TYPE_ALBUM:
            answ = self.album(plex_id)
        elif plex_type == v.PLEX_TYPE_ARTIST:
            answ = self.artist(plex_id)
        elif plex_type in (v.PLEX_TYPE_CLIP, v.PLEX_TYPE_PHOTO, v.PLEX_TYPE_PLAYLIST):
            # Will never be synched to Kodi
            pass
        elif plex_type is None:
            # SLOW - lookup plex_id in all our tables
            for kind in (v.PLEX_TYPE_MOVIE,
                         v.PLEX_TYPE_EPISODE,
                         v.PLEX_TYPE_SHOW,
                         v.PLEX_TYPE_SEASON,
                         'song',  # darn
                         v.PLEX_TYPE_ALBUM,
                         v.PLEX_TYPE_ARTIST):
                method = getattr(self, kind)
                answ = method(plex_id)
                if answ:
                    break
        return answ

    def item_by_kodi_id(self, kodi_id, kodi_type):
        """
        """
        if kodi_type not in SUPPORTED_KODI_TYPES:
            return
        data = self.plexconn.select(v.PLEX_TYPE_FROM_KODI_TYPE[kodi_type], ("*",), 
          "WHERE kodi_id = %s LIMIT 1" % (kodi_id, )
        )
        
        method = getattr(self, 'entry_to_%s' % v.PLEX_TYPE_FROM_KODI_TYPE[kodi_type])        
        return method(data)

    def plex_id_by_last_sync(self, plex_type, last_sync, limit):
        """
        Returns an iterator for all items where the last_sync is NOT identical
        """
        data = self.plexconn.select(plex_type, ("plex_id",), "WHERE last_sync <> %s LIMIT %s"
          % (last_sync, limit))
        return (x[0] for x in data)

    def checksum(self, plex_id, plex_type):
        """
        Returns the checksum for plex_id
        """
        data = self.plexconn.select(plex_type, ("checksum",), "WHERE plex_id = %s LIMIT 1" % (plex_id, ))
        try:
            return data[0][0]
        except :
            pass

    def update_last_sync(self, plex_id, plex_type, last_sync):
        """
        Sets a new timestamp for plex_id
        """
        self.plexconn.update(plex_type,
          ("last_sync", ),
          (last_sync,),
          "WHERE plex_id = %s" % (plex_id,)
          )

    def remove(self, plex_id, plex_type):
        """
        Removes the item from our Plex db
        """
        self.plexconn.delete(plex_type, "WHERE plex_id = %s" % (plex_id, ))        

    def every_plex_id(self, plex_type, offset, limit):
        """
        Returns an iterator for plex_type for every single plex_id
        Will start with records at DB position offset [int] and return limit
        [int] number of items
        """
        data = self.plexconn.select(plex_type, ("plex_id",), 'LIMIT '+str(limit)+' OFFSET ' + str(offset))
        return (x[0] for x in data)

    def missing_fanart(self, plex_type, offset, limit):
        """
        Returns an iterator for plex_type for all plex_id, where fanart_synced
        has not yet been set to 1
        Will start with records at DB position offset [int] and return limit
        [int] number of items
        """
        data = self.plexconn.select(plex_type, ("plex_id",),
          "WHERE fanart_synced=0 AND LIMIT %s OFFSET %s" % (limit, offset)
        )
        return (x[0] for x in data)

    def set_fanart_synced(self, plex_id, plex_type):
        """
        Toggles fanart_synced to 1 for plex_id
        """
        self.plexconn.update(plex_type, ("fanart_synced",), (1,), "WHERE plex_id=%s" % (plex_id,))

    def plexid_by_sectionid(self, section_id, plex_type, limit):
        data = self.plexconn.select("plex_type", ("plex_id", ), "WHERE section_id=%s LIMIT %s"
            % (section_id, limit))
        return (x[0] for x in data)

    def kodiid_by_sectionid(self, section_id, plex_type):
        data = self.plexconn.select(plex_type, ("kodi_id",), "WHERE section_id=%s" % (section_id))
        return (x[0] for x in data)                


def initialize():
        """
        Run once upon PKC startup to verify that plex db exists.
        """
        with PlexDBBase() as plexdb:
            plexdb.plexconn.createTable("version",
              ({"fieldname": "idVersion", "fieldtype": "varchar", "fieldsize": 50, "notnull": True},),
              ("idVersion",)
            )
            plexdb.plexconn.replace("version", ("idVersion",),(v.ADDON_VERSION,),"WHERE idVersion='%s'" % (v.ADDON_VERSION,))
            plexdb.plexconn.createTable("sections",
              ({"fieldname": "section_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": True},
               {"fieldname": "section_name", "fieldtype": "varchar", "fieldsize": 50, "notnull": False},
               {"fieldname": "plex_type", "fieldtype": "varchar", "fieldsize": 50, "notnull": False},
               {"fieldname": "kodi_tagid", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "sync_to_kodi", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "last_sync", "fieldtype": "bigint", "fieldsize": 0, "notnull": False}
              ),
              ("section_id",)
            )
            
            plexdb.plexconn.createTable("movie",
              ({"fieldname": "plex_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": True},
               {"fieldname": "checksum", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "section_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_fileid", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_pathid", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "fanart_synced", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "last_sync", "fieldtype": "bigint", "fieldsize": 0, "notnull": False}
              ),
              ("plex_id",)
            )            

            plexdb.plexconn.createTable("tvshow",
              ({"fieldname": "plex_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": True},
               {"fieldname": "checksum", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "section_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},               
               {"fieldname": "kodi_pathid", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "fanart_synced", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "last_sync", "fieldtype": "bigint", "fieldsize": 0, "notnull": False}
              ),
              ("plex_id",)
            )     
            
            plexdb.plexconn.createTable("season",
              ({"fieldname": "plex_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": True},
               {"fieldname": "checksum", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "section_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "tvshow_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "parent_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},               
               {"fieldname": "fanart_synced", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "last_sync", "fieldtype": "bigint", "fieldsize": 0, "notnull": False}
              ),
              ("plex_id",)
            )
            
            plexdb.plexconn.createTable("episode",
              ({"fieldname": "plex_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": True},
               {"fieldname": "checksum", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "section_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "tvshow_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "grandparent_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "season_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "parent_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},               
               {"fieldname": "kodi_fileid", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},               
               {"fieldname": "kodi_fileid_2", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},               
               {"fieldname": "kodi_pathid", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},               
               {"fieldname": "fanart_synced", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "last_sync", "fieldtype": "bigint", "fieldsize": 0, "notnull": False}
              ),
              ("plex_id",)
            )

            plexdb.plexconn.createTable("artist",
              ({"fieldname": "plex_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": True},
               {"fieldname": "checksum", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "section_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "fanart_synced", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "last_sync", "fieldtype": "bigint", "fieldsize": 0, "notnull": False}
              ),
              ("plex_id",)
            )

            plexdb.plexconn.createTable("album",
              ({"fieldname": "plex_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": True},
               {"fieldname": "checksum", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "section_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "artist_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "parent_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "fanart_synced", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "last_sync", "fieldtype": "bigint", "fieldsize": 0, "notnull": False}
              ),
              ("plex_id",)
            )

            plexdb.plexconn.createTable("track",
              ({"fieldname": "plex_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": True},
               {"fieldname": "checksum", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "section_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "artist_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "grandparent_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "album_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "parent_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_pathid", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},               
               {"fieldname": "last_sync", "fieldtype": "bigint", "fieldsize": 0, "notnull": False}
              ),
              ("plex_id",)
            )
            
            plexdb.plexconn.createTable("playlists",
              ({"fieldname": "plex_id", "fieldtype": "bigint", "fieldsize": 0, "notnull": True},
               {"fieldname": "plex_name", "fieldtype": "varchar", "fieldsize": 50, "notnull": False},
               {"fieldname": "plex_updatedat", "fieldtype": "bigint", "fieldsize": 0, "notnull": False},
               {"fieldname": "kodi_path", "fieldtype": "varchar", "fieldsize": 250, "notnull": False},
               {"fieldname": "kodi_type", "fieldtype": "varchar", "fieldsize": 50, "notnull": False},
               {"fieldname": "kodi_hash", "fieldtype": "varchar", "fieldsize": 50, "notnull": False},               
              ),
              ("plex_id",)
            )            
                        
            # DB indicees for faster lookups
            commands = (
                'CREATE INDEX IF NOT EXISTS ix_movie_1 ON movie (last_sync)',
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_movie_2 ON movie (kodi_id)',
                'CREATE INDEX IF NOT EXISTS ix_show_1 ON tvshow (last_sync)',
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_show_2 ON tvshow (kodi_id)',
                'CREATE INDEX IF NOT EXISTS ix_season_1 ON season (last_sync)',
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_season_2 ON season (kodi_id)',
                'CREATE INDEX IF NOT EXISTS ix_episode_1 ON episode (last_sync)',
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_episode_2 ON episode (kodi_id)',
                'CREATE INDEX IF NOT EXISTS ix_artist_1 ON artist (last_sync)',
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_artist_2 ON artist (kodi_id)',
                'CREATE INDEX IF NOT EXISTS ix_album_1 ON album (last_sync)',
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_album_2 ON album (kodi_id)',
                'CREATE INDEX IF NOT EXISTS ix_track_1 ON track (last_sync)',
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_track_2 ON track (kodi_id)',
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_playlists_2 ON playlists (kodi_path)',
                'CREATE INDEX IF NOT EXISTS ix_playlists_3 ON playlists (kodi_hash)',
            )
            if plexdb.plexconn.dbtype == "sqlite":
                for cmd in commands:
                    plexdb.plexconn.execute(cmd)


def wipe(table=None):
    """
    Completely resets the Plex database.
    If a table [unicode] name is provided, only that table will be dropped
    """
    with PlexDBBase() as plexdb:
        if table:
            tables = [table]
        else:
            data = plexdb.plexconn.TableList()
            tables = [i[0] for i in data]
        for table in tables:            
            plexdb.plexconn.execute('DROP table IF EXISTS %s' % table)
