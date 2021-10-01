#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
from logging import getLogger

from . import common
from .. import db, variables as v, app, timing 
import re

LOG = getLogger('PLEX.kodi_db.music')

ARTIST_ROLE_ID = 1

class KodiMusicDB(common.KodiDBBase):
    db_kind = 'music'

    @db.catch_operationalerrors
    def add_path(self, path):
        """
        Add the path (unicode) to the music DB, if it does not exist already.
        Returns the path id
        """
        # SQL won't return existing paths otherwise
        path = '' if path is None else path
        data = self.kodiconn.select("path",("idPath",),"WHERE strPath = '%s'" % (self.kodiconn.escape(path), ))        
        if len(data)>0:
            pathid = data[0][0]
        else:
            pathid = self.kodiconn.insert("path",("strPath", "strHash"), (path, '123'))
            
        return pathid

    @db.catch_operationalerrors
    def setup_kodi_default_entries(self):
        """
        Makes sure that we retain the Kodi standard databases. E.g. that there
        is a dummy artist with ID 1
        """
        self.kodiconn.replace("artist",
          ("idArtist","strArtist","strMusicBrainzArtistID"),
          (1, '[Missing Tag]', 'Artist Tag Missing'),
          "WHERE idArtist=1"
        )

        self.kodiconn.replace("role",
          ("idRole","strRole"),
          (1,"Artist"),
          "WHERE idRole=%s" % ARTIST_ROLE_ID)        
        
        if v.KODIVERSION >= 18:
            self.kodiconn.delete("versiontagscan")
            self.kodiconn.insert("versiontagscan",
              ("idVersion","iNeedsScan","lastscanned"),
              (v.DB_MUSIC_VERSION, 0, timing.kodi_now())
            )

    @db.catch_operationalerrors
    def update_path(self, path, kodi_pathid):
        self.kodiconn.update("path",
          ("strPath", "strHash"),
          (path, '123'),
          "WHERE idPath='%s'" % (kodi_pathid, )
        )        

    def song_id_from_filename(self, filename, path):
        """
        Returns the Kodi song_id from the Kodi music database or None if not
        found OR something went wrong.
        """
        path_ids = self.kodiconn.select("path",("idPath",), "WHERE strPath = '%s'" % (self.kodiconn.escape(path), ))        
        if len(path_ids) != 1:
            LOG.debug('Found wrong number of path ids: %s for path %s, abort',
                      path_ids, path)
            return
        song_ids = self.kodiconn.select("song",("idSong", ),"WHERE strFileName = %s AND idPath = '%s'" % (self.kodiconn.escape(filename), path_ids[0][0]))
                                    
        if len(song_ids) != 1:
            LOG.info('Found wrong number of songs %s, abort', song_ids)
            return
        return song_ids[0][0]

    @db.catch_operationalerrors
    def delete_song_from_song_artist(self, song_id):
        """
        Deletes son from song_artist table and possibly orphaned roles
        """
        artists = self.kodiconn.select("song_artist",("idArtist", "idRole"),"WHERE idSong='%s'" % (song_id, ))        
        if len(artists)==0:
            # No entry to begin with
            return
        # Delete the entry
        self.kodiconn.delete("song_artist", "WHERE idSong='%s'" % (song_id,))

    @db.catch_operationalerrors
    def delete_song_from_song_genre(self, song_id):
        """
        Deletes the one entry with id song_id from the song_genre table.
        Will also delete orphaned genres from genre table
        """

        genres = self.kodiconn.select("song_genre",("idGenre",),"WHERE idSong='%s'" % (song_id,))
        self.kodiconn.delete("song_genre","WHERE idSong='%s'" %(song_id,))
        
        # Check for orphaned genres in both song_genre and album_genre tables
        for genre in genres:            
            if not self.kodiconn.exists("song_genre","WHERE idGenre = '%s'" %(genre[0])):
                if not self.kodiconn.exists("albumg_genre","WHERE idGenre='%s'" % (genre[0])):                
                    self.delete_genre(genre[0])

    @db.catch_operationalerrors
    def delete_genre(self, genre_id):
        """
        Dedicated method in order to catch OperationalErrors correctly
        """
        self.kodiconn.delete("genre","WHERE idGenre='%s'" % (genre_id,))

    @db.catch_operationalerrors
    def delete_album_from_album_genre(self, album_id):
        """
        Deletes the one entry with id album_id from the album_genre table.
        Will also delete orphaned genres from genre table
        """

        genres = self.kodiconn.select("album_genre",("idGenre",),"WHERE idAlbum = '%s'", (album_id,))
        self.kodiconn.delete("album_genre","idAlbum = '%s'",
                            (album_id, ))
        # Check for orphaned genres in both album_genre and song_genre tables
        for genre in genres:
            if not self.kodiconn.exists("album_genre", "WHERE idGenre = '%s'" %(genre[0], )):            
                if not self.kodiconn.exists("song_genre", "WHERE idGenre = '%s'" % (genre[0], )):                
                    self.delete_genre(genre[0])

    def new_album_id(self):
        maxalbum = self.kodiconn.select('album',("COALESCE(MAX(idAlbum), 0)",) )
        return maxalbum[0][0] + 1

    @db.catch_operationalerrors
    def add_album_17(self, *args):
        """
        strReleaseType: 'album' or 'single'
        """
        if app.SYNC.artwork:
            self.kodiconn.insert("album",
              ("idAlbum",
                "strAlbum","strMusicBrainzAlbumID",
                "strArtists", "strGenres",
                "iYear", "bCompilation","strReview",
                "strImage",
                "strLabel","iUserrating", "lastScraped", "strReleaseType"),
                (args)
            )
        else:
            args = list(args)
            del args[8] ##strImage
            self.kodiconn.insert("album",
              ("idAlbum",
                "strAlbum","strMusicBrainzAlbumID",
                "strArtists", "strGenres",
                "iYear", "bCompilation","strReview",                
                "strLabel","iUserrating", "lastScraped", "strReleaseType"),
                (args)
            )            

    @db.catch_operationalerrors
    def update_album_17(self, *args):
        args = list(args)
        idAlbum = args[12]
        del args[12]
        if app.SYNC.artwork:
            self.kodiconn.update(
                "album",
                ("strAlbum","strMusicBrainzAlbumID", "strArtists", "strGenres", "iYear", "bCompilation","strReview", 
                "strImage",
                "strLabel","iUserrating", "lastScraped", "strReleaseType"),
                (args),
                "WHERE idAlbum='%s'" % idAlbum
            )            
        else:            
            del args[7]
            self.kodiconn.update(
                "album",
                ("strAlbum","strMusicBrainzAlbumID", "strArtists", "strGenres", "iYear", "bCompilation","strReview",                 
                "strLabel","iUserrating", "lastScraped", "strReleaseType"),
                (args),
                "WHERE idAlbum='%s'" % idAlbum
            )            

    @db.catch_operationalerrors
    def add_album(self, *args):
        """
        strReleaseType: 'album' or 'single'
        """
        if app.SYNC.artwork:
            self.kodiconn.insert("album",
              ("idAlbum", "strAlbum",
                "strMusicBrainzAlbumID", "strArtistDisp", "strGenres", "iYear", "bCompilation", "strReview",
                "strImage",
                "strLabel", "iUserrating", "lastScraped", "strReleaseType"
              ),
              (args)
            )            
        else:
            args = list(args)
            del args[8]
            self.kodiconn.insert("album",
              ("idAlbum", "strAlbum",
                "strMusicBrainzAlbumID", "strArtistDisp", "strGenres", "iYear", "bCompilation", "strReview",                
                "strLabel", "iUserrating", "lastScraped", "strReleaseType"
              ),
              (args)
            )

    @db.catch_operationalerrors
    def update_album(self, *args):
        args = list(args)
        idAlbum = args[12]
        del args[12]
        if app.SYNC.artwork:
            self.kodiconn.update("album",
              ("strAlbum",
                "strMusicBrainzAlbumID", "strArtistDisp", "strGenres", "iYear", "bCompilation", "strReview",
                "strImage",
                "strLabel", "iUserrating", "lastScraped", "strReleaseType"
              ),
              (args),
              "WHERE idAlbum = '%s'" % (idAlbum,)
            ) 
        else:            
            del args[7]
            self.kodiconn.update("album",
              ("strAlbum",
                "strMusicBrainzAlbumID", "strArtistDisp", "strGenres", "iYear", "bCompilation", "strReview",                
                "strLabel", "iUserrating", "lastScraped", "strReleaseType"
              ),
              (args),
              "WHERE idAlbum = '%s'" % (idAlbum,)
            ) 

    @db.catch_operationalerrors
    def add_albumartist(self, artist_id, kodi_id, artistname):
        self.kodiconn.replace("album_artist",
          ("idArtist", "idAlbum", "strArtist"),
          (artist_id, kodi_id, artistname),
          "WHERE idArtist='%s' AND idAlbum='%s'" % (artist_id, kodi_id)
        )        

    @db.catch_operationalerrors
    def add_music_genres(self, kodiid, genres, mediatype):
        """
        Adds a list of genres (list of unicode) for a certain Kodi item
        """
        if mediatype == "album":
            # Delete current genres for clean slate
            self.kodiconn.delete("album_genre","WHERE idAlbum = "  % (kodiid,))

            for genre in genres:
                _genres = self.kodiconn.select("genre",("idGenre",), "WHERE strGenre='%s'" % (self.kodiconn.escape(genre),))
                
                try:
                    genreid = _genres[0][0]
                except:
                    # Create the genre
                    genreid = self.kodiconn.insert("genre",("strGenre",),(self.kodiconn.escape(genre,)))
                self.kodiconn.replace("album_genre",
                  ("idGenre","idAlbum"),
                  (genreid, kodiid),
                  "WHERE idGenre='%s' AND idAlbum='%s'" % (genreid, kodiid)
                )                
        elif mediatype == "song":
            # Delete current genres for clean slate
            self.kodiconn.delete("song_genre","WHERE idSong = '%s'" % (kodiid,))
            
            for genre in genres:
                _genres = self.kodiconn.select("genre",("idGenre",), "WHERE strGenre='%s'" % (self.kodiconn.escape(genre),))                
                try:
                    genreid = _genres[0][0]
                except:
                    # Create the genre
                    genreid = self.kodiconn.insert("genre",("strGenre",),(self.kodiconn.escape(genre),))                    
                self.kodiconn.replace("song_genre",
                  ("idGenre","idSong","iOrder"),
                  (genreid, kodiid, 0),
                  "WHERE idGenre='%s' AND idSong='%s'" % (genreid, kodiid))                

    def add_song_id(self):
        data = self.kodiconn.select("song",("COALESCE(MAX(idSong),0)",))        
        return data[0][0] + 1

    @db.catch_operationalerrors
    def add_song(self, *args):
        self.kodiconn.insert("song",
          ( "idSong",
            "idAlbum",
            "idPath",
            "strArtistDisp",
            "strGenres",
            "strTitle",
            "iTrack",
            "iDuration",
            "iYear",
            "strFileName",
            "strMusicBrainzTrackID",
            "iTimesPlayed",
            "lastplayed",
            "rating",
            "iStartOffset",
            "iEndOffset",
            "mood",
            "dateAdded"),
          (args)
        )
        

    @db.catch_operationalerrors
    def add_song_17(self, *args):
        self.kodiconn.insert("song",            
               ("idSong",
                "idAlbum",
                "idPath",
                "strArtists",
                "strGenres",
                "strTitle",
                "iTrack",
                "iDuration",
                "iYear",
                "strFileName",
                "strMusicBrainzTrackID",
                "iTimesPlayed",
                "lastplayed",
                "rating",
                "iStartOffset",
                "iEndOffset",
                "mood",
                "dateAdded")
            
        , (args))

    @db.catch_operationalerrors
    def update_song(self, *args):
        args = list(args)
        idSong = args[len(args)-1]
        del args[len(args)-1]
        self.kodiconn.update(
          "song",
          ( "idAlbum",
            "strArtistDisp",
            "strGenres",
            "strTitle",
            "iTrack",
            "iDuration",
            "iYear",
            "strFilename",
            "iTimesPlayed",
            "lastplayed",
            "rating",
            "comment",
            "mood",
            "dateAdded"),
          (args),
            "WHERE idSong = '%s'" % (idSong,)
        )

    @db.catch_operationalerrors
    def set_playcount(self, *args):
        args = list(args)
        idSong = args[len(args)-1]
        del args[len(args)-1]
        self.kodiconn.update("song",
          ("iTimesPlayed","lastplayed"),
          (args),
          "WHERE idSong='%s'" % (idSong,)
        )        

    @db.catch_operationalerrors
    def update_song_17(self, *args):
        args = list(args)
        songid = args[len(args)-1]
        del args[len(args)-1]
        self.kodiconn.update("song",
            ("idAlbum",
             "strArtists",
            "strGenres",
            "strTitle",
            "iTrack",
            "iDuration",
            "iYear",
            "strFilename",
            "iTimesPlayed",
            "lastplayed",
            "rating",
            "comment",
            "mood",
            "dateAdded"),
            (args),
            "WHERE idSong = '%s'" % (songid,)
        )        

    def path_id_from_song(self, kodi_id):
        data = self.kodiconn.select("song",("idPath",),"WHERE idSong='%s' LIMIT 1" % (kodi_id, ))        
        try:
            return data[0][0]
        except:
            pass

    @db.catch_operationalerrors
    def add_artist(self, name, musicbrainz):
        """
        Adds a single artist's name to the db
        """
        data = self.kodiconn.select("artist",("idArtist","strArtist"),"WHERE strMusicBrainzArtistID = '%s'" % (musicbrainz,))
        
        try:
            result = data[0]
            artistid = result[0]
            artistname = result[1]
        except:
            result = self.kodiconn.select("artist",("idArtist",),"WHERE strArtist='%s'" %(self.kodiconn.escape(name),))            
            try:
                artistid = data[0][0]
            except:
                # Krypton has a dummy first entry idArtist: 1  strArtist:
                # [Missing Tag] strMusicBrainzArtistID: Artist Tag Missing
                artistid = self.kodiconn.insert(
                    "artist",
                    ("strArtist","strMusicBrainzArtistID"),
                    (name, musicbrainz)
                )                
        else:
            if artistname != name:
                self.kodiconn.update("artist",
                  ("strArtist",),
                  (name,),
                  "WHERE idArtist='%s'" % (artistid)
                )                
        return artistid

    @db.catch_operationalerrors
    def update_artist(self, *args):
        args = list(args)
        artistid = args[len(args)-1]
        del args[len(args)-1]

        if app.SYNC.artwork:
            self.kodiconn.update("artist",
                ("strGenres",
                "strBiography",
                "strImage",
                "strFanart",
                "lastScraped"),
                (args),
                "WHERE idArtist = '%s'" % (artistid,)
            )
            
        else:
            
            del args[3], args[2]
            self.kodiconn.update("artist",
                ("strGenres",
                "strBiography",                
                "strFanart",
                "lastScraped"),
                (args),
                "WHERE idArtist = '%s'" % (artistid,)
            )                        

    @db.catch_operationalerrors
    def remove_song(self, kodi_id):
        self.kodiconn.delete("song","WHERE idSong = '%s'" % (kodi_id, ))

    @db.catch_operationalerrors
    def remove_path(self, path_id):

        self.kodiconn.delete('path', "WHERE idPath = '%s'" % (path_id, ))

    @db.catch_operationalerrors
    def add_song_artist(self, artist_id, song_id, artist_name):
        self.kodiconn.replace("song_artist",
            (
                "idArtist",
                "idSong",
                "idRole",
                "iOrder",
                "strArtist"),            
        (artist_id, song_id, ARTIST_ROLE_ID, 0, artist_name),
        "WHERE idArtist='%s' AND idSong='%s' AND idRole='%s'" %(artist_id, song_id, ARTIST_ROLE_ID))

    @db.catch_operationalerrors
    def add_albuminfosong(self, song_id, album_id, track_no, track_title,
                          runtime):
        """
        Kodi 17 only
        """
        self.kodiconn.replace(
            "albuminfosong",
            ("idAlbumInfoSong",
                "idAlbumInfo",
                "iTrack",
                "strTitle",
                "iDuration"),            
        (song_id, album_id, track_no, track_title, runtime),
        "WHERE idAlbumInfoSong='%s' AND idAlbumInfo='%s' AND iTrack='%s'"
          % (song_id, album_id, track_no)
        )

    @db.catch_operationalerrors
    def update_userrating(self, kodi_id, kodi_type, userrating):
        """
        Updates userrating for songs and albums
        """
        if kodi_type == v.KODI_TYPE_SONG:
            column = 'userrating'
            identifier = 'idSong'
        elif kodi_type == v.KODI_TYPE_ALBUM:
            column = 'iUserrating'
            identifier = 'idAlbum'
        else:
            return

        self.kodiconn.update(kodi_type, (column,), (userrating,),
          "WHERE "+identifier+"='%s'" % (kodi_id))

    @db.catch_operationalerrors
    def remove_albuminfosong(self, kodi_id):
        """
        Kodi 17 only
        """
        self.kodiconn.delete("albuminfosong","WHERE idAlbumInfoSong = '%s'" % (kodi_id,))        

    @db.catch_operationalerrors
    def remove_album(self, kodi_id):
        if v.KODIVERSION < 18:
            self.kodiconn.delete("albuminfosong", " WHERE idAlbumInfo = '%s'" % (kodi_id,))
            
        self.kodiconn.delete("album_artist", "WHERE idAlbum = '%s'" % (kodi_id,))        
        self.kodiconn.delete("album", "WHERE idAlbum = '%s'" % (kodi_id,))                

    @db.catch_operationalerrors
    def remove_artist(self, kodi_id):
        self.kodiconn.delete("album_artist", "WHERE idArtist = '%s'" % (kodi_id,))  
        self.kodiconn.delete("artist", "WHERE idArtist = '%s'" % (kodi_id,))  
        self.kodiconn.delete("song_artist", "WHERE idArtist = '%s'" % (kodi_id,))          
