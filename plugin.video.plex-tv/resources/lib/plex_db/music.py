#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
from .. import variables as v


class Music(object):
    def add_artist(self, plex_id, checksum, section_id, kodi_id, last_sync):
        """
        Appends or replaces music artist entry into the plex table
        """
        self.plexconn.replace(
            "artist",
            ("plex_id",
             "checksum",
             "section_id",
             "kodi_id",
             "last_sync"),
            (plex_id,
             checksum,
             section_id,
             kodi_id,
             last_sync),
             "WHERE plex_id = %s" % (plex_id,)
        )        

    def add_album(self, plex_id, checksum, section_id, artist_id, parent_id,
                  kodi_id, last_sync):
        """
        Appends or replaces an entry into the plex table
        """
        self.plexconn.replace(
            "album",
            ("plex_id",
             "checksum",
             "section_id",
             "artist_id",
             "parent_id",
             "kodi_id",
             "last_sync"),
            (plex_id,
             checksum,
             section_id,
             artist_id,
             parent_id,
             kodi_id,
             last_sync),
             "WHERE plex_id = %s" % (plex_id,)
        )        

    def add_song(self, plex_id, checksum, section_id, artist_id, grandparent_id,
                 album_id, parent_id, kodi_id, kodi_pathid, last_sync):
        """
        Appends or replaces an entry into the plex table
        """
        self.plexconn.replace(
            "track",
            ("plex_id",
             "checksum",
             "section_id",
             "artist_id",             
             "grandparent_id",
             "album_id",
             "parent_id",
             "kodi_id",
             "kodi_pathid",
             "last_sync"),
            (plex_id,
             checksum,
             section_id,
             artist_id,
             grandparent_id,
             album_id,
             parent_id,
             kodi_id,
             kodi_pathid,
             last_sync),
             "WHERE plex_id = %s" % (plex_id,)
        )
        
    def artist(self, plex_id):
        """
        Returns the show info as a tuple for the TV show with plex_id:
            plex_id INTEGER PRIMARY KEY,
            checksum INTEGER UNIQUE,
            section_id INTEGER,
            kodi_id INTEGER,
            last_sync INTEGER
        """
        if plex_id is None:
            return
        data = self.plexconn.select("artist",("*",), "WHERE plex_id=%s LIMIT 1" % (plex_id,))
        if len(data)==0:
            artist = None
        else:
            artist = data[0]
        return self.entry_to_artist(artist)

    def album(self, plex_id):
        """
        Returns the show info as a tuple for the TV show with plex_id:
            plex_id INTEGER PRIMARY KEY,
            checksum INTEGER UNIQUE,
            section_id INTEGER,
            artist_id INTEGER,  # plex_id of the parent artist
            parent_id INTEGER,  # kodi_id of the parent artist
            kodi_id INTEGER,
            last_sync INTEGER
        """
        if plex_id is None:
            return
        data = self.plexconn.select("album", ("*", ), "WHERE plex_id = %s LIMIT 1" % (plex_id,))
        if len(data)==0:
            album = None
        else:
            album = data[0]
        return self.entry_to_album(album)

    def song(self, plex_id):
        """
        Returns the show info as a tuple for the TV show with plex_id:
            plex_id INTEGER PRIMARY KEY,
            checksum INTEGER UNIQUE,
            section_id INTEGER,
            artist_id INTEGER,  # plex_id of the parent artist
            grandparent_id INTEGER,  # kodi_id of the parent artist
            album_id INTEGER,  # plex_id of the parent album
            parent_id INTEGER,  # kodi_id of the parent album
            kodi_id INTEGER,
            kodi_pathid INTEGER,
            last_sync INTEGER
        """
        if plex_id is None:
            return
        data = self.plexconn.select("track", ("*", ), "WHERE plex_id = %s LIMIT 1" % (plex_id,))
        if len(data)==0:
            track = None
        else:
            track = data[0]

        return self.entry_to_track(track)

    @staticmethod
    def entry_to_track(entry):
        if not entry:
            return
        return {
            'plex_type': v.PLEX_TYPE_SONG,
            'kodi_type': v.KODI_TYPE_SONG,
            'plex_id': entry[0],
            'checksum': entry[1],
            'section_id': entry[2],
            'artist_id': entry[3],
            'grandparent_id': entry[4],
            'album_id': entry[5],
            'parent_id': entry[6],
            'kodi_id': entry[7],
            'kodi_pathid': entry[8],
            'last_sync': entry[9]
        }

    @staticmethod
    def entry_to_album(entry):
        if not entry:
            return
        return {
            'plex_type': v.PLEX_TYPE_ALBUM,
            'kodi_type': v.KODI_TYPE_ALBUM,
            'plex_id': entry[0],
            'checksum': entry[1],
            'section_id': entry[2],
            'artist_id': entry[3],
            'parent_id': entry[4],
            'kodi_id': entry[5],
            'last_sync': entry[6]
        }

    @staticmethod
    def entry_to_artist(entry):
        if not entry:
            return
        return {
            'plex_type': v.PLEX_TYPE_ARTIST,
            'kodi_type': v.KODI_TYPE_ARTIST,
            'plex_id': entry[0],
            'checksum': entry[1],
            'section_id': entry[2],
            'kodi_id': entry[3],
            'last_sync': entry[4]
        }

    def album_has_songs(self, plex_id):
        """
        Returns True if there are songs left for the album with plex_id
        """
        _ex = self.plexconn.exists("track","WHERE album_id = %s" % (plex_id,))        
        return _ex

    def artist_has_albums(self, plex_id):
        """
        Returns True if there are albums left for the artist with plex_id
        """
        _ex = self.plexconn.exists("album","WHERE artist_id = %s" % (plex_id,))        
        return _ex        

    def artist_has_songs(self, plex_id):
        """
        Returns True if there are episodes left for the show with plex_id
        """
        _ex = self.plexconn.exists("track","WHERE artist_id = %s" % (plex_id,))        
        return _ex                

    def song_by_album(self, plex_id):
        """
        Returns an iterator for all songs that have a parent album_id with
        a value of plex_id
        """
        data = self.plexconn.select("track","*", "WHERE album_id=%s" % (plex_id,))        
        return (self.entry_to_track(x) for x in data)

    def song_by_artist(self, plex_id):
        """
        Returns an iterator for all songs that have a grandparent artist_id
        with a value of plex_id
        """
        data = self.plexconn.select("track",("*",),"WHERE artist_id=%s" % (plex_id,))        
        return (self.entry_to_track(x) for x in data)

    def album_by_artist(self, plex_id):
        """
        Returns an iterator for all albums that have a parent artist_id
        with a value of plex_id
        """
        data = self.plexconn.select("album",("*",), "WHERE artist_id=%s" % (plex_id,))
        return (self.entry_to_album(x) for x in data)

    def songs_have_been_synced(self):
        """
        Returns True if at least one song has been synced - indicating that
        Plex Music sync has been active at some point
        """
        _ex = self.plexconn.exists("track")        
        return _ex
