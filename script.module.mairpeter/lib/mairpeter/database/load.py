from . import dbmysql, dbsqlite, advancedsettings
import xbmc


def loadDB(databasename, defaultdb=""):    
        
    _config = advancedsettings.DBConfigFromAdvancedSettings(databasename, defaultdb=defaultdb)        
    _db = None
    
    if  (_config["type"] == "mysql"):                        
        _db = dbmysql.MySQLDB()    
        _config.pop("type")
        
    else:
        _db = dbsqlite.SQLiteDB()            
    _db.connect(_config)
    return _db