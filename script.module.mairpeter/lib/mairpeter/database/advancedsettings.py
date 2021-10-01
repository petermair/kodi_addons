import xbmcvfs
import xbmc
from xml.dom import minidom
from xml.parsers.expat import ExpatError

def DBConfigFromAdvancedSettings(database, defaultdb = ""):
    if defaultdb == "":
        defaultdb = database
    config = {
        "type": "sqlite3",
        "host": xbmc.translatePath("special://database/"+defaultdb+".db"),
        "database": defaultdb
    }
    as_file = xbmc.translatePath('special://profile/advancedsettings.xml')
    if(xbmcvfs.exists(as_file)):        
        try:
            doc = minidom.parse(as_file)
            for db_node in doc.documentElement.childNodes:                    
                if db_node.nodeName == database+"database":                    
                    config["database"] = database
                    for db_set in db_node.childNodes:                            
                        if db_set.nodeName == "type":                              
                            config["type"] = db_set.childNodes[0].data
                        elif db_set.nodeName == "host":
                            config["host"] = db_set.childNodes[0].data
                        elif db_set.nodeName == "database":
                            config["database"] = db_set.childNodes[0].data
                        elif db_set.nodeName == "port":
                            config["port"] =  db_set.childNodes[0].data
                        elif db_set.nodeName == "user":
                            config["user"] = db_set.childNodes[0].data
                        elif db_set.nodeName == "pass":
                            config["password"] = db_set.childNodes[0].data
        except ExpatError:
            pass
    return config