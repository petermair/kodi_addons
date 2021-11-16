import json
from .common import Globals
import time
from xbmcaddon import Addon

def db_addFolder(id, parentid, verb, title, detailurl, ordernr = -1, active = 1, content = None):
    g = Globals()
    db = g.db()
    marketid = g.MarketID    
    db.replace("folders",
      ("id","verb","title","detailurl", "content"),
      (id, verb, title, detailurl, content),
      "WHERE id='%s'" % (db.escape(id),)
    )
    db.replace("folderhierarchy",
      ("id","parentid","marketid", "active"),
      (id, parentid, marketid, active),
      "WHERE id='%s' and parentid='%s'" % (db.escape(id), db.escape(parentid))
    )

    if ordernr>-1:
      db.replace("folderhierarchy",
        ("ordernr",),
        (ordernr, ),
        "WHERE id='%s' and parentid='%s'" % (db.escape(id), db.escape(parentid))
      )  

def db_setSync(id, minutes = 24*60):
  g = Globals()
  db = g.db()
  if minutes == 0:
    dt = 0
  else:
    dt = time.time()
    dt = int(dt)  
  db.update("folders",
    ("lastsync", "syncminutes"),
    (dt, minutes),
    "WHERE id='%s'" % (db.escape(id))
  )
  db.update("folderhierarchy",("active",),(1,), "WHERE id='%s'" % (db.escape(id)))

def db_getArt(id):
  g = Globals()
  db = g.db()
  art = {}
  data =db.select("art", ("arttype", "url"), "WHERE mediaid='%s'" % (db.escape(id),))
  for a in data:
      art[a[0]] = a[1]
  return art
    
def db_setArt(id, arttype, url):
  g = Globals()
  db = g.db()    
  db.replace("art", ("mediaid","arttype","url"),
              (id, arttype, url),
              "WHERE mediaid='"+db.escape(id)+"' AND arttype='"+arttype+"'")

def db_Setup():
    ADDON_VERSION = Addon().getAddonInfo('version')
    NEWDBVERSION = 2
    dbversion = 0      
    version = '0.0.0'

    g = Globals()
    db = g.db()

    tables = db.TableList()
    if len(tables)==0:
        db.createTable(
            "version",
            (
                {"fieldname": "version",   "fieldtype": "varchar", "fieldsize": 20, "notnull": True},            
                {"fieldname": "dbversion", "fieldtype": "varchar", "fieldsize": 20, "notnull": False},
            ),
            ("version",)
        )
    v = db.select("version",("version","dbversion"),"ORDER BY version DESC")
    if len(v)>0:
        dbversion = v[0][1]
        version = v[0][0]       
        
    if (dbversion == NEWDBVERSION) and (version==ADDON_VERSION):
        return         

    
    db.createTable(
        "art",
        (
            {"fieldname": "mediaid", "fieldtype": "varchar", "fieldsize": 300, "notnull": True},            
            {"fieldname": "arttype", "fieldtype": "varchar", "fieldsize":  50, "notnull": True},
            {"fieldname": "url",     "fieldtype": "varchar", "fieldsize":3000, "notnull": True},
        ),
        ("mediaid","arttype")
    )

    db.createTable(
        "folderhierarchy",
        (
            {"fieldname": "id",       "fieldtype": "varchar", "fieldsize": 300, "notnull": True},            
            {"fieldname": "parentid", "fieldtype": "varchar", "fieldsize": 300, "notnull": True},            
            {"fieldname": "marketid", "fieldtype": "varchar", "fieldsize":  50, "notnull": True},
            {"fieldname": "ordernr",  "fieldtype": "int",     "fieldsize":   0, "notnull": False},
            {"fieldname": "active",   "fieldtype": "int",     "fieldsize":   0, "notnull": False},
        ),
        ("id","parentid","marketid")
    )

    db.createTable(
        "folders",
        (
            {"fieldname": "id",        "fieldtype": "varchar", "fieldsize":   300, "notnull": True},            
            {"fieldname": "verb",      "fieldtype": "varchar", "fieldsize":   300, "notnull": True},            
            {"fieldname": "title",     "fieldtype": "varchar", "fieldsize":   150, "notnull": True},
            {"fieldname": "detailurl",  "fieldtype": "varchar", "fieldsize": 3000, "notnull": False},
            {"fieldname": "content",    "fieldtype": "varchar", "fieldsize":   20, "notnull": False},
            {"fieldname": "lastsync",   "fieldtype": "bigint",  "fieldsize":    0, "notnull": False},
            {"fieldname": "syncminutes","fieldtype": "int",     "fieldsize":    0, "notnull": False},
            {"fieldname": "prime",      "fieldtype": "int",     "fieldsize":    0, "notnull": False},
        ),
        ("id",)
    )    

    db.createTable(
        "profiles",
        (
            {"fieldname": "id",            "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "name",          "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "agegroup",      "fieldtype": "varchar", "fieldsize":  100, "notnull": True},
            {"fieldname": "avatarid",      "fieldtype": "varchar", "fieldsize":   50, "notnull": False},            
            {"fieldname": "isdefault",     "fieldtype": "int",     "fieldsize":    0, "notnull": False},
            {"fieldname": "switchlink",    "fieldtype": "varchar", "fieldsize": 2000, "notnull": False},
            {"fieldname": "lastsync",      "fieldtype": "bigint",  "fieldsize":    0, "notnull": False},
        ),
        ("id",)
    )

    db.createTable(
        "movies",
        (
            {"fieldname": "id",           "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "title",        "fieldtype": "varchar", "fieldsize":  200, "notnull": True},            
            {"fieldname": "releaseyear",  "fieldtype": "varchar", "fieldsize":   10, "notnull": False},
            {"fieldname": "duration",     "fieldtype": "int",     "fieldsize":    0, "notnull": False},            
            {"fieldname": "plot",         "fieldtype": "longtext","fieldsize":    0, "notnull": False},            
            {"fieldname": "isplayable",   "fieldtype": "int",     "fieldsize":    0, "notnull": False},            
        ),
        ("id",)
    )

    db.createTable(
        "series",
        (
            {"fieldname": "id",           "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "title",        "fieldtype": "varchar", "fieldsize":  200, "notnull": False},                                    
        ),
        ("id",)
    )

    db.createTable(
        "seasons",
        (
            {"fieldname": "id",           "fieldtype": "varchar", "fieldsize":   50, "notnull": True},     
            {"fieldname": "seriesid",     "fieldtype": "varchar", "fieldsize":   50, "notnull": True},        
            {"fieldname": "title",        "fieldtype": "varchar", "fieldsize":  200, "notnull": False},            
            {"fieldname": "releaseyear",  "fieldtype": "varchar", "fieldsize":   10, "notnull": False},
            {"fieldname": "releasedate",  "fieldtype": "varchar", "fieldsize":   50, "notnull": False},
            {"fieldname": "duration",     "fieldtype": "int",     "fieldsize":    0, "notnull": False},            
            {"fieldname": "plot",         "fieldtype": "longtext","fieldsize":    0, "notnull": False},            
            {"fieldname": "seasonnumber",  "fieldtype": "int",    "fieldsize":    0, "notnull": False},            
            {"fieldname": "detailurl",    "fieldtype": "varchar", "fieldsize": 1000, "notnull": False},            
        ),
        ("id",)
    )

    db.createTable(
        "episodes",
        (
            {"fieldname": "id",           "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "seasonsid",    "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "seriesid",     "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "title",        "fieldtype": "varchar", "fieldsize":  200, "notnull": True},            
            {"fieldname": "releaseyear",  "fieldtype": "varchar", "fieldsize":   10, "notnull": False},
            {"fieldname": "releasedate",  "fieldtype": "varchar", "fieldsize":   50, "notnull": False},
            {"fieldname": "duration",     "fieldtype": "int",     "fieldsize":    0, "notnull": False},            
            {"fieldname": "plot",         "fieldtype": "longtext","fieldsize":    0, "notnull": False},            
            {"fieldname": "episodenumber","fieldtype": "int",     "fieldsize":    0, "notnull": False},            
            {"fieldname": "detailurl",    "fieldtype": "varchar", "fieldsize": 1000, "notnull": False},            
            {"fieldname": "isplayable",   "fieldtype": "int",     "fieldsize":    0, "notnull": False},            
        ),
        ("id",)
    )

    db.createTable(
        "extendedinfo",
        (
            {"fieldname": "id",             "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "releasedate",    "fieldtype": "varchar", "fieldsize":   20, "notnull": False},            
            {"fieldname": "releaseyear",    "fieldtype": "int",     "fieldsize":    0, "notnull": False},            
            {"fieldname": "duration",       "fieldtype": "int",     "fieldsize":    0, "notnull": False},            
            {"fieldname": "rating",         "fieldtype": "float",   "fieldsize":    0, "notnull": False},
            {"fieldname": "isPrime",        "fieldtype": "int",     "fieldsize":    0, "notnull": False},
            {"fieldname": "isClosedCaption","fieldtype": "int",     "fieldsize":    0, "notnull": False},            
            {"fieldname": "isXRay",         "fieldtype": "int",     "fieldsize":    0, "notnull": False},            
            {"fieldname": "titletype",      "fieldtype": "varchar", "fieldsize":   50, "notnull": False},                        
        ),
        ("id",)
    )

    db.createTable(
        "genres",
        (
            {"fieldname": "id",             "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "text",           "fieldtype": "varchar", "fieldsize":  150, "notnull": True},            
            {"fieldname": "detailurl",      "fieldtype": "varchar", "fieldsize":  200, "notnull": True},                                               
        ),
        ("id",)
    )

    db.createTable(
        "moviegenres",
        (
            {"fieldname": "mediaid",         "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "genresid",        "fieldtype": "varchar", "fieldsize":   50, "notnull": True},                        
        ),
        ("mediaid","genresid")
    )

    db.createTable(
        "moviestudios",
        (
            {"fieldname": "mediaid",         "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "title",           "fieldtype": "varchar", "fieldsize":  150, "notnull": True},                                                                     
        ),
        ("mediaid",)
    )

    db.createTable(
        "movieactors",
        (
            {"fieldname": "mediaid",         "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "title",           "fieldtype": "varchar", "fieldsize":  150, "notnull": True},                                                                     
            {"fieldname": "ordernr",         "fieldtype": "int",     "fieldsize":    0, "notnull": True}
        ),
        ("mediaid","ordernr")
    )    

    
    db.createTable(
        "watchlist",
        (
            {"fieldname": "id",             "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "tag",            "fieldtype": "varchar", "fieldsize":   20, "notnull": True},            
            {"fieldname": "returnurl",      "fieldtype": "varchar", "fieldsize":  200, "notnull": True},                                               
            {"fieldname": "token",          "fieldtype": "varchar", "fieldsize":  200, "notnull": True},                                               
            {"fieldname": "partialurl",     "fieldtype": "varchar", "fieldsize":  200, "notnull": True},                                               
            {"fieldname": "titleid",        "fieldtype": "varchar", "fieldsize":   50, "notnull": True},                                               
        ),
        ("id",)
    )

    if (int(dbversion)!=NEWDBVERSION) or (version != ADDON_VERSION):
        db.beginTransaction()  
        db.replace("version",("version","dbversion"),(ADDON_VERSION, NEWDBVERSION),"WHERE version='%s'" % ADDON_VERSION)
        db.commit()