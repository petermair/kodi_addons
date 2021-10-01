#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from . import common


class KodiTextureDB(common.KodiDBBase):
    db_kind = 'texture'

    def url_not_yet_cached(self, url):
        """
        Returns True if url has not yet been cached to the Kodi texture cache
        """        
        return not self.artconn.exists("texture", "WHERE url='"+self.artconn.escape(url)+"'"  )
