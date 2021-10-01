# Kodi Addons for Plex, Amazon Prime and Disney+ 

This repo for Kodi Media Center contains modified versions of the [PlexKodiConnect](https://github.com/croneter/PlexKodiConnect), [Amazon VOD](https://github.com/Sandmann79/xbmc) and [Disney+ addons](https://github.com/matthuisman/slyguy.addons/), with support for SQLite3 and MySQL-Databases

Widevine DRM protected streams are reproduced via `InputStream.Adaptive` henceforth referred to as IS.A.

## Disclaimer
This addon is not officially commissioned or supported by Amazon, Plex or Disney, nor are authors associated with it. 


## Features
* Amazon Prime Video Addon for Kodi Media Center
* Disney+ Video Addon  for Kodi Media Center
* Plex Addon for Kodi Media Center


## Setup instructions
* install the repository as described in [these instructions](https://github.com/PeterMair/kodi_addons/blob/master/xbmc/README.md)
* install **Plex, Amazon Prime and Disney+** video addon from MairPeter Repository

## Playback methods
Several playback methods are supported, although `InputStream.Adaptive` is the default since Kodi 18 Leia.

### InputStream.Adaptive
Uses the Inputstream interface with the internal Kodi player, which is available since Kodi 17, to playback Widevine encrypted video streams.
