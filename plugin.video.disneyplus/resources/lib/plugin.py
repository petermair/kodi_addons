# coding=utf-8

from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.log import log
from slyguy.exceptions import PluginError
from slyguy.constants import KODI_VERSION
from slyguy.drm import is_wv_secure
import xbmcgui

from .api import API
from .constants import *
from .language import _

import time
from xbmcaddon import Addon

import warnings
import json
api = API()

SYNC_COLLECTION_MINUTES = 7 * 24 * 60
SYNC_SET_MINUTES = 7 * 24 * 60
SYNC_SERIES_MINUTES = 7 * 24 * 60
SYNC_SEASON_MINUTES = 1 * 24 * 60 
SYNC_MOVIE_MINUTES = 1 * 24 * 60

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in
    InitialDBSetup()

@plugin.route('')
def index(**kwargs):
    
    if not api.logged_in:
        folder = plugin.Folder(cacheToDisc=False)
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
        folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)
        return folder
    else:
        db = api.db
        
        data = db.select("folderhierarchy h", ("h.foldersid", "h.parentid"), "WHERE h.parentid = '%s' AND h.profileid='%s' ORDER BY ordernr" % (DB_ZERO,userdata.get('profile_id')))       
        if len(data)==0:            
            InitialSync()                        

        return showfolder(DB_ZERO, DB_ZERO)


    

def db_addFolder(id, parentid, type, slug, contentclass, title, ordernr):
    db = api.db
    db.replace("folders", 
        ("id", "type", "slug", "contentclass", "title"),              
        (id, type, slug, contentclass, title), 
        "WHERE id='"+id+"'"
    )
    db.replace("folderhierarchy",
      ("foldersid", "parentid","profileid","ordernr","active"),
      (id, parentid, userdata.get('profile_id'), ordernr,1),
      "WHERE foldersid='"+id+"' AND parentid='"+parentid+"' AND profileid='"+userdata.get('profile_id')+"'"
    )

def db_FolderSync(id, parentid, lastsync, syncminutes):
    db = api.db
    db.replace("folders",
      ("lastsync","syncminutes"),
      (lastsync, syncminutes),
      "WHERE id='"+id+"'"
    )
    
def InitialDBSetup():
    ADDON_VERSION = Addon().getAddonInfo('version')
    dbversion = 1
    api.db.beginTransaction
    api.db.createTable(
        "version",
        (
            {"fieldname": "version",   "fieldtype": "varchar", "fieldsize": 20, "notnull": True},            
            {"fieldname": "dbversion", "fieldtype": "varchar", "fieldsize": 20, "notnull": False},
        ),
        ("version",)
    )
    v = api.db.select("version",("MAX(dbversion)",))
    if len(v)>0:
        dbversion = v[0][0]
    if dbversion == None:
        dbversion = 1    

    api.db.createTable(
        "art",
        (
            {"fieldname": "mediaid", "fieldtype": "varchar", "fieldsize":  40, "notnull": True},            
            {"fieldname": "arttype", "fieldtype": "varchar", "fieldsize":  36, "notnull": True},
            {"fieldname": "url",     "fieldtype": "varchar", "fieldsize": 250, "notnull": True},
        ),
        ("mediaid","arttype")
    )
    
    api.db.createTable(
        "episodes",
        (
            {"fieldname": "id",        "fieldtype": "varchar", "fieldsize": 40, "notnull": True},            
            {"fieldname": "seasonsid", "fieldtype": "varchar", "fieldsize": 36, "notnull": True},
            {"fieldname": "season",    "fieldtype": "int",     "fieldsize": 11, "notnull": True},
            {"fieldname": "episode",   "fieldtype": "int",     "fieldsize": 11, "notnull": True},
        ),
        ("id",)
    )

    if int(dbversion)<2: ##
        api.db.execute("DROP TABLE IF EXISTS folderhierarchy")

    api.db.createTable(
        "folderhierarchy",
        (
            {"fieldname": "foldersid","fieldtype": "varchar", "fieldsize": 40, "notnull": True},                       
            {"fieldname": "parentid", "fieldtype": "varchar", "fieldsize": 40, "notnull": True},
            {"fieldname": "profileid", "fieldtype": "varchar", "fieldsize": 40, "notnull": True},
            {"fieldname": "ordernr",  "fieldtype": "int",     "fieldsize": 11, "notnull": True},   
            {"fieldname": "active",   "fieldtype": "int",     "fieldsize":  11, "notnull": False},                     
        ),
        ("foldersid","parentid","profileid")
    )

    api.db.createTable(
        "folders",
        (
            {"fieldname": "id",           "fieldtype": "varchar", "fieldsize":  40, "notnull": True},            
            {"fieldname": "type",         "fieldtype": "varchar", "fieldsize":  36, "notnull": True},
            {"fieldname": "slug",         "fieldtype": "varchar", "fieldsize":  50, "notnull": True},
            {"fieldname": "contentclass","fieldtype": "varchar", "fieldsize":   50, "notnull": True},
            {"fieldname": "title",        "fieldtype": "varchar", "fieldsize": 200, "notnull": True},
            {"fieldname": "lastsync",     "fieldtype": "bigint",  "fieldsize":  20, "notnull": False},
            {"fieldname": "syncminutes",  "fieldtype": "int",     "fieldsize":  11, "notnull": False},            
        ),
        ("id",)
    )

    api.db.createTable(
        "movies",
        (
            {"fieldname": "id",              "fieldtype": "varchar", "fieldsize":  40, "notnull": True},            
            {"fieldname": "title",           "fieldtype": "varchar", "fieldsize": 206, "notnull": True},
            {"fieldname": "plot",            "fieldtype": "longtext","fieldsize":   0, "notnull": False},
            {"fieldname": "mediatype",       "fieldtype": "varchar", "fieldsize":  50, "notnull": True},
            {"fieldname": "duration",        "fieldtype": "int",     "fieldsize": 200, "notnull": False},
            {"fieldname": "releasedate",     "fieldtype": "varchar", "fieldsize":  20, "notnull": False},
            {"fieldname": "releaseyear",     "fieldtype": "int",     "fieldsize":  11, "notnull": False},
            {"fieldname": "url",             "fieldtype": "varchar", "fieldsize": 250, "notnull": False},
            {"fieldname": "encodedfamilyid", "fieldtype": "varchar", "fieldsize":  40, "notnull": False},
        ),
        ("id", )
    )

    api.db.createTable(
        "seasons",
        (
            {"fieldname": "id",                   "fieldtype": "varchar", "fieldsize":  40, "notnull": True},            
            {"fieldname": "seriesid",             "fieldtype": "varchar", "fieldsize":  36, "notnull": True},
            {"fieldname": "title",                "fieldtype": "varchar", "fieldsize": 200, "notnull": True},
            {"fieldname": "seasonsequencenumber", "fieldtype": "int",     "fieldsize":  11, "notnull": True},
            {"fieldname": "plot",                 "fieldtype": "longtext","fieldsize":   0, "notnull": False},
            {"fieldname": "mediatype",            "fieldtype": "varchar", "fieldsize":  50, "notnull": True},
            {"fieldname": "releaseyear",          "fieldtype": "int",     "fieldsize":  11, "notnull": False},
            {"fieldname": "releasedate",          "fieldtype": "varchar", "fieldsize":  20, "notnull": False},            
        ),
        ("id", )
    )

    api.db.createTable(
        "series",
        (
            {"fieldname": "id",                   "fieldtype": "varchar", "fieldsize":  40, "notnull": True},                        
            {"fieldname": "title",                "fieldtype": "varchar", "fieldsize": 200, "notnull": True},
            {"fieldname": "encodedseriesid",      "fieldtype": "varchar", "fieldsize":  50, "notnull": True},
            {"fieldname": "plot",                 "fieldtype": "longtext","fieldsize":   0, "notnull": False},
            {"fieldname": "mediatype",            "fieldtype": "varchar", "fieldsize":  50, "notnull": True},
            {"fieldname": "releaseyear",          "fieldtype": "int",     "fieldsize":  11, "notnull": False},
            {"fieldname": "releasedate",          "fieldtype": "varchar", "fieldsize":  20, "notnull": False},            
        ),
        ("id", )
    )

    api.db.replace("version",("version","dbversion"),(ADDON_VERSION, '2'),"WHERE version='%s'" % ADDON_VERSION)
    
    api.db.commit

@plugin.route()
def InitialSync(**kwargs):    
    db = api.db
    db.beginTransaction()
    _dialog = xbmcgui.DialogProgress()
    _dialog.create(heading="Synchronize...", line1="Initializing Disney Plus...")
    db_addFolder(DB_ZERO, DB_ZERO, 'none', '', '', 'Disney Plus', 0)
    synccollection(folderid=DB_ZERO, parentid=DB_ZERO, slug='home', content_class='home', label=_.FEATURED, fullSync=True, ordernr=1, dialog=_dialog)
    db.commit()
    db.beginTransaction()
    syncsets(folderid=HUBS_SET_ID, parentid=DB_ZERO, set_id=HUBS_SET_ID, set_type=HUBS_SET_TYPE, fullSync=True, ordernr=2, dialog=_dialog)
    db.commit()
    db.beginTransaction()
    synccollection(folderid=DB_ZERO, parentid=DB_ZERO, slug='movies', content_class='contentType', label=_.MOVIES, fullSync=True, ordernr=3, dialog=_dialog)
    db.commit()
    db.beginTransaction()
    synccollection(folderid=DB_ZERO, parentid=DB_ZERO, slug='series', content_class='contentType', label=_.SERIES, fullSync=True, ordernr=4, dialog=_dialog)
    db.commit()
    db.beginTransaction()
    synccollection(folderid=DB_ZERO, parentid=DB_ZERO, slug='originals', content_class='originals', label=_.ORIGINALS, fullSync=True, ordernr=5, dialog=_dialog)
    db.commit()
    db.beginTransaction()
    syncsets(folderid=WATCHLIST_SET_ID, parentid=DB_ZERO, set_id=WATCHLIST_SET_ID, set_type=WATCHLIST_SET_TYPE, fullSync=True, odernr=6, dialog=_dialog)    
    db.commit()
    db.beginTransaction()
    syncsets(folderid=CONTINUE_WATCHING_SET_ID, parentid=DB_ZERO, set_id=CONTINUE_WATCHING_SET_ID, set_type=CONTINUE_WATCHING_SET_TYPE, fullSync=True, odernr=7, dialog=_dialog)    
    _dialog.close
    db.commit()

@plugin.route()
def SyncManually(folderid, parentid,**kwargs):
    
    db = api.db    
    
    rows = db.select("folderhierarchy h INNER JOIN folders f ON f.id=h.foldersid", ("f.type","f.slug","f.contentclass","f.title","h.ordernr"),"WHERE h.foldersid='%s' AND h.parentid='%s' AND h.profileid='%s'" % (folderid, parentid, userdata.get('profile_id')))
    db.beginTransaction()
    for data in rows:
        _dialog = xbmcgui.DialogProgress()
        _dialog.create(heading="Synchronize...", line1=data[3])
        if data[0] == "CuratedSet":            
            syncsets(folderid=folderid, parentid=parentid, set_id=folderid, set_type=data[2], fullSync=True, ordernr=data[4], dialog=_dialog)
        if (data[0] == "StandardCollection") or (data[0]=="PersonalizedCollection"):
            synccollection(folderid=folderid, parentid=parentid, slug=data[1], content_class=data[2], label=data[3], fullSync=True, ordernr = data[4], dialog=_dialog)            
        if (data[0] == "DmcSeries"):
            sync_series(folderid, folderid, fullSync="True")
        _dialog.close()
    db.commit()    

def synccollection(folderid, parentid, slug, content_class, label=None, fullSync=False, ordernr=1, collectionid=DB_ZERO, dialog=None, **kwargs):    
    db = api.db    
    ordernr = int(ordernr)    
    fullSync = (str(fullSync)=="True")    
    dosync = fullSync or (folderid == DB_ZERO)
    dt = time.time()
    dt = int(dt)    
    if dosync == False:        
        parent = db.select("folders", ("id","lastsync","syncminutes"), "WHERE id='%s'" % folderid)
        dosync = (len(parent) == 0)
        for p in parent:            
            if (int(p[1] or 0)+int(p[2] or 0)*60<dt):
                dosync = True    
    if dosync == True:            
        type = 'PersonalizedCollection' if slug == 'home' else 'StandardCollection'
        data = api.collection_by_slug(slug, content_class, type)                    

        folderid = data["collectionId"]        
        label = label or _get_text(data['text'], 'title', 'collection')
        if fullSync==False:
            db.beginTransaction()
                
        db.update("folderhierarchy",("active",),(0,),"WHERE foldersid IN (SELECT id FROM folders WHERE slug='%s') AND parentid='%s' AND profileid='%s'" % (slug, parentid,userdata.get('profile_id')))
        db_addFolder(folderid, parentid, type, slug, content_class, label, ordernr)
        db_FolderSync(folderid, parentid, dt,SYNC_COLLECTION_MINUTES)
        
        db_saveart(folderid, data.get('image', []))        
        o = 0
        for row in data['containers']:
            o = o + 1
            _type = row.get('type')
            _set = row.get('set')
            _style = row.get('style')
            ref_type = _set['refType'] if _set['type'] == 'SetRef' else _set['type']

            if _set.get('refIdType') == 'setId':
                set_id = _set['refId']
                type = "CuratedSet"
            else:
                set_id = _set.get('setId')
                type="CuratedSet"

            ##if not set_id:
            ##    return None

            if slug == 'home' and _style in ('brandSix', 'ContinueWatchingSet', 'hero', 'WatchlistSet'):
                continue

            if _style == 'BecauseYouSet':
                continue
                # data = api.set_by_id(set_id, _style, page_size=0)
                # if not data['meta']['hits']:
                #     continue
                # title = _get_text(data['text'], 'title', 'set')
            else:
                title = _get_text(_set['text'], 'title', 'set')   
            if not(dialog==None):
                try:
                    dialog.update(100 * o / len(data), line1=title)
                except: ## Kodi v.19
                    dialog.update(100 * o / len(data), message=title)
            db_addFolder(set_id, folderid, type, "", ref_type, title, o)                                    
            if fullSync == True:
                syncsets(set_id, folderid, set_id, ref_type, 1, fullSync=True, ordernr=0)
        if fullSync == False:
            db.commit()


@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username, password)
    _select_profile()
    gui.refresh()

@plugin.route()
def hubs(**kwargs):
    folder = plugin.Folder(_.HUBS)

    data = api.collection_by_slug('home', 'home', 'StandardCollection')
    for row in data['containers']:
        _style = row.get('style')
        _set = row.get('set')
        if _set and _style == 'brandSix':
            items = _process_rows(_set.get('items', []), 'brand')
            folder.add_items(items)

    return folder

@plugin.route()
def select_profile(**kwargs):
    if userdata.get('kid_lockdown', False):
        return

    _select_profile()
    gui.refresh()

def _avatars(ids):
    avatars = {}

    data = api.avatar_by_id(ids)
    for row in data['avatars']:
        avatars[row['avatarId']] = row['image']['tile']['1.00']['avatar']['default']['url'] + '/scale?width=300'

    return avatars

def _select_profile():
    account = api.account()['account']
    profiles = account['profiles']
    avatars = _avatars([x['attributes']['avatar']['id'] for x in profiles])

    options = []
    values = []
    default = -1

    for index, profile in enumerate(profiles):
        values.append(profile)
        profile['_avatar'] = avatars.get(profile['attributes']['avatar']['id'])

        if profile['attributes']['parentalControls']['isPinProtected']:
            label = _(_.PROFILE_WITH_PIN, name=profile['name'])
        else:
            label = profile['name']

        options.append(plugin.Item(label=label, art={'thumb': profile['_avatar']}))

        if account['activeProfile'] and profile['id'] == account['activeProfile']['id']:
            default = index
            userdata.set('avatar', profile['_avatar'])
            userdata.set('profile', profile['name'])
            userdata.set('profile_id', profile['id'])

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    _switch_profile(values[index])

def _switch_profile(profile):
    pin = None
    if profile['attributes']['parentalControls']['isPinProtected']:
        pin = gui.input(_.ENTER_PIN, hide_input=True).strip()

    api.switch_profile(profile['id'], pin=pin)

    if settings.getBool('kid_lockdown', False) and profile['attributes']['kidsModeEnabled']:
        userdata.set('kid_lockdown', True)

    userdata.set('avatar', profile['_avatar'])
    userdata.set('profile', profile['name'])
    userdata.set('profile_id', profile['id'])
    gui.notification(_.PROFILE_ACTIVATED, heading=profile['name'], icon=profile['_avatar'])



def syncsets(folderid, parentid, set_id, set_type, page=1, fullSync = False, ordernr=1, dialog=None, **kwargs):
    page = int(page)
    db = api.db    
    fullSync = (str(fullSync)=="True")
    dosync = fullSync or (page>1)
    dt = time.time()
    dt = int(dt)    
    parent = db.select("folders f INNER JOIN folderhierarchy h ON f.id=h.parentid AND h.profileid='"+userdata.get('profile_id')+"'", ("f.id","f.lastsync","f.syncminutes"), "WHERE id='"+folderid+"' LIMIT 1")
    if dosync == False:                        
        dosync = len(parent) == 0
        for p in parent:
            if (int(p[1] or 0)+int(p[2] or 0)*60<dt):
                dosync = True  
    if (dosync == True):           
        
        data = api.set_by_id(set_id, set_type, page=page)    
                
        if fullSync == False:            
            db.beginTransaction()        
            
        
        
        title = _get_text(data['text'], 'title', 'set')        
        if set_id == CONTINUE_WATCHING_SET_ID:
            refresh = 0 ## Always refresh            
        elif set_type=="WatchlistSet":
            refresh = SYNC_SET_MINUTES
        else:
            shouldRefresh = data["shouldRefresh"]                        
            folderid = data["setId"]   
            if str(shouldRefresh)=="true":
                refresh = SYNC_MOVIE_MINUTES            
            else:
                refresh = SYNC_SET_MINUTES                

        
        
        if not(dialog == None):
            try:
                dialog.update(50, line1=title)
            except: ## Kodi v.19
                dialog.update(50, message=title)

        if data['meta']['offset'] == 0:
            db.update("folderhierarchy",("active",),(0,),"WHERE parentid='%s' AND profileid='%s'" % (folderid,userdata.get('profile_id')))
        
        db_addFolder(folderid, parentid, "CuratedSet", "", set_type,title, ordernr)
        db_FolderSync(folderid, parentid, dt, refresh)
        
        if fullSync == False:
            db.commit()                        
        ordernr = ordernr + 1
        _process_rows(folderid, parentid, data.get('items', []), data['type'], fullSync=fullSync)
        if set_id == CONTINUE_WATCHING_SET_ID:
            pass
        elif (data['meta']['page_size'] + data['meta']['offset']) < data['meta']['hits']:
            syncsets(folderid, parentid, set_id, set_type, page=page+1, fullSync=fullSync, ordernr = ordernr, dialog=dialog)        
    


def dbart(id):
    art = {}
    data =api.db.select("art", ("arttype", "url"), "WHERE mediaid='%s'" % id)
    for a in data:
        art[a[0]] = a[1]
    return art


@plugin.route()
def showfolder(folderid=DB_ZERO, parentid=DB_ZERO, **kwargs):
    ##
    sync_enabled = settings.getBool('sync_playback', True)
    watchlist_enabled = settings.getBool('sync_watchlist', True)
    title = "Disney+"

    db = api.db

    data = db.select("folderhierarchy h INNER JOIN folders f ON f.id=h.foldersid LEFT JOIN art ON f.id=art.mediaid AND art.arttype='fanart'",
            ("f.id", "f.type", "f.slug", "f.contentclass", "f.title","art.url", "h.ordernr"),
            "WHERE h.foldersid='%s' AND h.parentid='%s' AND h.profileid='%s' LIMIT 1" % (folderid, parentid,userdata.get('profile_id')) 
            )
    for parentdata in data:    
        id = parentdata[0]
        type = parentdata[1]
        slug = parentdata[2]
        content_class = parentdata[3]
        title = parentdata[4]
        ordernr = int(parentdata[6])
        if (type == 'CuratedSet'):
            syncsets(id, parentid, id, content_class, page=1, fullSync="False", ordernr =ordernr)
        elif type == 'StandardCollection':
            synccollection(folderid, parentid, slug, content_class, title, fullSync="False", ordernr =ordernr)  
        elif type =='DmcSeries':            
            sync_series(folderid, id, fullSync = "False")

    folder = plugin.Folder(title)

    
    data = db.select("folderhierarchy h INNER JOIN folders f ON h.foldersid=f.id",
       ("f.id", "f.title", "f.type", "f.slug", "f.contentclass", "h.parentid"),
       "WHERE h.parentid='%s' AND h.foldersid!=h.parentid AND h.active=1 AND h.profileid='%s' ORDER BY h.ordernr" % (folderid,userdata.get('profile_id'))
    )

    for row in data:        
        content_type = row[2]
        ##content_class = row[4]
        if (row[2]=='DmcVideo'): 
            movies = db.select("movies",("plot","duration","releaseyear","releasedate","mediatype","encodedfamilyid"),"WHERE id='%s'" % row[0])
            for movie in movies:
                item = folder.add_item(
                    label = row[1],
                    path = _get_play_path(row[0]),
                    art = dbart(row[0]),
                    info =  {
                        'plot': movie[0],
                        'duration': movie[1]/1000,
                        'year': movie[2],
                        'aired': movie[3] or movie[2],                    
                        'mediatype': 'movie',                                                
                    },                    
                    playable = True
                )
                item.context.append((_.FULL_DETAILS, 'RunPlugin({})'.format(plugin.url_for(full_details, family_id=movie[5]))),),
        elif (row[2]=='DmcSeries'):
            _series = db.select("series",("plot","releaseyear","releasedate","mediatype","encodedseriesid"),"WHERE id='%s'" % row[0])
            item = folder.add_item(
                    label = row[1],
                    art = dbart(row[0]),                    
                    context = (("Load Series", 'RunPlugin({})'.format(plugin.url_for(SyncManually, folderid=row[0], parentid=row[5] ))),),                    
                    path = plugin.url_for(showfolder, folderid=row[0], parentid=row[5]),
                )
            for serie in _series:
                item.info.update({
                        'plot': serie[0],
                        'year': serie[1],
                        'mediatype': 'tvshow',
                    })
               
        elif (row[2]=='DmcSeason'):
            _seasons = db.select("seasons s INNER JOIN series se ON se.id = s.seriesid",("s.plot","s.releaseyear","s.releasedate","s.mediatype","s.seasonsequencenumber","se.title"),"WHERE s.id='%s'" % row[0])
            for season in _seasons:
                item = folder.add_item(
                    label = row[1],
                    info  = {
                        'plot': season[0],
                        'year': season[1],
                        'season': season[4],
                        'mediatype': 'season',
                        "tvshowtitle": season[5]
                    },
                    art   = dbart(row[0]),
                    path  = plugin.url_for(showfolder, folderid=row[0], parentid=row[5]),
                )
        elif (row[2] == 'DmcEpisode'):
            movies = db.select("""movies m LEFT JOIN episodes e ON m.id=e.id 
              INNER JOIN seasons s ON s.id=e.seasonsid 
              INNER JOIN series se ON se.id = s.seriesid""",("m.plot","m.duration","m.releaseyear","m.releasedate","m.mediatype", "e.season", "e.episode", "se.title"),"WHERE m.id='%s'" % row[0])
            for movie in movies:
                item = folder.add_item(
                    label = row[1],
                    info  = {
                        'plot': movie[0],
                        'duration': movie[1]/1000,
                        'year': movie[2],
                        'aired': movie[3] or movie[2],                    
                        'mediatype': 'episode',
                        'season': movie[5],
                        'episode': movie[6],
                        "tvshowtitle": movie[7]
                    },
                    art  = dbart(row[0]),
                    path = _get_play_path(row[0]),
                    playable = True,
                )
        else:
            item = folder.add_item(
                label = row[1],
                art = dbart(row[0]),
                path = plugin.url_for(showfolder, folderid=row[0], parentid=row[5]),
                context = (("Synchronize", 'RunPlugin({})'.format(plugin.url_for(SyncManually, folderid=row[0], parentid=row[5] ))),),
            )            
        if watchlist_enabled:            
            if content_class == "WatchlistSet":
                item.context.append((_.DELETE_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(delete_watchlist, content_id=row[0]))))
            elif (content_type == 'DmcSeries') or (content_type == 'DmcVideo'):
                item.context.append((_.ADD_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(add_watchlist, content_id=row[0], title=item.label))))
    if folderid == DB_ZERO:
        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if not userdata.get('kid_lockdown', False):
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': userdata.get('avatar')}, info={'plot': userdata.get('profile')}, _kiosk=False, bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)        
    return folder


def _process_rows(folderid, parentid, rows, content_class=None,fullSync = False):
    db = api.db
    

    fullSync = (str(fullSync)=="True")

    items = []

    ordernr = 0
    

    

    for row in rows:
        item = None
        content_type = row.get('type')
        ordernr = ordernr + 1
        dt = time.time()
        dt = int(dt)
        id = ""
        if content_type == 'DmcVideo':
            id = row["contentId"]
            program_type = row.get('programType')            
            title = _get_text(row['text'], 'title', 'program')
            type = 'DmcVideo'
            if program_type == 'episode':
                if content_class in ('episode', CONTINUE_WATCHING_SET_TYPE):
                    type = 'DmcEpisode'
                    item = sync_video(row, fullSync)                    
                else:
                    item = sync_video(row, fullSync)                    
                    ##type = 'DmcSeries'
            else:
                item = sync_video(row, fullSync)

        elif content_type == 'DmcSeries':
            id = row["seriesId"]
            item = _parse_series(row, fullSync)
            title = _get_text(row['text'], 'title', 'series')
            type = 'DmcSeries'
            minutes = 60 * 24
        elif content_type in ('PersonalizedCollection', 'StandardCollection'):
            id = row["collectionId"]
            item = _parse_collection(row, folderid, ordernr, fullSync)
            title = _get_text(row['text'], 'title', 'collection')
            type = content_type
            minutes = 7 * 60 * 24
    
        
        if  (id!="") and not(content_type in ('PersonalizedCollection', 'StandardCollection')):
            if fullSync == False:
                db.beginTransaction()

            db_addFolder(id, folderid, type, "", "StandardCollection", title, ordernr)
            db_FolderSync(id, folderid,SYNC_COLLECTION_MINUTES, dt)
            
            if fullSync == False:
                db.commit()
    
        if not item:
            continue



        items.append(item)

    return items

@plugin.route()
def add_watchlist(content_id, title=None, icon=None, **kwargs):
    api.db.beginTransaction
    db_FolderSync(WATCHLIST_SET_ID, DB_ZERO, 0,0)
    api.db.commit
    gui.notification(_.ADDED_WATCHLIST, heading=title, icon=icon)
    api.add_watchlist(content_id)

@plugin.route()
def delete_watchlist(content_id, **kwargs):
    api.delete_watchlist(content_id)
    api.db.beginTransaction
    db_FolderSync(WATCHLIST_SET_ID, DB_ZERO, 0,0)
    api.db.commit
    gui.refresh()

def _parse_collection(row, parentid, ordernr, fullSync):
    db = api.db    
    fullSync = (str(fullSync)=='True')
    
    if fullSync == False:
        db.beginTransaction()    

    dt = time.time()
    dt = int(dt)

    set_id= row["collectionId"]
    title = _get_text(row['text'], 'title', 'collection')
    slug=row['collectionGroup']['slugs'][0]['value'] 
    content_class=row['collectionGroup']['contentClass']
    db_saveart(set_id, row['image'])
    
    db_addFolder(set_id, parentid, "StandardCollection", slug, content_class, title, ordernr)

    

    if fullSync == False:
        db.commit()      

def _get_play_path(content_id):
    if not content_id:
        return None

    kwargs = {
        'content_id': content_id,
    }

    profile_id = userdata.get('profile_id')
    if profile_id:
        kwargs['profile_id'] = profile_id

    if settings.getBool('sync_playback', False):
        kwargs['_noresume'] = True

    return plugin.url_for(play, **kwargs)

def _parse_series(row, fullSync=False, parentid=DB_ZERO):
    db = api.db
    fullSync = (str(fullSync)=='True')
    title = _get_text(row['text'], 'title', 'series')
    if fullSync == False:
        db.beginTransaction()     

    dt = time.time()
    dt = int(dt)



    db.replace("series",
        ("id","title", "plot","mediatype","releaseyear","encodedseriesid"),
        (row['seriesId'], title, 
        _get_text(row['text'], 'description', 'series'),
        "tvshow", row['releases'][0]['releaseYear'],row['encodedSeriesId']
        ),
        "WHERE id='"+row['seriesId']+"'"
    )  
    db_saveart(row["seriesId"], row.get('image'))   
     

    if fullSync == False:
        db.commit()
    

def _parse_season(row, series, fullSync=False):
    
    title = _(_.SEASON, season=row['seasonSequenceNumber'])

    db = api.db

    fullSync = (str(fullSync)=='True')
    if fullSync == False:
        db.beginTransaction()     

    dt = time.time()
    dt = int(dt)

    db_addFolder(row["seasonId"],series["seriesId"],row["type"],"",row["seriesType"],title, row['seasonSequenceNumber'])
    db_FolderSync(row["seasonId"],series["seriesId"],SYNC_SEASON_MINUTES, dt)

    db.replace("seasons",
        ("id","seriesid","title","seasonsequencenumber", "plot","mediatype", "releasedate","releaseyear"),
        (row['seasonId'], series['seriesId'], title, row['seasonSequenceNumber'],
            _get_text(row['text'], 'description', 'season') or _get_text(series['text'], 'description', 'series'),
            "season", None, row['releases'][0]['releaseYear']            
        ),
        "WHERE id='"+row['seasonId']+"'"
    )  
    db_saveart(row["seasonId"], row.get('image') or series['image'])       

    if fullSync == False:
        db.commit()


def sync_video(row, fullSync = "False"):
    db = api.db

    fullSync = (str(fullSync)=='True')
    if fullSync == False:
        db.beginTransaction()     

    dt = time.time()
    dt = int(dt)
    title = _get_text(row['text'], 'title', 'program')
    if row['programType'] == 'episode':
        db_addFolder(row['contentId'],row['seasonId'],row["type"],'',row["programType"],title,row['episodeSequenceNumber'])
        db_FolderSync(row['contentId'],row['seasonId'],dt, SYNC_MOVIE_MINUTES)        

    db.replace("movies",
        ("id","title","plot","mediatype","duration","releasedate", "releaseyear", "url", "encodedfamilyid"),
        (row['contentId'], title, _get_text(row['text'], 'description', 'program'),
        row['programType'], row['mediaMetadata']['runtimeMillis'],
            row['releases'][0]['releaseDate'], row['releases'][0]['releaseYear'], _get_play_path(row['contentId']), row['family']['encodedFamilyId']),
        "WHERE id='%s'" % row['contentId']
    )  

    if row['programType'] == 'episode':
        db.replace("episodes",
        ("id","seasonsid", "season", "episode"),
        (row['contentId'], row['seasonId'], row['seasonSequenceNumber'],row['episodeSequenceNumber']),
        "WHERE id='"+row["contentId"]+"'"
        
        )

    db_saveart(row["contentId"], row.get('image'))       

    if fullSync == False:
        db.commit()    

def _parse_video(row):
    

    item = plugin.Item(
        label = _get_text(row['text'], 'title', 'program'),
        info  = {
            'plot': _get_text(row['text'], 'description', 'program'),
            'duration': row['mediaMetadata']['runtimeMillis']/1000,
            'year': row['releases'][0]['releaseYear'],
            'aired': row['releases'][0]['releaseDate'] or row['releases'][0]['releaseYear'],
            'mediatype': 'movie',
        },
        art  = db_saveart(row["contentId"], row['image']),
        path = _get_play_path(row['contentId']),
        playable = True,
    )

    if row['programType'] == 'episode':
        item.info.update({
            'mediatype': 'episode',
            'season': row['seasonSequenceNumber'],
            'episode': row['episodeSequenceNumber'],
            'tvshowtitle': _get_text(row['text'], 'title', 'series'),
        })
    else:                
        item.context.append((_.FULL_DETAILS, 'RunPlugin({})'.format(plugin.url_for(full_details, family_id=row['family']['encodedFamilyId']))))
        item.context.append((_.EXTRAS, "Container.Update({})".format(plugin.url_for(extras, family_id=row['family']['encodedFamilyId']))))
        item.context.append((_.SUGGESTED, "Container.Update({})".format(plugin.url_for(suggested, family_id=row['family']['encodedFamilyId']))))
        pass

    return item

def db_saveart(id, images):
    def _first_image_url(d):
        for r1 in d:
            for r2 in d[r1]:
                return d[r1][r2]['url']

    art = {}
    # don't ask for jpeg thumb; might be transparent png instead
    thumbsize = '/scale?width=400&aspectRatio=1.78'
    bannersize = '/scale?width=1440&aspectRatio=1.78&format=jpeg'
    fullsize = '/scale?width=1440&aspectRatio=1.78&format=jpeg'

    fanart_count = 0
    for name in images or []:
        art_type = images[name]

        lr = br = pr = '' # chosen ratios
        for r in art_type:
            if r == '1.78':
                lr = r
            elif r.startswith('3') and (not br or float(r) > float(br)):
                br = r # longest banner ratio
            elif r.startswith('0') and (not lr or float(lr)-0.67 > float(r)-0.67):
                pr = r # poster ratio closest to 2:3

        if name in ('tile', 'thumbnail'):
            if lr:
                art['thumb'] = _first_image_url(art_type[lr]) + thumbsize
            if pr:
                art['poster'] = _first_image_url(art_type[pr]) + thumbsize

        elif name == 'hero_tile':
            if br:
                art['banner'] = _first_image_url(art_type[br]) + bannersize

        elif name in ('hero_collection', 'background_details', 'background'):
            if lr:
                k = 'fanart{}'.format(fanart_count) if fanart_count else 'fanart'
                art[k] = _first_image_url(art_type[lr]) + fullsize
                fanart_count += 1
            if pr:
                art['keyart'] = _first_image_url(art_type[pr]) + bannersize

        elif name in ('title_treatment', 'logo'):
            lr = '2.00' if '2.00' in art_type else lr
            if lr:
                art['clearlogo'] = _first_image_url(art_type[lr]) + thumbsize

    for x in art:
        api.db.replace("art", ("mediaid","arttype","url"),
                (id, x, art[x]),
                "WHERE mediaid='"+id+"' AND arttype='"+x+"'"
                ) 
    return art

def _get_text(texts, field, source):
    _types = ['medium', 'brief', 'full']

    candidates = []
    for key in texts:
        if key != field:
            continue

        for _type in texts[key]:
            if _type not in _types or source not in texts[key][_type]:
                continue

            for row in texts[key][_type][source]:
                candidates.append((_types.index(_type), texts[key][_type][source][row]['content']))

    if not candidates:
        return None

    return sorted(candidates, key=lambda x: x[0])[0][1]

def sync_series(folderid, series_id, fullSync = False):
    db = api.db
    fullSync = (str(fullSync)=="True")    
    dosync = fullSync
    dt = time.time()
    dt = int(dt)
    
    if dosync == False:        
        parent = db.select("folders f INNER JOIN folderhierarchy h ON h.parentid=f.id AND h.profileid='%s'" % (userdata.get('profile_id'),), 
        ("f.id","f.lastsync","f.syncminutes"), "WHERE id='%s'" % series_id)
        dosync = (len(parent) == 0)
        for p in parent:            
            if (int(p[1] or 0)+int(p[2] or 0)*60<dt):
                dosync = True    
    if dosync == True:            
        serie = db.select("series",("encodedseriesid",),"WHERE id='%s'" % series_id)
        encodedseriesid = serie[0][0]
        data = api.series_bundle(encodedseriesid)
    
        art = db_saveart(series_id, data['series']['image'])
        title = _get_text(data['series']['text'], 'title', 'series')
        folder = plugin.Folder(title)
        ordernr = 1
        for row in data['seasons']['seasons']:            
            item = _parse_season(row, data['series'])
            sync_season(row["seasonId"],series_id, 1)    
            ordernr = ordernr + 1
            
        if fullSync == False:
            db.beginTransaction
        if data['extras']['videos']:
            label = (_.EXTRAS)
            db_addFolder(series_id+'-EXT', series_id, 'Extras','','',label, ordernr)
            db_FolderSync(row["seasonId"],series_id,SYNC_SEASON_MINUTES, dt)
            db_saveart(series_id+'-EXT', data['series']['image'])
            ordernr = ordernr + 1

        if data['related']['items']:
            label = (_.SUGGESTED)
            (series_id+'-REL', series_id, 'Related','','',label, ordernr)
            db_saveart(series_id+'-REL', data['series']['image'])
            ordernr = ordernr + 1


        db_FolderSync(series_id, folderid, dt, SYNC_SERIES_MINUTES)

        if fullSync == False:
            db.commit

        for row in data['related']['items']:
            _process_rows(series_id+'-REL', series_id,data['related']['items']) 

        for row in data['extras']['videos']:
            _process_rows(series_id+'-EXT', series_id,data['extras']['videos'])                                                                

                
        

def sync_season(season_id, folderid, page=1, **kwargs):

    db = api.db
    dt = time.time()
    dt = int(dt)

    ##parentdata = db.select("folders",("id", "lastsync", "syncminutes"),
    ##  "WHERE id='"+season_id+"'")
    ##dosync = (len(parentdata)==0) or (page>1)
    ##if dosync == False:
    ##    for p in parentdata:
    ##        if(p[1]+p[2]*60<dt):
    ##            dosync = True
    dosync = True
    
    if dosync:
        page = int(page)
        data = api.episodes(season_id, page=page)

        _process_rows(season_id, folderid,data['videos'], content_class='episode')

        if (data['meta']['page_size'] + data['meta']['offset']) < data['meta']['hits']:
            sync_season(season_id, folderid, page=page+1)

@plugin.route()
def suggested(family_id=None, series_id=None, **kwargs):
    if family_id:
        data = api.video_bundle(family_id)
    elif series_id:
        data = api.series_bundle(series_id)

    folder = plugin.Folder(_.SUGGESTED)

    items = _process_rows(data['related']['items'])
    folder.add_items(items)
    return folder

@plugin.route()
def extras(family_id=None, series_id=None, **kwargs):
    if family_id:
        data = api.video_bundle(family_id)
        fanart = _get_art(data['video']['image']).get('fanart')
    elif series_id:
        data = api.series_bundle(series_id)
        fanart = _get_art(data['series']['image']).get('fanart')

    folder = plugin.Folder(_.EXTRAS, fanart=fanart)
    items = _process_rows(data['extras']['videos'])
    folder.add_items(items)
    return folder



@plugin.route()
def full_details(family_id=None, series_id=None,**kwargs):
    if series_id:
        data = api.series_bundle(series_id)        
        item = _parse_series(data['series'])

    elif family_id:
        data = api.video_bundle(family_id)
        sync_video(data["video"])
        item = _parse_video(data['video'])    

    warnings.warn(json.dumps(data))

    gui.info(item)

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = api.search(query)
    hits = [x['hit'] for x in data['hits']]
    return _process_rows(hits), False

@plugin.route()
@plugin.login_required()
def play(content_id=None, family_id=None, **kwargs):
    if KODI_VERSION > 18:
        ver_required = '2.6.0'
    else:
        ver_required = '2.4.5'

    ia = inputstream.Widevine(
        license_key = api.get_config()['services']['drm']['client']['endpoints']['widevineLicense']['href'],
        manifest_type = 'hls',
        mimetype = 'application/vnd.apple.mpegurl',
        wv_secure = is_wv_secure(),
    )

    if not ia.check() or not inputstream.require_version(ver_required):
        gui.ok(_(_.IA_VER_ERROR, kodi_ver=KODI_VERSION, ver_required=ver_required))

    if family_id:
        data = api.video_bundle(family_id)
    else:
        data = api.video(content_id)

    video = data.get('video')
    if not video:
        raise PluginError(_.NO_VIDEO_FOUND)

    playback_url = video['mediaMetadata']['playbackUrls'][0]['href']
    playback_data = api.playback_data(playback_url, ia.wv_secure)
    media_stream = playback_data['stream']['complete'][0]['url']
    original_language = video.get('originalLanguage') or 'en'

    headers = api.session.headers
    ia.properties['original_audio_language'] = original_language

    item = _parse_video(video)
    item.update(
        path = media_stream,
        inputstream = ia,
        headers = headers,
        proxy_data = {'original_language': original_language},
    )

    milestones = video.get('milestone', [])
    item.play_next = {}
    item.play_skips = []

    if settings.getBool('sync_playback', False) and playback_data['playhead']['status'] == 'PlayheadFound':
        item.resume_from = plugin.resume_from(playback_data['playhead']['position'])
        if item.resume_from == -1:
            return

    elif milestones and settings.getBool('skip_intros', False):
        intro_start = _get_milestone(milestones, 'intro_start')
        intro_end = _get_milestone(milestones, 'intro_end')

        if intro_start <= 10 and intro_end > intro_start:
            item.resume_from = intro_end
        elif intro_start > 0 and intro_end > intro_start:
            item.play_skips.append({'from': intro_start, 'to': intro_end})

    if milestones and settings.getBool('skip_credits', False):
        credits_start = _get_milestone(milestones, 'up_next')
        tag_start = _get_milestone(milestones, 'tag_start')
        tag_end = _get_milestone(milestones, 'tag_end')
        item.play_skips.append({'from': credits_start, 'to': tag_start})
        if tag_end:
            item.play_skips.append({'from': tag_end, 'to': 0})

    if video['programType'] == 'episode' and settings.getBool('play_next_episode', True):
        data = api.up_next(video['contentId'])
        for row in data.get('items', []):
            if row['type'] == 'DmcVideo' and row['programType'] == 'episode' and row['encodedSeriesId'] == video['encodedSeriesId']:
                item.play_next['next_file'] = _get_play_path(row['contentId'])
                break

    elif video['programType'] != 'episode' and settings.getBool('play_next_movie', False):
        data = api.up_next(video['contentId'])
        for row in data.get('items', []):
            if row['type'] == 'DmcVideo' and row['programType'] != 'episode':
                item.play_next['next_file'] = _get_play_path(row['contentId'])
                break

    if settings.getBool('sync_playback', False):
        telemetry = playback_data['tracking']['telemetry']
        item.callback = {
            'type':'interval',
            'interval': 30,
            'callback': plugin.url_for(callback, media_id=telemetry['mediaId'], fguid=telemetry['fguid']),
        }

    return item

@plugin.route()
@plugin.no_error_gui()
def callback(media_id, fguid, _time, **kwargs):
    api.update_resume(media_id, fguid, int(_time))

def _get_milestone(milestones, name, default=0):
    if not milestones:
        return default

    for key in milestones:
        if key == name:
            return int(milestones[key][0]['milestoneTime'][0]['startMillis'] / 1000)

    return default

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('kid_lockdown')
    userdata.delete('avatar')
    userdata.delete('profile')
    userdata.delete('profile_id')
    gui.refresh()
