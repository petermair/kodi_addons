#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals


class Playlists(object):
    def playlist_ids(self):
        """
        Returns an iterator of all Plex ids of playlists.
        """
        data = self.plexconn.select("playlists",("plex_id",))        
        return (x[0] for x in data)

    def kodi_playlist_paths(self):
        """
        Returns an iterator of all Kodi playlist paths.
        """
        data = self.plexconn.select("playlists",("kodi_path",))        
        return (x[0] for x in data)

    def delete_playlist(self, playlist):
        """
        Removes the entry for playlist [Playqueue_Object] from the Plex
        playlists table.
        Be sure to either set playlist.id or playlist.kodi_path
        """
        if playlist.plex_id:
            self.plexconn.delete("playlists","WHERE plexid=%s" % playlist.plexid)
            
        elif playlist.kodi_path:
            self.plexconn.delete("playlists","WHERE kodi_path=%s" % playlist.kodi_path)            
        else:
            raise RuntimeError('Cannot delete playlist: %s' % playlist)        

    def add_playlist(self, playlist):
        """
        Inserts or modifies an existing entry in the Plex playlists table.
        """
        self.plexconn.replace("playlists",
          ( "plex_id",
            "plex_name",
            "plex_updatedat",
            "kodi_path",
            "kodi_type",
            "kodi_hash"),
            (playlist.plex_id,
             playlist.plex_name,
             playlist.plex_updatedat,
             playlist.kodi_path,
             playlist.kodi_type,
             playlist.kodi_hash),
             "WHERE plex_id=%s" % playlist.plex_id
        )
        
    def playlist(self, playlist, plex_id=None, path=None):
        """
        Returns a complete Playlist (empty one passed in via playlist) for the
        entry with plex_id OR kodi_path.
        Returns None if not found
        """
        query = 'SELECT * FROM playlists WHERE %s = %s LIMIT 1'
        if plex_id:
            answ = self.plexconn.select("playlist",
              ("plex_id","plex_name","plex_updatedata","kodi_path","kodi_type","kodi_hash"),
              "WHERE plex_id=" % (plex_id))            
        elif path:
            answ = self.plexconn.select("playlist",
            ("plex_id","plex_name","plex_updatedata","kodi_path","kodi_type","kodi_hash"),
            "WHERE kodi_path=" % (path))            
        
        
        if len(answ)==0:
            return
        playlist.plex_id = answ[0]
        playlist.plex_name = answ[1]
        playlist.plex_updatedat = answ[2]
        playlist.kodi_path = answ[3]
        playlist.kodi_type = answ[4]
        playlist.kodi_hash = answ[5]
        return playlist

    def all_kodi_paths(self):
        """
        Returns a generator for all kodi_paths of all synched playlists
        """
        data = self.plexconn.select("playlists",("kodi_path",))        
        return (x[0] for x in data)

    def wipe_playlists(self):
        """
        Deletes all entries in the playlists table
        """
        self.plexconn.delete("playlists")
        
