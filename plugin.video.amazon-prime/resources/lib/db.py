import json
from .common import Globals
import time

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