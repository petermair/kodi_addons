from xbmcaddon import Addon


def InitialDBSetup(api):
    ADDON_VERSION = Addon().getAddonInfo('version')
    NEWDBVERSION = 4
    dbversion = NEWDBVERSION      
    version = '0.0.0'

    tables = api.db.TableList()
    if len(tables)==0:
        api.db.createTable(
            "version",
            (
                {"fieldname": "version",   "fieldtype": "varchar", "fieldsize": 20, "notnull": True},            
                {"fieldname": "dbversion", "fieldtype": "varchar", "fieldsize": 20, "notnull": False},
            ),
            ("version",)
        )
    v = api.db.select("version",("version","dbversion"),"ORDER BY dbversion DESC, version DESC")
    if len(v)>0:
        dbversion = v[0][1]
        version = v[0][0]       
        
    if (version == ADDON_VERSION) and (dbversion == NEWDBVERSION):
        return


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

    if int(dbversion)==1: ## Drop table, profileid added
        api.db.execute("DROP TABLE IF EXISTS folderhierarchy")

    api.db.createTable(
        "folderhierarchy",
        (
            {"fieldname": "foldersid","fieldtype": "varchar", "fieldsize": 40, "notnull": True},                       
            {"fieldname": "parentid", "fieldtype": "varchar", "fieldsize": 40, "notnull": True},
            {"fieldname": "profileid", "fieldtype": "varchar", "fieldsize": 40, "notnull": True},
            {"fieldname": "ordernr",  "fieldtype": "int",     "fieldsize": 11, "notnull": True},   
            {"fieldname": "active",   "fieldtype": "int",     "fieldsize":  11, "notnull": False},  
            {"fieldname": "lastsync", "fieldtype": "bigint",  "fieldsize":  20, "notnull": False}, ## Added DB v.4                 
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

    api.db.createTable(
        "genres",
        (
            {"fieldname": "mediaid",         "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "title",           "fieldtype": "varchar", "fieldsize":  150, "notnull": True},                        
        ),
        ("mediaid","title")
    )

    api.db.createTable(
        "directors",
        (
            {"fieldname": "mediaid",         "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "title",            "fieldtype": "varchar", "fieldsize":  150, "notnull": True},                        
        ),
        ("mediaid","title")
    )

    api.db.createTable(
        "actors",
        (
            {"fieldname": "mediaid",         "fieldtype": "varchar", "fieldsize":   50, "notnull": True},            
            {"fieldname": "title",            "fieldtype": "varchar", "fieldsize":  150, "notnull": True},                        
            {"fieldname": "role",       "fieldtype": "varchar", "fieldsize":  150, "notnull": True},                        
        ),
        ("mediaid","title")
    )

    if (int(dbversion)!=NEWDBVERSION) or (version != ADDON_VERSION):
        api.db.beginTransaction    
        api.db.replace("version",("version","dbversion"),(ADDON_VERSION, NEWDBVERSION),"WHERE version='%s'" % ADDON_VERSION)
        api.db.commit