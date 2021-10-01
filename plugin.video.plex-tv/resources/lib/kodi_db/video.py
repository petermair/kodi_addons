#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from logging import getLogger
from sqlite3 import IntegrityError
from sqlite3.dbapi2 import DatabaseError, Error

from . import common
from .. import db, path_ops, timing, variables as v
import re

LOG = getLogger('PLEX.kodi_db.video')

MOVIE_PATH = 'plugin://%s.movies/' % v.ADDON_ID
SHOW_PATH = 'plugin://%s.tvshows/' % v.ADDON_ID


class KodiVideoDB(common.KodiDBBase):
    db_kind = 'video'

    @db.catch_operationalerrors
    def create_kodi_db_indicees(self):
        """
        Index the "actors" because we got a TON - speed up SELECT and WHEN
        """
        commands = (
            'CREATE UNIQUE INDEX IF NOT EXISTS ix_actor_2 ON actor (actor_id);',
            'CREATE UNIQUE INDEX IF NOT EXISTS ix_files_2 ON files (idFile);',
        )
        if self.kodiconn.dbtype=="sqlite":
          for cmd in commands:
            self.kodiconn.execute(cmd)

    @db.catch_operationalerrors
    def setup_path_table(self):
        """
        Use with Kodi video DB

        Sets strContent to e.g. 'movies' and strScraper to metadata.local

        For some reason, Kodi ignores this if done via itemtypes while e.g.
        adding or updating items. (addPath method does NOT work)
        """
        for path, kind in ((MOVIE_PATH, 'movies'), (SHOW_PATH, 'tvshows')):
            path_id = self.get_path(path)
            if path_id is None:
                self.kodiconn.insert("path",
                   ("strPath", "strContent", "strScraper", "noUpdate", "exclude"),
                    (path, kind,'metadata.local',1,0)
                )

    @db.catch_operationalerrors
    def parent_path_id(self, path):
        """
        Video DB: Adds all subdirectories to path table while setting a "trail"
        of parent path ids
        """
        parentpath = path_ops.path.abspath(
            path_ops.path.join(path,
                               path_ops.decode_path(path_ops.path.pardir)))
        pathid = self.get_path(parentpath)
        if pathid is None:
            pathid = self.kodiconn.insert("path",
              ("strPath", "dateAdded"),
              (parentpath, timing.kodi_now())
            )
            
            if parentpath != path:
                # In case we end up having media in the filesystem root, C:\
                parent_id = self.parent_path_id(parentpath)
                self.update_parentpath_id(parent_id, pathid)
        return pathid

    @db.catch_operationalerrors
    def update_parentpath_id(self, parent_id, pathid):
        """
        Dedicated method in order to catch OperationalErrors correctly
        """
        self.kodiconn.update("path",
          ("idParentPath",),
          (parent_id,),
          " WHERE idPath = '%s'" % pathid
        )

    @db.catch_operationalerrors
    def add_path(self, path, date_added=None, id_parent_path=None,
                 content=None, scraper=None):
        """
        Returns the idPath from the path table. Creates a new entry if path
        [unicode] does not yet exist (using date_added [kodi date type],
        id_parent_path [int], content ['tvshows', 'movies', None], scraper
        [usually 'metadata.local'])

        WILL activate noUpdate for the path!
        """
        path = '' if path is None else path
        data = self.kodiconn.select("path",("idPath",),"WHERE strPath = '%s' LIMIT 1" % (self.kodiconn.escape(path), ))
        try:
            pathid = data[0][0]
        except:
            pathid = self.kodiconn.insert("path",
              ( "strPath", "dateAdded", "idParentPath", "strContent", "strScraper", "noUpdate"),
                (path, date_added, id_parent_path, content, scraper, 1)
            )            
        return pathid

    def get_path(self, path):
        """
        Returns the idPath from the path table for path [unicode] or None
        """
        data = self.kodiconn.select("path", ("idPath",),"WHERE strPath = '%s'" %(self.kodiconn.escape(path),))
        try:
            return data[0][0]
        except:
            pass

    @db.catch_operationalerrors
    def add_file(self, filename, path_id, date_added):
        """
        Adds the filename [unicode] to the table files if not already added
        and returns the idFile.
        """
        pathid = self.kodiconn.insert("files",
          ("idPath", "strFilename", "dateAdded"),
          (path_id, filename, date_added)
        )
        
        return pathid

    def modify_file(self, filename, path_id, date_added):
        data = self.kodiconn.select("files",("idFile",), 
          "WHERE idPath = '%s' AND strFilename = '%s'" % (path_id, self.kodiconn.escape(filename))
        )
        try:
            file_id = data[0][0]
        except:
            file_id = self.add_file(filename, path_id, date_added)
        return file_id

    def obsolete_file_ids(self):
        """
        Returns a generator for idFile of all Kodi file ids that do not have a
        dateAdded set (dateAdded NULL) and the filename start with
        'plugin://plugin.video.plex-tv'
        These entries should be deleted as they're created falsely by Kodi.
        """
        data = self.kodiconn.select("files",("idFile",), 
          "WHERE dateAdded IS NULL AND strFilename LIKE 'plugin://plugin.video.plex-tv%'")        
        return (x[0] for x in data)

    def tvshow_id_from_path(self, path):
        """
        Returns the idShow for path [unicode] or None
        """
        data = self.kodiconn.select("path", ("idPath",), "WHERE strPath = '%s' LIMIT 1" % (self.kodiconn.escape(path),))
        try:
            path_id = data[0][0]
        except:
            return

        data = self.kodiconn.select("tvshowlinkpath", ("idShow",), 
          "WHERE idPath = %s LIMIT 1" % (path_id,)
        )
        
        try:
            return data[0][0]
        except:
            pass

    @db.catch_operationalerrors
    def remove_file(self, file_id, remove_orphans=True):
        """
        Removes the entry for file_id from the files table. Will also delete
        entries from the associated tables: bookmark, settings, streamdetails.
        If remove_orphans is true, this method will delete any orphaned path
        entries in the Kodi path table
        """
        data = self.kodiconn.select("files",("idPath", ), 
          "WHERE idFile = '%s' LIMIT 1" % (file_id,)
        )        
        try:
            path_id = data[0][0]
        except:
            return

        self.kodiconn.delete("files", "WHERE idFile = %s" % (file_id,))
        self.kodiconn.delete("bookmark", "WHERE idFile = %s" % (file_id,))
        self.kodiconn.delete("settings", "WHERE idFile = %s" % (file_id,))
        self.kodiconn.delete("streamdetails", "WHERE idFile = %s" % (file_id,))
        self.kodiconn.delete("stacktimes", "WHERE idFile = %s" % (file_id,))
        if remove_orphans:
            # Delete orphaned path entry
            data = self.kodiconn.select("files", ("idFile", ),
              "WHERE idPath = '%s' LIMIT 1" % (path_id,)
            )
            
            if len(data)==0:
                # Make sure we're not deleting our root paths!
                self.kodiconn.delete("path", 
                "WHERE idPath = '%s' AND strPath NOT IN ('%s', '%s')" % (path_id, MOVIE_PATH, SHOW_PATH)
            )

    @db.catch_operationalerrors
    def _modify_link_and_table(self, kodi_id, kodi_type, entries, link_table,
                               table, key, first_id=None):
        first_id = first_id if first_id is not None else 1
        entry_ids = []
        for entry in entries:
            data = self.kodiconn.select(table, (key,), "WHERE name = '%s'  LIMIT 1" % (self.kodiconn.escape(entry), ))           
            if len(data)>0:
                entry_id = data[0][0]
            else:
                entry_id = self.kodiconn.insert(table, ("name", ), (entry, ))                
            
            entry_ids.append(entry_id)
        # Now process the ids obtained from the names
        # Get the existing, old entries
        outdated_entries = []
        try:
            c = self.kodiconn.select(link_table, (key,),
              "WHERE media_id = '%s' AND media_type = '%s'" % (kodi_id, kodi_type)
            )            
            for entry_id in c:
                try:
                    entry_ids.remove(entry_id[0])
                except ValueError:
                    outdated_entries.append(entry_id[0])
        except DatabaseError: 
            LOG.info('No data!')
        
        # Add all new entries that haven't already been added
        for entry_id in entry_ids:
            try:
                self.kodiconn.insert(link_table, (key, "media_id", "media_type"),
                  (entry_id, kodi_id, kodi_type)
                )                
            except IntegrityError:
                LOG.info('IntegrityError: skipping entry %s for table %s',
                         entry_id, link_table)
        # Delete all outdated references in the link table. Also check whether
        # we need to delete orphaned entries in the master table
        for entry_id in outdated_entries:
            self.kodiconn.delete(link_table,
              "WHERE %s = '%s' AND media_id = %s AND media_type='%s'" % 
              (key, entry_id, kodi_id, kodi_type)
            )
            data = self.kodiconn.select(link_table, (key, ), "WHERE %s = '%s'" % (key, entry_id))
            if len(data)==0:
                # Delete in the original table because entry is now orphaned
                self.kodiconn.delete(table, "WHERE %s='%s'" % (key, entry_id))

    def modify_countries(self, kodi_id, kodi_type, countries=None):
        """
        Writes a country (string) in the list countries into the Kodi DB. Will
        also delete any orphaned country entries.
        """
        
        self._modify_link_and_table(kodi_id,
                                    kodi_type,
                                    countries if countries else [],
                                    'country_link',
                                    'country',
                                    'country_id')

    def modify_genres(self, kodi_id, kodi_type, genres=None):
        """
        Writes a country (string) in the list countries into the Kodi DB. Will
        also delete any orphaned country entries.
        """
        self._modify_link_and_table(kodi_id,
                                    kodi_type,
                                    genres if genres else [],
                                    'genre_link',
                                    'genre',
                                    'genre_id')

    def modify_studios(self, kodi_id, kodi_type, studios=None):
        """
        Writes a country (string) in the list countries into the Kodi DB. Will
        also delete any orphaned country entries.
        """
        self._modify_link_and_table(kodi_id,
                                    kodi_type,
                                    studios if studios else [],
                                    'studio_link',
                                    'studio',
                                    'studio_id')

    def modify_tags(self, kodi_id, kodi_type, tags=None):
        """
        Writes a country (string) in the list countries into the Kodi DB. Will
        also delete any orphaned country entries.
        """
        self._modify_link_and_table(kodi_id,
                                    kodi_type,
                                    tags if tags else [],
                                    'tag_link',
                                    'tag',
                                    'tag_id')

    def add_people(self, kodi_id, kodi_type, people):
        """
        Makes sure that actors, directors and writers are recorded correctly
        for the elmement kodi_id, kodi_type.
        Will also delete a freshly orphaned actor entry.
        """
        for kind, people_list in people.iteritems():
            self._add_people_kind(kodi_id, kodi_type, kind, people_list)

    @db.catch_operationalerrors
    def _add_people_kind(self, kodi_id, kodi_type, kind, people_list):
        # Save new people to Kodi DB by iterating over the remaining entries
        if kind == 'actor':
            for person in people_list:
                # Make sure the person entry in table actor exists
                actor_id, new = self._get_actor_id(person[0],
                                                   art_url=person[1])
                if not new and person[1]:
                    # Person might have shown up as a director or writer first
                    # WITHOUT an art url from the Plex side!
                    # Check here if we need to set the actor's art url
                    self._check_actor_art(actor_id, person[1])
                # Link the person with the media element
                try:
                    self.kodiconn.replace("actor_link",
                      ("actor_id","media_id", "media_type","role","cast_order"),
                      (actor_id, kodi_id, kodi_type, person[2], person[3]),
                      "WHERE actor_id='%s' AND media_id='%s' AND media_type='%s'" % 
                        (actor_id, kodi_id, kodi_type)
                    )
                except IntegrityError:
                    # With Kodi, an actor may have only one role, unlike Plex
                    pass
        else:
            for person in people_list:
                # Make sure the person entry in table actor exists:
                actor_id, _ = self._get_actor_id(person[0])
                # Link the person with the media element
                try:
                    self.kodiconn.replace(kind+'_link',
                      ("actor_id","media_id","media_type"),
                      (actor_id, kodi_id, kodi_type),
                      "WHERE actor_id='%s' AND media_id='%s' AND media_type='%s'" %
                        (actor_id, kodi_id, kodi_type)
                    )                                         
                except IntegrityError:
                    # Again, Kodi may have only one person assigned to a role
                    pass

    def modify_people(self, kodi_id, kodi_type, people=None):
        """
        Makes sure that actors, directors and writers are recorded correctly
        for the elmement kodi_id, kodi_type.
        Will also delete a freshly orphaned actor entry.
        """
        for kind, people_list in (people if people else
                                  {'actor': [],
                                   'director': [],
                                   'writer': []}).iteritems():
            self._modify_people_kind(kodi_id, kodi_type, kind, people_list)

    @db.catch_operationalerrors
    def _modify_people_kind(self, kodi_id, kodi_type, kind, people_list):
        # Get the people already saved in the DB for this specific item
        if kind == 'actor':
            old_people = self.kodiconn.select(
                """actor_link 
                   LEFT JOIN actor ON actor.actor_id = actor_link.actor_id 
                   LEFT JOIN art ON (art.media_id = actor_link.actor_id AND art.media_type = 'actor')""",
                ("actor.actor_id", "actor.name", "art.url", "actor_link.role", "actor_link.cast_order"),
                "WHERE actor_link.media_id = '%s' AND actor_link.media_type = '%s'" %
                    (kodi_id, kodi_type)
            )            
        else:
            old_people = self.kodiconn.select(                
                kind+"""_link AS l
                LEFT JOIN actor AS a ON a.actor_id = l.actor_id""",
                ("a.actor_id", "a.name"),
                "WHERE l.media_id = '%s' AND l.media_type = '%s'" %
                (kodi_id, kodi_type)
            )
                    
        # Determine which people we need to save or delete
        outdated_people = []
        for person in old_people:
            try:
                people_list.remove(person[1:])
            except ValueError:
                outdated_people.append(person)
        # Get rid of old entries
                
        
        ##query_actor_delete = 'DELETE FROM actor WHERE actor_id = %s'
        for person in outdated_people:
            # Delete the outdated entry            
            self.kodiconn.delete(kind+"_link",
              "WHERE actor_id = '%s' AND media_id = '%s' AND media_type = '%s'" % 
                (person[0], kodi_id, kodi_type)
            )            
            # Do we now have orphaned entries?
            for person_kind in ('actor', 'writer', 'director'):
                cs = self.kodiconn.select(person_kind+"_link",("*",),
                  "WHERE actor_id = '%s'" % (person[0],)
                )                
            if len(cs)>0:                    
                break
            else:
                # person entry in actor table is now orphaned
                # Delete the person from actor table
                self.kodiconn.delete("actor","WHERE actor_id = '%s'" % (person[0],))
                if kind == 'actor':
                    # Delete any associated artwork
                    self.delete_artwork(person[0], 'actor')
        # Save new people to Kodi DB by iterating over the remaining entries
        self._add_people_kind(kodi_id, kodi_type, kind, people_list)

    @db.catch_operationalerrors
    def _new_actor_id(self, name, art_url):
        # Not yet in actor DB, add person
        actor_id = self.kodiconn.insert("actor", ("name",), (name,))        
        if art_url:
            self.add_art(art_url, actor_id, 'actor', 'thumb')
        return actor_id

    def _get_actor_id(self, name, art_url=None):
        """
        Returns the tuple
            (actor_id [int], new_entry [bool])
        for name [unicode] in table actor (without ensuring that the name
        matches)."new_entry" will be True if a new DB entry has just been
        created.
        If not, will create a new record with actor_id, name, art_url

        Uses Plex ids and thus assumes that Plex person id is unique!
        """
        data = self.kodiconn.select("actor",("actor_id", ), "WHERE name='%s' LIMIT 1" % (self.kodiconn.escape(name),))
        if len(data)>0:
            return (data[0][0], False)
        else:
            return (self._new_actor_id(name, art_url), True)

    def _check_actor_art(self, actor_id, url):
        """
        Sets the actor's art url [unicode] for actor_id [int]
        """
        _exists = self.kodiconn.exists("art", 
          "WHERE media_id = '%s' AND media_type = 'actor'"
            % (actor_id, )
          )
        if not _exists:
            # We got a new artwork url for this actor!
            self.add_art(url, actor_id, 'actor', 'thumb')

    def get_art(self, kodi_id, kodi_type):
        """
        Returns a dict of all available artwork with unicode urls/paths:
        {
            'thumb'
            'poster'
            'banner'
            'clearart'
            'clearlogo'
            'discart'
            'fanart'    and also potentially more fanart 'fanart1', 'fanart2',
        }
        Missing fanart will not appear in the dict. 'landscape' and 'icon'
        might be implemented in the future.
        """
        data = self.kodiconn.select("art",("type","url"), 
          "WHERE media_id='%s' AND media_type='%s'" % (kodi_id, kodi_type)
        )                                
        return dict(data)

    @db.catch_operationalerrors
    def modify_streams(self, fileid, streamdetails=None, runtime=None):
        """
        Leave streamdetails and runtime empty to delete all stream entries for
        fileid
        """
        # First remove any existing entries
        self.kodiconn.delete("streamdetails","WHERE idFile = '%s'" % (fileid,))
        if not streamdetails:
            return
        for videotrack in streamdetails['video']:
            self.kodiconn.insert("streamdetails",
              ( "idFile", "iStreamType", "strVideoCodec", "fVideoAspect",
                "iVideoWidth", "iVideoHeight", "iVideoDuration" ,"strStereoMode"),
              ( fileid, 0, videotrack['codec'],
                videotrack['aspect'], videotrack['width'],
                videotrack['height'], runtime,
                videotrack['video3DFormat'])              
            )            
        for audiotrack in streamdetails['audio']:
            self.kodiconn.insert("streamdetails",
              ("idFile", "iStreamType", "strAudioCodec", "iAudioChannels", "strAudioLanguage"),
              (fileid, 1, audiotrack['codec'], audiotrack['channels'], audiotrack['language'])            
            )            
        for subtitletrack in streamdetails['subtitle']:
            self.kodiconn.insert("streamdetails",
              ("idFile", "iStreamType", "strSubtitleLanguage"),
              (fileid, 2, subtitletrack)
            )            

    def video_id_from_filename(self, filename, path):
        """
        Returns the tuple (itemId, type) where
            itemId:     Kodi DB unique Id for either movie or episode
            type:       either 'movie' or 'episode'

        Returns None if not found OR if too many entries were found
        """
        files = self.kodiconn.select("files",("idFile","idPath"),
          "WHERE strFilename = '%s'" %(self.kodiconn.escape(filename),))        
        if len(files) == 0:
            LOG.debug('Did not find any file, abort')
            return
        # result will contain a list of all idFile with matching filename and
        # matching path
        result = []
        for file in files:
            # Use idPath to get path as a string
            paths = self.kodiconn.select("path", ("strPath",),
              "WHERE idPath = '%s'" % file[1]
            )
            try:
                path_str = paths[0][0]
            except:
                # idPath not found; skip
                continue
            # For whatever reason, double might have become triple
            path_str = path_str.replace('///', '//').replace('\\\\\\', '\\\\')
            if path_str == path:
                result.append(file[0])
        if len(result) == 0:
            LOG.info('Did not find matching paths, abort')
            return
        # Kodi seems to make ONE temporary entry; we only want the earlier,
        # permanent one
        if len(result) > 2:
            LOG.warn('We found too many items with matching filenames and '
                     ' paths, aborting')
            return
        file_id = result[0]

        # Try movies first
        data = self.kodiconn.select("movie",("idMovie", ),
          "WHERE idFile = '%s'" % (file_id, )
        )        

        try:
            movie_id = data[0][0]
            typus = v.KODI_TYPE_MOVIE
        except:
            # Try tv shows next
            data = self.kodiconn.select("episode",("idEpisode", ),
              "WHERE idFile = '%s'" % (file_id, )
            )                                            
            try:
                movie_id = data[0][0]
                typus = v.KODI_TYPE_EPISODE
            except:
                LOG.debug('Did not find a video DB match')
                return
        return movie_id, typus

    def get_resume(self, file_id):
        """
        Returns the first resume point in seconds (int) if found, else None for
        the Kodi file_id provided
        """
        data = self.kodiconn.select("bookmark",
          ("timeInSeconds",),
          "WHERE idFile = %s LIMIT 1" % (file_id, )
        )

        try:
            return data[0][0]
        except:
            pass

    def get_playcount(self, file_id):
        """
        Returns the playcount for the item file_id or None if not found
        """
        data = self.kodiconn.select("files",("playCount",),
          "WHERE idFile = '%s' LIMIT 1" % (file_id, )
        )
        try:
            return data[0][0]
        except:
            pass

    @db.catch_operationalerrors
    def set_resume(self, file_id, resume_seconds, total_seconds, playcount,
                   dateplayed):
        """
        Adds a resume marker for a video library item. Will even set 2,
        considering add-on path widget hacks.
        """
        # Delete existing resume point
        self.kodiconn.delete("bookmark","WHERE idFile = '%s'" % (file_id,))        
        # Set watched count
        # Be careful to set playCount to None, NOT the int zero!
        self.kodiconn.update("files", 
          ("playCount", "lastPlayed"),
          (playcount or None, dateplayed),
          "WHERE idFile = '%s'" % (file_id,)
        )
        # Set the resume bookmark
        if resume_seconds:
            self.kodiconn.insert("bookmark", 
               ("idFile",
                "timeInSeconds",
                "totalTimeInSeconds",
                "thumbNailImage",
                "player",
                "playerState",
                "type"),
                (file_id,
                  resume_seconds,
                  total_seconds,
                  '',
                  'VideoPlayer',
                  '',
                  1)
            )
            
    @db.catch_operationalerrors
    def create_tag(self, name):
        """
        Will create a new tag if needed and return the tag_id
        """
        data = self.kodiconn.select("tag", ("tag_id", ),"WHERE name = '%s'" % (name,))
        try:
            tag_id = data[0][0]
        except:
            tag_id = self.kodiconn.insert("tag", ("name",), (name,))            
        return tag_id

    @db.catch_operationalerrors
    def update_tag(self, oldtag, newtag, kodiid, mediatype):
        """
        Updates the tag_id by replaying oldtag with newtag
        """
        try:
            self.kodiconn.update("tag_link",
              ("tag_id", ),
              (newtag),
              "WHERE media_id = '%s' AND media_type = '%s' AND tag_id = '%s'" %
              (kodiid, mediatype, oldtag,)
            )            
        except Exception:
            # The new tag we are going to apply already exists for this item
            # delete current tag instead
            self.kodiconn.delete("tag_link",
              "WHERE media_id = '%s' AND media_type = '%s' AND tag_id = '%s'" % 
                (kodiid, mediatype, oldtag,)
            )


    @db.catch_operationalerrors
    def create_collection(self, set_name):
        """
        Returns the collection/set id for set_name [unicode]
        """
        data = self.kodiconn.select("sets",("idSet",),"WHERE strSet = '%s'" % (self.kodiconn.escape(set_name),))
        try:
            setid = data[0][0]
        except:
            setid = self.kodiconn.insert("sets", ("strSet",), (self.kodiconn.escape(set_name),))
        return setid

    @db.catch_operationalerrors
    def assign_collection(self, setid, movieid):
        """
        Assign the movie to one set/collection
        """
        self.kodiconn.update("movie", ("idSet",), (setid,), 
          "WHERE idMovie = '%s'" % movieid
        )        

    @db.catch_operationalerrors
    def remove_from_set(self, movieid):
        """
        Remove the movie with movieid [int] from an associated movie set, movie
        collection
        """
        self.kodiconn.update("movie", ("idSet",),(None,),"WHERE idMovie='%s'" % (movieid,))

    def get_set_id(self, kodi_id):
        """
        Returns the set_id for the movie with kodi_id or None
        """
        data = self.kodiconn.select("movie", ("idSet",), 
          "WHERE idMovie = '%s'" % (kodi_id,)
        )        
        try:
            return data[0][0]
        except:
            pass

    @db.catch_operationalerrors
    def delete_possibly_empty_set(self, set_id):
        """
        Checks whether there are other movies in the set set_id. If not,
        deletes the set
        """
        data = self.kodiconn.select("movie", ("idSet",), 
          "WHERE idSet = '%s'" % (set_id,)
        )  
        
        if len(data)==0:
            self.kodiconn.delete("sets","WHERE idSet = '%s'" % (set_id,))            

    @db.catch_operationalerrors
    def add_season(self, showid, seasonnumber, name, userrating):
        """
        Adds a TV show season to the Kodi video DB or simply returns the ID,
        if there already is an entry in the DB
        """
        id = self.kodiconn.insert("seasons",
          ("idShow", "season", "name", "userrating"),
          (showid, seasonnumber, name, userrating)
        )
        
        return id

    @db.catch_operationalerrors
    def update_season(self, seasonid, showid, seasonnumber, name, userrating):
        """
        Updates a TV show season with a certain seasonid
        """
        self.kodiconn.update("seasons",
          ("idShow","season","name","userrating"),
          (showid, seasonnumber, name, userrating),
          "WHERE idSeason = '%s'" % (seasonid,)
        )        

    @db.catch_operationalerrors
    def add_uniqueid(self, *args):
        """
        Feed with:
            media_id: int
            media_type: string
            value: string
            type: e.g. 'imdb' or 'tvdb'
        """
        id = self.kodiconn.insert(
            "uniqueid",
            ("media_id","media_type","value","type"),
            (args)
        )        
        return id

    @db.catch_operationalerrors
    def update_uniqueid(self, *args):
        """
        Pass in value, media_id, media_type, type
        """
        data = self.kodiconn.select("uniqueid",
           ("uniqueid",),
           "WHERE media_id=%s AND media_type='%s' AND value='%s' AND type='%s' LIMIT 1" %
           (args)
           )
        if len(data) == 0:
            id = self.kodiconn.insert(
                "uniqueid",
                ("media_id","media_type","value","type"),
                (args),
            )    
        else:
          id = data[0][0]
        return id

    @db.catch_operationalerrors
    def remove_uniqueid(self, kodi_id, kodi_type):
        """
        Deletes the entry from the uniqueid table for the item
        """
        self.kodiconn.delete("uniqueid",
          "WHERE media_id = '%s' AND media_type = '%s'" % (kodi_id, kodi_type)
        )

    @db.catch_operationalerrors
    def update_ratings(self, *args):
        """
        Feed with media_id, media_type, rating_type, rating, votes, rating_id
        """
        data = self.kodiconn.select("rating",("rating_id",),
          "WHERE media_id='%s' AND media_type='%s' AND rating='%s'" %
          (args[0], args[1], args[2])
        )
        if len(data)==0:
            id = self.kodiconn.insert("rating",
              ("media_id", "media_type", "rating_type", "rating", "votes"),
              (args)
            )
        else:
          id = data[0][0]
        return id

    @db.catch_operationalerrors
    def add_ratings(self, *args):
        """
        feed with:
            media_id, media_type, rating_type, rating, votes

        rating_type = 'default'
        """
        id = self.kodiconn.insert("rating", 
          ("media_id","media_type","rating_type","rating","votes"),
          (args)
        )        
        return id

    @db.catch_operationalerrors
    def remove_ratings(self, kodi_id, kodi_type):
        """
        Removes all ratings from the rating table for the item
        """
        self.kodiconn.delete("rating", 
          "WHERE media_id = '%s' AND media_type = '%s'" % (kodi_id, kodi_type)
        )        

    def new_tvshow_id(self):
        data = self.kodiconn.select("tvshow",("COALESCE(MAX(idShow), 0)",))        
        return data[0][0] + 1

    def new_episode_id(self):
        data = self.kodiconn.select("episode",("COALESCE(MAX(idEpisode), 0)",))        
        return data[0][0] + 1

    @db.catch_operationalerrors
    def add_episode(self, *args):
        self.kodiconn.insert("episode",
            ("idEpisode",
            "idFile",
            "c00",
            "c01",
            "c03",
            "c04",
            "c05",
            "c09",
            "c10",
            "c12",
            "c13",
            "c14",
            "idShow",
            "c15",
            "c16",
            "c18",
            "c19",
            "c20",
            "idSeason",
            "userrating" ),
            (args)
        )        

    @db.catch_operationalerrors
    def update_episode(self, *args):
        args = list(args)
        id = args[len(args)-1]
        del args[len(args)-1]
        self.kodiconn.update("episode",
            (
            "c00",
            "c01",
            "c03",
            "c04",
            "c05",
            "c09",
            "c10",
            "c12",
            "c13",
            "c14",
            "idShow",
            "c15",
            "c16",
            "c18",
            "c19",
            "c20",
            "idSeason",
            "userrating" ),
            (args),        
           "WHERE idEpisode = '%s'" % id
        )

    @db.catch_operationalerrors
    def add_show(self, *args):
        self.kodiconn.insert("tvshow",
           ("idShow",
            "c00",
            "c01",
            "c04",
            "c05",
            "c08",
            "c09",
            "c12",
            "c13",
            "c14",
            "c15"),
            (args)
        )

    @db.catch_operationalerrors
    def update_show(self, *args):
        args = list(args)
        id = args[len(args)-1]        
        del args[len(args)-1]
        self.kodiconn.replace("tvshow",
           (
            "c00",
            "c01",
            "c04",
            "c05",
            "c08",
            "c09",
            "c12",
            "c13",
            "c14",
            "c15"),
            (args),
            "WHERE idShow = '%s'" % (id, )
        )                            

    @db.catch_operationalerrors
    def add_showlinkpath(self, kodi_id, kodi_pathid):
        self.kodiconn.insert("tvshowlinkpath",
          ("idShow", "idPath"),
          (kodi_id, kodi_pathid)
        )

    @db.catch_operationalerrors
    def remove_show(self, kodi_id):
        self.kodiconn.delete('tvshow', "WHERE idShow = '%s'" % (kodi_id,))

    @db.catch_operationalerrors
    def remove_season(self, kodi_id):
        self.kodiconn.delete('seasons', "WHERE idSeason = '%s'" %
                            (kodi_id,))

    @db.catch_operationalerrors
    def remove_episode(self, kodi_id):
        self.kodiconn.delete('episode', "WHERE idEpisode = '%s'" %
                            (kodi_id,))

    def new_movie_id(self):
        data = self.kodiconn.select("movie", ("COALESCE(MAX(idMovie), 0)",))        
        return data[0][0] + 1

    @db.catch_operationalerrors
    def add_movie(self, *args):        
        self.kodiconn.replace("movie",
          (
            "idMovie",
            "idFile",
            "c00",
            "c01",
            "c02",
            "c03",
            "c04",
            "c05",
            "c06",
            "c07",
            "c09",
            "c10",
            "c11",
            "c12",
            "c14",
            "c15",
            "c16",
            "c18",
            "c19",
            "c21",
            "c22",
            "c23",
            "premiered",
            "userrating"),
            (args),
            "WHERE idMovie='%s'" % (str(args[0]),)
        )

                       

    @db.catch_operationalerrors
    def remove_movie(self, kodi_id):
        self.kodiconn.delete("movie", "WHERE idMovie='%s'" % (kodi_id,))        

    @db.catch_operationalerrors
    def update_userrating(self, kodi_id, kodi_type, userrating):
        """
        Updates userrating
        """
        if kodi_type == v.KODI_TYPE_MOVIE:
            table = kodi_type
            identifier = 'idMovie'
        elif kodi_type == v.KODI_TYPE_EPISODE:
            table = kodi_type
            identifier = 'idEpisode'
        elif kodi_type == v.KODI_TYPE_SEASON:
            table = 'seasons'
            identifier = 'idSeason'
        elif kodi_type == v.KODI_TYPE_SHOW:
            table = kodi_type
            identifier = 'idShow'
        self.kodiconn.update(table, ("userrating",), (userrating,),
          "WHERE %s = '%s'" % (identifier, kodi_id)
        )
