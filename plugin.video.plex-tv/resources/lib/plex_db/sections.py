#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals


class Sections(object):
    def all_sections(self):
        """
        Returns an iterator for all sections
        """
        data = self.plexconn.select("sections",("*",))        
        return (self.entry_to_section(x) for x in data)

    def section(self, section_id):
        """
        For section_id, returns the dict
            section_id INTEGER PRIMARY KEY,
            section_name TEXT,
            plex_type TEXT,
            kodi_tagid INTEGER,
            sync_to_kodi BOOL,
            last_sync INTEGER
        """
        data = self.plexconn.select("sections",("*", ),"WHERE section_id=%s LIMIT 1" % (section_id))        
        if len(data)>0:
          return self.entry_to_section(data[0])
        else:
          return

    @staticmethod
    def entry_to_section(entry):
        if not entry:
            return
        return {
            'section_id': entry[0],
            'section_name': entry[1],
            'plex_type': entry[2],
            'kodi_tagid': entry[3],
            'sync_to_kodi': entry[4] == 1,
            'last_sync': entry[5]
        }

    def section_id_by_name(self, section_name):
        """
        Returns the section_id for section_name (or None)
        """
        data = self.plexconn.select("sections",("section_id",),"WHERE section_name = '%s' LIMIT 1" % (section_name,))        
        try:
            return data[0][0]
        except:
            pass

    def add_section(self, section_id, section_name, plex_type, kodi_tagid,
                    sync_to_kodi, last_sync):
        """
        Appends a Plex section to the Plex sections table
        sync=False: Plex library won't be synced to Kodi
        """
        self.plexconn.replace("sections",
           ("section_id",
            "section_name",
            "plex_type",
            "kodi_tagid",
            "sync_to_kodi",
            "last_sync"),
           (section_id,
            section_name,
            plex_type,
            kodi_tagid,
            sync_to_kodi,
            last_sync),
            "WHERE section_id = %s" % (section_id, )
        )        

    def update_section(self, section_id, section_name):
        """
        Updates the section with section_id
        """
        self.plexconn.update("sections", 
          ("section_name", ),
          (section_name, ),
          "WHERE section_id = %s" % (section_id,)
        )
        

    def remove_section(self, section_id):
        """
        Removes the Plex db entry for the section with section_id
        """
        self.plexconn.delete("sections", "WHERE section_id=%s" % (section_id,))

    def update_section_sync(self, section_id, sync_to_kodi):
        """
        Updates whether we should sync sections_id (sync=True) or not
        """
        if sync_to_kodi:
            self.plexconn.update("sections",
              ("sync_to_kodi", )
              (sync_to_kodi),
              "WHERE section_id = %s" % (section_id,)
            )
        else:
            # Set last_sync = 0 in order to force a full sync if reactivated
            self.plexconn.update("sections",
              ("sync_to_kodi", "last_sync")
              (sync_to_kodi, 0),
              "WHERE section_id = %s" % (section_id,)
            )            

    def update_section_last_sync(self, section_id, last_sync):
        """
        Updates the timestamp for the section        
        """
        self.plexconn.update("sections", ("last_sync",), (last_sync,),
          "WHERE section_id=%s" % (section_id, ))        

    def force_full_sync(self):
        """
        Sets the last_sync flag to 0 for every section
        """
        self.plexconn.update("sections", ("last_sync", ), (0, ))
