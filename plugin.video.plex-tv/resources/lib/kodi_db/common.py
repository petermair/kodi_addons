#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
from threading import Lock
import warnings

from .. import db, path_ops

KODIDB_LOCK = Lock()
# Names of tables we generally leave untouched and e.g. don't wipe
UNTOUCHED_TABLES = ('version', 'versiontagscan')


class KodiDBBase(object):
    """
    Kodi database methods used for all types of items
    """
    def __init__(self, texture_db=False, kodiconn=None, artconn=None,
                 lock=False):
        """
        Allows direct use with a connection instead of context mgr
        """
        self._texture_db = texture_db
        self.lock = lock
        self.kodiconn = kodiconn        
        self.artconn = artconn        

    def __enter__(self):
        if self.lock:
            KODIDB_LOCK.acquire()
        self.kodiconn = db.connect(self.db_kind)        
        self.artconn = db.connect('texture') if self._texture_db \
            else None        
        return self

    def __exit__(self, e_typ, e_val, trcbak):
        try:
            if e_typ:
                # re-raise any exception
                return False
            self.kodiconn.commit()
            if self.artconn:
                self.artconn.commit()
        finally:
            self.kodiconn.disconnect()
            if self.artconn:
                self.artconn.disconnect()
            if self.lock:
                KODIDB_LOCK.release()

    def art_urls(self, kodi_id, kodi_type):
        cs = self.kodiconn.select("art",("url",),"WHERE media_id = '%s' AND media_type='%s'",(kodi_id, kodi_type))                 
        return (x[0] for x in
                cs)

    def artwork_generator(self, kodi_type, limit, offset):
        cs = self.kodiconn.select("art",("url",),"WHERE type='%s' LIMIT %s OFFSET %s" % (kodi_type, str(limit), str(offset)))        
        return (x[0] for x in cs)

    def add_artwork(self, artworks, kodi_id, kodi_type):
        """
        Pass in an artworks dict (see PlexAPI) to set an items artwork.
        """
        for kodi_art, url in artworks.iteritems():
            self.add_art(url, kodi_id, kodi_type, kodi_art)

    @db.catch_operationalerrors
    def add_art(self, url, kodi_id, kodi_type, kodi_art):
        """
        Adds or modifies the artwork of kind kodi_art (e.g. 'poster') in the
        Kodi art table for item kodi_id/kodi_type. Will also cache everything
        except actor portraits.
        """
        self.kodiconn.insert("art",("media_id","media_type","type","url"),(kodi_id, kodi_type, kodi_art, url))        

    def modify_artwork(self, artworks, kodi_id, kodi_type):
        """
        Pass in an artworks dict (see PlexAPI) to set an items artwork.
        """
        for kodi_art, url in artworks.iteritems():
            self.modify_art(url, kodi_id, kodi_type, kodi_art)

    @db.catch_operationalerrors
    def modify_art(self, url, kodi_id, kodi_type, kodi_art):
        """
        Adds or modifies the artwork of kind kodi_art (e.g. 'poster') in the
        Kodi art table for item kodi_id/kodi_type. Will also cache everything
        except actor portraits.
        """
        cs = self.kodiconn.select("art",("url",),
          "WHERE media_id = '%s' AND media_type = '%s' AND type = '%s' LIMIT 1" %(kodi_id, kodi_type, kodi_art,))
        
        try:
            old_url = cs[0][0]              
        except:     
            # Update the artwork   
            self.kodiconn.insert("art",("media_id", "media_type", "type", "url"),(kodi_id, kodi_type, kodi_art, url))                     
        else:    
            if url == old_url:
                # Only cache artwork if it changed
                return
            self.delete_cached_artwork(old_url)
            self.kodiconn.update("art",("url",),(url,), 
              "WHERE media_id = '%s' AND media_type = '%s' AND type = '%s'" % (kodi_id, kodi_type, kodi_art))

    def delete_artwork(self, kodi_id, kodi_type):        
        rows = self.kodiconn.select("art",("url",), "WHERE media_id = '%s' AND media_type = '%s'" % (kodi_id, kodi_type))                
        for row in rows:
            self.delete_cached_artwork(row[0])

    @db.catch_operationalerrors
    def delete_cached_artwork(self, url):
        if self.artconn.exists("texture","WHERE url = '%s' LIMIT 1" % (self.artconn.escape(url),)):
            urls = self.artconn.select("texture",("url",),"WHERE url = '%s' LIMIT 1" % (self.artconn.escape(url),))
            cachedurl = urls[0][0]
            # Delete thumbnail as well as the entry
            path = path_ops.translate_path("special://thumbnails/%s"
                                           % cachedurl)
            if path_ops.exists(path):
                path_ops.rmtree(path, ignore_errors=True)
            self.artconn.delete("texture","WHERE url = '%s'" % (self.artconn.escape(url),))           

    @db.catch_operationalerrors
    def wipe(self):
        """
        Completely wipes the corresponding Kodi database
        """
        
        ex = self.kodiconn.TableList()
                  
        tables = [i[0] for i in ex]
        for table in UNTOUCHED_TABLES:
            if table in tables:
                tables.remove(table)
        for table in tables:
            self.kodiconn.delete(table,"")            
