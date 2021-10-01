# -*- coding: utf-8 -*-
# We need this in order to use add-on paths like
# 'plugin://plugin.video.plex-tv.MOVIES' in the Kodi video database
###############################################################################
from __future__ import absolute_import, division, unicode_literals
from logging import getLogger
import sys
import os

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

# Import from the main pkc add-on
__addon__ = xbmcaddon.Addon(id='plugin.video.plex-tv')
__temp_path__ = os.path.join(__addon__.getAddonInfo('path').decode('utf-8'), 'resources', 'lib')
__base__ = xbmc.translatePath(__temp_path__.encode('utf-8')).decode('utf-8')
sys.path.append(__base__)

import transfer, loghandler
from tools import unicode_paths

###############################################################################
loghandler.config()
LOG = getLogger('PLEX.TVSHOWS')
###############################################################################

HANDLE = int(sys.argv[1])


def play():
    """
    Start up playback_starter in main Python thread
    """
    LOG.debug('Full sys.sys.argv received: %s', sys.argv)
    # Put the request into the 'queue'
    if not sys.argv[2]:
        # Browsing to a tv show from a tv show info dialog - picked up
        # by kodimonitor.py and its method OnAdd
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    else:
        request = '%s&handle=%s' % (unicode_paths.decode(sys.argv[2]), HANDLE)
        if b'resume:true' in sys.argv:
            request += '&resume=1'
        elif b'resume:false' in sys.argv:
            request += '&resume=0'
        transfer.plex_command('PLAY-%s' % request)
    if HANDLE == -1:
        # Handle -1 received, not waiting for main thread
        return
    # Wait for the result
    result = transfer.wait_for_transfer(source='main')
    if result is True:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        # Tell main thread that we're done
        transfer.send(True, target='main')
    else:
        xbmcplugin.setResolvedUrl(HANDLE, True, result)


if __name__ == '__main__':
    LOG.info('PKC add-on for tv shows started')
    play()
    LOG.info('PKC add-on for tv shows stopped')
