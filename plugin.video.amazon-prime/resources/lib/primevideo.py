#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import OrderedDict
from copy import deepcopy

from xbmcvfs import exists
from kodi_six import xbmcplugin, xbmcgui
import json
import re
import time
import math

from .common import key_exists, return_item, sleep
from .singleton import Singleton
from .network import getURL, getURLData, MechanizeLogin, FQify, GrabJSON
from .logging import Log
# from .itemlisting import setContentAndView
from .l10n import *
from .users import *
# from .playback import PlayVideo
from .db import *

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

import warnings


class PrimeVideo(Singleton):
    """ Wrangler of all things PrimeVideo.com """

    _catalog = {}  # Catalog cache    
    _separator = '/'  # Virtual path separator
    

    def __init__(self, globalsInstance, settingsInstance):
        self._g = globalsInstance
        self._s = settingsInstance
        """ Data for date string deconstruction and reassembly

            Date references:
            https://www.primevideo.com/detail/0LCQSTWDMN9V770DG2DKXY3GVF/  09 10 11 12 01 02 03 04 05
            https://www.primevideo.com/detail/0ND5POOAYD6A4THTH7C1TD3TYE/  06 07 08 09

            Languages: https://www.primevideo.com/settings/language/
        """
        self._dateParserData = {
            'generic': r'^(?P<m>[^W]+)[.,:;\s-]+(?P<d>[0-9]+),\s+(?P<y>[0-9]+)(?:\s+[0-9]+|$)',
            'asianMonthExtractor': r'^([0-9]+)[월月]',
            'da_DK': {'deconstruct': r'^(?P<d>[0-9]+)\.?\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'januar': 1, 'februar': 2, 'marts': 3, 'april': 4, 'maj': 5, 'juni': 6, 'juli': 7, 'august': 8, 'september': 9, 'oktober': 10,
                                 'november': 11, 'december': 12}},
            'de_DE': {'deconstruct': r'^(?P<d>[0-9]+)\.?\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'januar': 1, 'februar': 2, 'märz': 3, 'april': 4, 'mai': 5, 'juni': 6, 'juli': 7, 'august': 8, 'september': 9, 'oktober': 10,
                                 'november': 11, 'dezember': 12}},
            'en_US': {'deconstruct': r'^(?P<m>[^\s]+)\s+(?P<d>[0-9]+),?\s+(?P<y>[0-9]+)',
                      'months': {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, 'august': 8, 'september': 9, 'october': 10,
                                 'november': 11, 'december': 12}},
            'es_ES': {'deconstruct': r'^(?P<d>[0-9]+)\s+de\s+(?P<m>[^\s]+),?\s+de\s+(?P<y>[0-9]+)',
                      'months': {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10,
                                 'noviembre': 11, 'diciembre': 12}},
            'fi_FI': {'deconstruct': r'^(?P<d>[0-9]+)\.?\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'tammikuuta': 1, 'helmikuuta': 2, 'maaliskuuta': 3, 'huhtikuuta': 4, 'toukokuuta': 5, 'kesäkuuta': 6, 'heinäkuuta': 7, 'elokuuta': 8,
                                 'syyskuuta': 9, 'lokakuuta': 10, 'marraskuuta': 11, 'joulukuuta': 12}},
            'fr_FR': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6, 'juillet': 7, 'aout': 8, 'août': 8, 'septembre': 9,
                                 'octobre': 10, 'novembre': 11, 'décembre': 12}},
            'hi_IN': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'जनवरी': 1, 'फ़रवरी': 2, 'मार्च': 3, 'अप्रैल': 4, 'मई': 5, 'जून': 6, 'जुलाई': 7, 'अगस्त': 8, 'सितंबर': 9, 'अक्तूबर': 10,
                                 'नवंबर': 11, 'दिसंबर': 12}},
            'id_ID': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8, 'september': 9,
                                 'oktober': 10, 'november': 11, 'desember': 12}},
            'it_IT': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8, 'settembre': 9,
                                 'ottobre': 10, 'novembre': 11, 'dicembre': 12}},
            'ko_KR': {'deconstruct': r'^(?P<y>[0-9]+)년\s+(?P<m>[0-9]+)월\s+(?P<d>[0-9]+)일'},
            'nb_NO': {'deconstruct': r'^(?P<d>[0-9]+)\.?\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'januar': 1, 'februar': 2, 'mars': 3, 'april': 4, 'mai': 5, 'juni': 6, 'juli': 7, 'august': 8, 'september': 9, 'oktober': 10,
                                 'november': 11, 'desember': 12}},
            'nl_NL': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6, 'juli': 7, 'augustus': 8, 'september': 9,
                                 'oktober': 10, 'november': 11, 'december': 12}},
            'pl_PL': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'stycznia': 1, 'lutego': 2, 'marca': 3, 'kwietnia': 4, 'maja': 5, 'czerwca': 6, 'lipca': 7, 'sierpnia': 8, 'września': 9,
                                 'października': 10, 'listopada': 11, 'grudnia': 12}},
            'pt_BR': {'deconstruct': r'^(?P<d>[0-9]+)\s+de\s+(?P<m>[^\s]+),?\s+de\s+(?P<y>[0-9]+)',
                      'months': {'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10,
                                 'novembro': 11, 'dezembro': 12}},
            'pt_PT': {'deconstruct': r'^(?P<d>[0-9]+)\s+de\s+(?P<m>[^\s]+),?\s+de\s+(?P<y>[0-9]+)',
                      'months': {'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10,
                                 'novembro': 11, 'dezembro': 12}},
            'ru_RU': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9,
                                 'октября': 10, 'ноября': 11, 'декабря': 12}},
            'sv_SE': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'januari': 1, 'februari': 2, 'mars': 3, 'april': 4, 'maj': 5, 'juni': 6, 'juli': 7, 'augusti': 8, 'september': 9, 'oktober': 10,
                                 'november': 11, 'december': 12}},
            'ta_IN': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+),?\s+(?P<y>[0-9]+)',
                      'months': {'ஜனவரி': 1, 'பிப்ரவரி': 2, 'மார்ச்': 3, 'ஏப்ரல்': 4, 'மே': 5, 'ஜூன்': 6, 'ஜூலை': 7, 'ஆகஸ்ட்': 8, 'செப்டம்பர்': 9,
                                 'அக்டோபர்': 10, 'நவம்பர்': 11, 'டிசம்பர்': 12}},
            'te_IN': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+),?\s+(?P<y>[0-9]+)',
                      'months': {'జనవరి': 1, 'ఫిబ్రవరి': 2, 'మార్చి': 3, 'ఏప్రిల్': 4, 'మే': 5, 'జూన్': 6, 'జులై': 7, 'ఆగస్టు': 8, 'సెప్టెంబర్': 9, 'అక్టోబర్': 10,
                                 'నవంబర్': 11, 'డిసెంబర్': 12}},
            'th_TH': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+),?\s+(?P<y>[0-9]+)',
                      'months': {'มกราคม': 1, 'กุมภาพันธ์': 2, 'มีนาคม': 3, 'เมษายน': 4, 'พฤษภาคม': 5, 'มิถุนายน': 6, 'กรกฎาคม': 7, 'สิงหาคม': 8, 'กันยายน': 9, 'ตุลาคม': 10,
                                 'พฤศจิกายน': 11, 'ธันวาคม': 12}},
            'tr_TR': {'deconstruct': r'^(?P<d>[0-9]+)\s+(?P<m>[^\s]+)\s+(?P<y>[0-9]+)',
                      'months': {'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'haziran': 6, 'temmuz': 7, 'ağustos': 8, 'eylül': 9,
                                 'ekim': 10, 'kasım': 11, 'aralık': 12}},
            'zh_CN': {'deconstruct': r'^(?P<y>[0-9]+)年(?P<m>[0-9]+)月(?P<d>[0-9]+)日',
                      'months': {'一月': 1, '二月': 2, '三月': 3, '四月': 4, '五月': 5, '六月': 6, '七月': 7, '八月': 8, '九月': 9, '十月': 10, '十一月': 11, '十二月': 12}},
            'zh_TW': {'deconstruct': r'^(?P<y>[0-9]+)年(?P<m>[0-9]+)月(?P<d>[0-9]+)日',
                      'months': {'一月': 1, '二月': 2, '三月': 3, '四月': 4, '五月': 5, '六月': 6, '七月': 7, '八月': 8, '九月': 9, '十月': 10, '十一月': 11, '十二月': 12}},
        }
        self._languages = [
            ('id_ID', 'Bahasa Indonesia'),
            ('da_DK', 'Dansk'),
            ('de_DE', 'Deutsch'),
            ('en_US', 'English'),
            ('es_ES', 'Español'),
            ('fr_FR', 'Français'),
            ('it_IT', 'Italiano'),
            ('nl_NL', 'Nederlands'),
            ('nb_NO', 'Norsk'),
            ('pl_PL', 'Polski'),
            ('pt_BR', 'Português (Brasil)'),
            ('pt_PT', 'Português (Portugal)'),
            ('fi_FI', 'Suomi'),
            ('sv_SE', 'Svenska'),
            ('tr_TR', 'Türkçe'),
            ('ru_RU', 'Русский'),
            ('hi_IN', 'हिन्दी'),
            ('ta_IN', 'தமிழ்'),
            ('te_IN', 'తెలుగు'),
            ('th_TH', 'ไทย'),
            ('zh_CN', '简体中文'),
            ('zh_TW', '繁體中文'),
            ('ko_KR', '한국어'),
        ]
        self._TextCleanPatterns = [[r'\s+-\s*([^&])', r' – \1'],  # Convert dash from small to medium where needed
                                   [r'\s*-\s+([^&])', r' – \1'],  # Convert dash from small to medium where needed
                                   [r'^\s+', ''],  # Remove leading spaces
                                   [r'\s+$', ''],  # Remove trailing spaces
                                   [r' {2,}', ' '],  # Remove double spacing
                                   [r'\.\.\.', '…']]  # Replace triple dots with ellipsis
        # rex compilation
        self._imageRefiner = re.compile(r'\._.*_\.')
        self._reURN = re.compile(r'(?:/gp/video)?/d(?:p|etail)/([^/]+)/')
        self._reImage = re.compile(r'(UR([0-9]*),([0-9]*)_(RI_UX|BL99_UR)([0-9]*)(_UY|,)([0-9]*)_[^w]*.(jpg|png))')
        self._dateParserData['generic'] = re.compile(self._dateParserData['generic'], re.UNICODE)
        self._dateParserData['asianMonthExtractor'] = re.compile(self._dateParserData['asianMonthExtractor'])
        for k in self._dateParserData:
            try:
                self._dateParserData[k]['deconstruct'] = re.compile(self._dateParserData[k]['deconstruct'])
            except: pass
        for i, s in enumerate(self._TextCleanPatterns):
            self._TextCleanPatterns[i][0] = re.compile(s[0])
        db_Setup()
    

    
    def _BeautifyText(self, title):
        """ Correct stylistic errors in Amazon's titles """

        for r in self._TextCleanPatterns:
            title = r[0].sub(r[1], title)
        return title

    def RefreshFolder(self, foldersid):
        db = self._g.db()
        db.beginTransaction()
        db_setSync(foldersid,0)
        db.commit()
        xbmc.executebuiltin('Container.Refresh')
        self._g.dialog.notification(self._g.addon.getAddonInfo('name'), "Refreshed", time=1000, sound=False)                
        

    def syncContent(self, path, doRefresh=False):        
        
        dt = time.time()
        dt = int(dt)    
        try:
            from urllib.parse import unquote_plus
        except:
            from urllib import unquote_plus

        db = self._g.db()
        
        parent = db.select("folders", ("id", "verb", "lastsync","detailurl","syncminutes"),"WHERE id='%s'" % (db.escape(path),))
        data = db.select("folderhierarchy",("*",),"WHERE parentid='%s' LIMIT 1" % (db.escape(path),))        

        dosync = doRefresh or (len(data)==0)        
        
        if dosync==False:
            if len(parent)==0:                
                dosync = True
            else:         
                if parent[0][3]=="":
                    dosync = False
                elif parent[0][2]==None or parent[0][4] is None:
                    dosync = True
                else:
                    ## Use value from settings, otherwise from database
                    dosync = (((parent[0][2] or 0) + 60 * (self._s.catalogCacheExpiry or (parent[0][4] or 0))) <dt)                
        if dosync==True:
            
            try:
                db.beginTransaction()
                db.update("folderhierarchy",("active",),(0,),"WHERE parentid='%s'" % (db.escape(path),))
                db.commit()
                amzLang = None
                cj = MechanizeLogin()
                if cj:
                    amzLang = cj.get('lc-main-av', path='/')
                amzLang = amzLang if amzLang else 'en_US'
                
                if (path=="root") or (path==None) or (path==""):                                        
                    self.BuildRoot("root")            
                else:            
                    if len(parent)>0:
                        requestURL = parent[0][3]            
                        requestURL = requestURL                                            
                        self.parseCollection(path, requestURL, 1,1)  
                db.beginTransaction()
                db_setSync(path)                  
                db.commit()
            except:
                db.rollback()
                raise
            
    def genID(self, id):
        id.replace('?','')
        id.replace('%','')
        return id.encode('ascii', 'ignore').decode('ascii')

    def ExtractURN(self, url):
            """ Extract the unique resource name identifier """
            ret = self._reURN.search(url)
            return None if not ret else ret.group(1)

    def RedefineImage(self, url, width=1920):
        ret = self._reImage.search(url)
        
        if ret is None:            
            return url
        else:            
            s = ret.group(1)
            w = float(ret.group(2))
            h = float(ret.group(3))
            ext = ret.group(8)
            nw = float(width)
            nh = int(math.ceil(nw * h / w))
            nw = int(nw)
            rep = "UR%s,%s_RI_UX%s_UY%s_.%s" % (str(nw),str(nh),str(nw),str(nh),str(ext))
            return url.replace(s, rep)


    def  parseCollection(self, path, requestURL, offset, page=1):
        
        def NotifyUser(msg, bForceDisplay=False):
            """ Pop up messages while scraping to inform users of progress """

            if not hasattr(NotifyUser, 'lastNotification'):
                NotifyUser.lastNotification = 0
            if bForceDisplay or (NotifyUser.lastNotification < time.time()):
                # Only update once every other second, to avoid endless message queue
                NotifyUser.lastNotification = 1 + time.time()
                self._g.dialog.notification(self._g.addon.getAddonInfo('name'), msg, time=1000, sound=False)                

        
        # Load content            

        
        g = Globals()
        db = g.db()  
        
        NotifyUser(getString(30252).format(page))

        
        if requestURL is not None:
            # Too many instances to track, append the episode finder to about every query and cross fingers
            ##requestURL += ('&' if '?' in requestURL else '?') + 'episodeListSize=9999'
            pass
        else: 
            data = db.select("series",("id",),"WHERE id='%s'" % (db.escape(path)))
            if len(data)>0:
                self.parseSeries(data[0][0])
            return


        urn = self.ExtractURN(requestURL)
        cnt = GrabJSON(requestURL)                   
        if urn:
            if "state" in cnt:
                if "collections" in cnt["state"]:
                    self.parseSeason(cnt)
                else:
                    if not db.exists("movies","WHERE id='%s'" % (db.escape(path),)):
                        self.parseMovie(path, cnt)
        else:                          
            iorder = offset
            if ("collections" in cnt):            
                corder = 1    
                for row in cnt["collections"]:
                    detailurl = ""
                    if("seeMoreLink" in row):
                        detailurl = row["seeMoreLink"]["url"]
                    colid = path+'/'+self.genID(row["text"])
                    if (row["collectionType"] != "Carousel"):                                            
                        continue
                    db.beginTransaction()
                    db_addFolder(colid,
                        path, "pv/browse/"+colid,row["text"],detailurl,corder,1, "folder")                    
                    db.commit()
                    corder = corder +1                
                    if (detailurl == ""):  
                        iorder = offset
                        if "items" in row:
                            for item in row["items"]:
                                self.parseItem(item, colid, iorder)
                                iorder = iorder + 1
            if ("items" in cnt):
                iorder = offset
                for item in cnt["items"]:
                    self.parseItem(item, path, iorder)                
                    iorder = iorder + 1    
            if path=="watchlist":
                wl = return_item(cnt, 'viewOutput', 'features', 'legacy-watchlist')
                if wl != None:
                    wordernr = 1
                    try:
                        for f in wl['filters']:
                            itemid = self.genID(path+'/'+f["id"])
                            db.beginTransaction()
                            db_addFolder(itemid,path,'pv/browse/'+itemid,f["text"], f['apiUrl' if 'apiUrl' in f else 'href'], wordernr, 1, "watchlist")
                            db.commit()
                            wordernr = wordernr + 1
                    except KeyError: pass  # Empty watchlist
            else:
                wl = return_item(cnt, 'viewOutput', 'features', 'legacy-watchlist', 'content')
                if wl != None:
                    iorder = offset
                    if "items" in wl:
                        for w in wl["items"]:
                            self.parseItem(w, path, iorder)
                            iorder = iorder + 1
            if "state" in cnt: ## Series
                pass


            nexturl = None
            if "pagination" in cnt:
                if "apiUrl" in cnt["pagination"]:
                    nexturl = cnt["pagination"]["apiUrl"]
                elif "paginator" in cnt["pagination"]:
                    nexturl = next((x['href'] for x in cnt['pagination']['paginator'] if
                                                (('type' in x) and ('NextPage' == x['type'])) or
                                                (('*className*' in x) and ('atv.wps.PaginatorNext' == x['*className*'])) or
                                                (('__type' in x) and ('PaginatorNext' in x['__type']))), None)
                if nexturl != None:
                    ## Avoid deadlock                    
                    self.parseCollection(path, nexturl, iorder, page + 1)


    def parseItem(self, item, parent, offset):
        g = Globals()
        db = g.db() 
        if "items" in item: 
            for i in item["items"]:
                self.parseItem(i, parent, 1)
        if "titleID" in item:
            itemid = self.genID(item["titleID"])
            subdetailurl =""
            verb = ""
            iorder = offset
            content = "folder"        
            verb = "pv/browse/"+itemid               
            if "href" in item:
                subdetailurl = item["href"]            
            elif "link"  in item:
                subdetailurl = item["link"]["url"]
            if "title" in item: 
                title = item["title"]
            if "heading" in item: ## Series
                title = item["heading"]              
            catalogdata=[]  
            compactgti = self.ExtractURN(subdetailurl)
            if compactgti != None:
                ## find type from DB
                if not db.exists("movies","WHERE id='%s'" %(db.escape(itemid),)):
                    if not db.exists("seasons","WHERE id='%s'" %(db.escape(itemid),)):
                            pbres = getURLData('catalog/GetPlaybackResources', itemid, silent=True, extra=True, useCookie=True,
                                opt='&titleDecorationScheme=primary-content', dRes='CatalogMetadata')
                            for res in pbres:
                                try:
                                    if "catalogMetadata" in res :
                                        catalogdata = res["catalogMetadata"]                                        
                                        content = catalogdata["catalog"]["type"].lower()
                                        if content=="episode": 
                                            content = "series"                                              
                                except:
                                    ## Bool
                                    pass
                    else:
                        content = "series"
                        data = db.select("seasons",("seriesid",),"WHERE id='%s'" % (db.escape(itemid),))
                        seriesid = data[0][0]                        
                        data = db.select("series",("title",),"WHERE id='%s'" % (db.escape(seriesid),))
                        title = data[0][0]
                        
                else:
                    content = "movie"
                    catalogdata=[]

            if content == "movie":            
                verb = '?mode=PlayVideo&name={}&asin={}{}'.format(compactgti, itemid, "")                        
                if len(catalogdata)>0:
                    movie = catalogdata                            
                    rt = plot = ry = None
                    if "catalog" in movie:
                        catalog = movie["catalog"]
                        if "runtimeSeconds" in catalog:
                            rt = catalog["runtimeSeconds"]                                                            
                        if "releaseYear" in catalog:
                            ry = catalog["releaseYear"]
                        if "synopsis" in catalog:
                            plot = catalog["synopsis"]
                    if "summary" in movie["playback"]:
                        isPlayable = movie["playback"]["summary"]["isPlayable"]
                    else:
                        isPlayable = True
                    db.beginTransaction()          
                    db.replace("movies",
                    ("id","isplayable","releaseyear","title","duration","plot"),
                    (itemid, int(isPlayable), ry, title, rt, plot),
                    "WHERE id='%s'"  % (db.escape(itemid),)
                    )                    
                    db_setSync(itemid)
                    db.commit()
            elif content=="series":            
                if len(catalogdata)>0:
                    episode = catalogdata
                    
                    if  not "family" in episode:
                        return None

                    family = episode["family"]
                    for tv in family["tvAncestors"]:
                        if tv["catalog"]["type"]=="SHOW":
                            db.beginTransaction()          
                            db.replace("series",("id", "title"), 
                                (tv["catalog"]["id"], tv["catalog"]["title"]),
                                "where id='%s'" % (db.escape(tv["catalog"]["id"]),)
                            )
                            db.commit()
                            itemid =  tv["catalog"]["id"]  
                            title = tv["catalog"]["title"] 
                    verb = "pv/browse/"+itemid
                else:
                    itemid = seriesid                             
                    verb = "pv/browse/"+itemid   
            elif content != "folder":
                warnings.warn("UNKNOWN CATALOG-TYPE!!!")
                warnings.warn(json.dumps(catalogdata))
                return

            db.beginTransaction()
            if "imageSrc" in item:
                img = self.RedefineImage(item["imageSrc"], 640)
                db_setArt(itemid, "thumb", img)            
                img = self.RedefineImage(item["imageSrc"])
                db_setArt(itemid, "fanart", img)    
            elif "image" in item:
                img = self.RedefineImage(item["image"]["url"], 640)
                db_setArt(itemid, "thumb", img)   
                img = self.RedefineImage(item["image"]["url"])
                db_setArt(itemid, "fanart", img)                   
                                                
            db_addFolder(            
                itemid,
                parent,
                verb,
                title,
                subdetailurl,
                iorder,
                1,
                content
            ) 
            db.commit()       
    	
    def getDetails(self, cnt):
        if "state" in cnt:
            state = cnt["state"]
            details = state['detail']
            if 'detail' in details:
                details = details['detail']
            # headerDetail contains sometimes gtis/asins, which are not included in details
            if 'headerDetail' in state['detail']:
                details.update(state['detail']['headerDetail'])
                del state['detail']['headerDetail']
            if 'btfMoreDetails' in state['detail']:
                del state['detail']['btfMoreDetails']
            return details
        else:
            return None

    def parseMovie(self,itemid, cnt):                
        g = Globals()
        db = g.db()        
        arttypes = {'packshot':'thumb', 'covershot':'poster', 'heroshot':'fanart'}   
        state = cnt["state"]
        if "collections" in state:
            ## self.parseSeason(cnt)
            pass
        else:
            ##detail = state["detail"]["headerDetail"][itemid]
            details = self.getDetails(cnt)         
            if itemid in details:   
                detail = details[itemid]
                for type in detail["images"]:
                    if type in arttypes:
                        db_setArt(itemid,arttypes[type],detail["images"][type])                
                releaseYear = None
                if "releaseYear" in detail:
                    releaseYear = detail["releaseYear"]
                db.beginTransaction()          
                db.replace("movies",
                ("id","title","duration","plot","releaseyear"),
                (itemid,detail["title"],detail["runtime"],detail["synopsis"],releaseYear),
                "WHERE id='%s'" % (db.escape(itemid),)
                )  
                db.commit()
                return "movie"      
            else:
                warnings.warn("NOT MOVIE CATALOG-TYPE!!!")
                warnings.warn(json.dumps(details))

    def parseSeries(self, seriesid):
        db = g.db()
        # Parse last season
        data = db.select("seasons",("id","detailurl"),"WHERE seriesid='%s' LIMIT 1" % (db.escape(seriesid)))
        cnt = GrabJSON(data[0][1])
        self.parseSeason(cnt)        
        db.beginTransaction()
        self.setExtendedInfo(data[0][0],cnt)
        db_setSync(data[0][0])
        db.commit()
        ## parse all other seasons
        data = db.select("seasons",("id","detailurl"),"WHERE seriesid='%s' AND id!='%s'" % (db.escape(seriesid), db.escape(data[0][0])))
        for series in data:
            cnt = GrabJSON(series[1])
            self.parseSeason(cnt)
            db.beginTransaction()
            self.setExtendedInfo(series[0],cnt)
            db_setSync(series[0])            
            db.commit()
        db.beginTransaction()
        db_setSync(seriesid)
        db.commit()




    def parseSeason(self, cnt):
        if not("state" in cnt):
            return
        state = cnt["state"]
        details = self.getDetails(cnt)
        db = g.db()
        detail = details[state["pageTitleId"]]           
        
        arttypes = {'packshot':'thumb', 'covershot':'poster', 'heroshot':'fanart'}
        for type in detail["images"]:
                if type in arttypes:
                    db_setArt(detail["catalogId"],arttypes[type],detail["images"][type])
                
        link = ""
        if "seasons" in state:
            for gti in state["self"]:
                episode = state["self"][gti]
                if episode["titleType"] == "episode":
                    compactgti = episode["compactGTI"]
                    asin = episode["asins"][0]
                    seriesid = self.parseEpisode(detail["catalogId"], gti, compactgti, asin)  
                else:
                    pass
            updateseries = False
            if not db.exists("seasons",("WHERE seriesid='%s'" % (seriesid,))):                
                updateseries = True      
            else:
                updateseries = db.exists("folders","WHERE id='%s' AND detailurl IS NOT NULL" % (seriesid,))


            for season in state["seasons"][state["pageTitleId"]]:
                ##season = state["seasons"][state["pageTitleId"]][seasonid]
                link = season["seasonLink"]
                db.beginTransaction()
                db.replace("seasons",("id", "seriesid","detailurl"),
                    (season["seasonId"],seriesid,season["seasonLink"]),
                    "WHERE id='%s'" % (season["seasonId"])
                )    
                db.commit()

            if updateseries:
                db.beginTransaction()
                db.replace("folders",("detailurl",),(None,),"WHERE id='%s'" % db.escape(seriesid,))
                db.commit()
                self.parseSeries(seriesid)  
                return seriesid                                                              
            db.beginTransaction()
            db.replace("seasons",
                ("id","seriesid","seasonnumber","releasedate","releaseyear","plot"),
                (detail["catalogId"],seriesid,detail["seasonNumber"],detail["releaseDate"],
                detail["releaseYear"],detail["synopsis"]),
                "WHERE id='%s'" % (detail["catalogId"])
            )            
            db_addFolder(detail["catalogId"],seriesid,"pv/browse/"+detail["catalogId"],detail["title"],
            link,detail["seasonNumber"],1, "season")            
            db_setSync(detail["catalogId"])        
            db.commit()
            return seriesid
        else:
            ## Not a TV-Show, Live-Event?
            return None
    
    def parseEpisode(self,seasonid, id, compactgti, asin):
        db = g.db()        
        data = db.select("episodes",("id", "seasonsid", "seriesid"),"WHERE id='%s'" % (db.escape(id),))
        if len(data)==0:
            urldata = getURLData('catalog/GetPlaybackResources', id, silent=True, extra=True, useCookie=True,
                    opt='&titleDecorationScheme=primary-content', dRes='CatalogMetadata')            
            episode = urldata[1]["catalogMetadata"]
            family = episode["family"]
            db.beginTransaction()
            for tv in family["tvAncestors"]:
                if tv["catalog"]["type"]=="SHOW":
                    db.replace("series",("id", "title"), 
                      (tv["catalog"]["id"], tv["catalog"]["title"]),
                      "where id='%s'" % (db.escape(tv["catalog"]["id"]),)
                    )
                    seriesid =  tv["catalog"]["id"]                    
            db.replace("episodes",
                ("id","seasonsid","seriesid","episodenumber","title","plot","duration","isplayable"),
                (episode["catalog"]["id"],seasonid, seriesid, episode["catalog"]["episodeNumber"],
                 episode["catalog"]["title"], episode["catalog"]["synopsis"],episode["catalog"]["runtimeSeconds"], int(episode["playback"]["summary"]["isPlayable"])),
                "WHERE id='%s'" % (db.escape(episode["catalog"]["id"],))
            )
            arttypes = {'episode':'thumb', 'title':'poster', 'hero':'fanart'}
            for type in episode["images"]["imageUrls"]:
                    if type in arttypes:
                        db_setArt(episode["catalog"]["id"],arttypes[type],episode["images"]["imageUrls"][type])
            verb = '?mode=PlayVideo&name={}&asin={}{}'.format(compactgti, asin, "")
            db_addFolder(episode["catalog"]["id"],seasonid,verb, episode["catalog"]["title"], 
              "", episode["catalog"]["episodeNumber"],1, 'episode')
            db_setSync(episode["catalog"]["id"])
            db.commit()
            return seriesid
        else:
            return data[0][2]
        

    def _AddDirectoryItem(self, title, artmetadata, verb):
        item = xbmcgui.ListItem(title)
        item.setArt(artmetadata)
        item.setInfo('video', {"plot": "-"})
        xbmcplugin.addDirectoryItem(
            self._g.pluginhandle, 
            self._g.pluginid + verb, 
            item, 
            isFolder=True)
        return item

    def _UpdateProfiles(self, data):
        db = g.db()
        
        if 'cerberus' in data:
            p = data['cerberus']['activeProfile']
            dt = time.time()
            dt = int(dt)            
            db.beginTransaction()
            db.replace("profiles",
                ("id","name","agegroup","switchlink","lastsync"),
                (p['id'],p["name"],p["ageGroup"], json.dumps(p['switchLink']), dt),
                "WHERE id='%s'" % (p['id'],))             
            self._catalog['profiles'] = {'active': p['id']}
            self._catalog['profiles'][p['id']] = {
                'title': p['name'],
                'metadata': {'artmeta': {'icon': p['avatarUrl']}},
                'verb': 'pv/profiles/switch/{}'.format(p['id']),
                'endpoint': p['switchLink']      
            }                  

            if 'otherProfiles' in data['cerberus']:
                for p in data['cerberus']['otherProfiles']:
                    db.replace("profiles",
                        ("id","name","agegroup","switchlink","lastsync"),
                        (p['id'],p["name"],p["ageGroup"], json.dumps(p['switchLink']), dt),
                        "WHERE id='%s'" % (p['id'],))                                 
                    self._catalog['profiles'][p['id']] = {
                        'title': p['name'],
                        'metadata': {'artmeta': {'icon': p['avatarUrl']}},
                        'verb': 'pv/profiles/switch/{}'.format(p['id']),
                        'endpoint': p['switchLink'],
                    }        
            db.commit()

    def WatchList(self, mediaid):
        cookie = MechanizeLogin()
        if not cookie:
            return
        db = g.db()
        data = db.select("folders",("id, content", "title", "detailurl",),"WHERE id='"+db.escape(mediaid)+"'" )              
        cnt = GrabJSON(data[0][3]) 
        #em = data["enrichments"]
        
        if "state" in cnt:
            if "watchlist" in cnt["state"]:
                for wl in cnt["state"]["watchlist"]:
                    watchlist = cnt["state"]["watchlist"][wl]                    
                    endp = watchlist["endpoint"]
                    action = watchlist["tag"]
                    url = self._g.BaseUrl + endp.get('partialURL')
                    query = endp.get('query')
                    query['tag'] = action
                    data = getURL(url, postdata=query, useCookie=cookie, check=True)
                    if data=="OK":
                        self._g.dialog.notification(self._g.addon.getAddonInfo('name'), 'Watchlist updated', time=1000, sound=False)
                        folders = db.select("folderhierarchy fh LEFT JOIN folders f ON fh.parentid=f.id",("fh.id",),"WHERE f.content='watchlist'")
                        for folder in folders:
                            db_setSync(folder[0], 0)
                        self.GetExtendedInfo(mediaid)
                        xbmc.executebuiltin('Container.Refresh')
                    else:
                        self._g.dialog.notification(self._g.addon.getAddonInfo('name'), 'Error', time=1000, sound=False)

    def Route(self, verb, path):        
        if 'search' == verb: g.pv.Search()
        elif 'browse' == verb: g.pv.Browse(path)
        elif 'refresh' == verb: g.pv.Refresh(path)
        elif 'profiles' == verb: g.pv.Profile(path)
        elif 'languageselect' == verb: g.pv.LanguageSelect()
        elif 'clearcache' == verb: g.pv.DeleteCache()
        elif 'more' == verb: g.pv.Info(path)        
        pass

    def Profile(self, path):
        """ Profile actions """
        path = path.split('/')

        def List():
            db = g.db()
            """ List all inactive profiles """
            # Hit a fast endpoint to grab and update CSRF tokens
            home = GrabJSON(self._g.BaseUrl + '/gp/video/profiles')
            db.beginTransaction()
            self._UpdateProfiles(home)
            db.commit()
            for k, p in self._catalog['profiles'].items():
                if 'active' == k or k == self._catalog['profiles']['active']:
                    continue
                self._AddDirectoryItem(p['title'], p['metadata']['artmeta'], p['verb'])
            xbmcplugin.endOfDirectory(self._g.pluginhandle, succeeded=True, cacheToDisc=False, updateListing=False)

        def Switch():
            db = g.db()
            """ Switch to an inactive profile """
            # Sometimes the switch just fails due to CSRF, possibly due to problems on Amazon's servers,
            # so we patiently try a few times
            for _ in range(0, 5):
                endpoint = self._catalog['profiles'][path[1]]['endpoint']
                Log('{} {}'.format(self._g.BaseUrl + endpoint['partialURL'], endpoint['query']))
                home = GrabJSON(self._g.BaseUrl + endpoint['partialURL'], endpoint['query'])
                db.beginTransaction()
                self._UpdateProfiles(home)
                db.commit()
                if path[1] == self._catalog['profiles']['active']:
                    break
                sleep(3)
            if path[1] == self._catalog['profiles']['active']:
                self.BuildRoot(home if home else {})
            else:
                self._g.dialog.notification(self._g.addon.getAddonInfo('name'), 'Profile switching unavailable at the moment, please try again', time=1000, sound=False)
            xbmcplugin.endOfDirectory(self._g.pluginhandle, succeeded=False, cacheToDisc=False, updateListing=True)

        if 'list' == path[0]: List()
        elif 'switch' == path[0]: Switch()

    def DeleteCache(self):
        """ Pops up a dialog asking cache purge confirmation """
        
        self._catalog = {}            
        Log('Deleting catalog', Log.DEBUG)

        

    def LanguageSelect(self):
        cj = MechanizeLogin()
        if cj:
            l = cj.get('lc-main-av', path='/')
        presel = [i for i, x in enumerate(self._languages) if x[0] == l]
        sel = self._g.dialog.select(getString(30133), [x[1] for x in self._languages], preselect=presel[0] if presel else -1)
        if sel < 0:
            self._g.addon.openSettings()
        else:
            Log('Changing text language to [{}] {}'.format(self._languages[sel][0], self._languages[sel][1]), Log.DEBUG)
            cj.set('lc-main-av', self._languages[sel][0], path='/')
            saveUserCookies(cj)
            self.DeleteCache()

    def BrowseRoot(self):
        """ Build and load the root PrimeVideo menu """

        self.Browse('root')

    def BuildRoot(self, home=None):
        db = self._g.db()
        """ Parse the top menu on primevideo.com and build the root catalog """
        db.beginTransaction()
        db_addFolder("root","","","Amazon Prime Video","BuildRoot",1,1,"root")
        db_setSync("root")
        db.commit()

        # Specify `None` instead of just not empty to avoid multiple queries to the same endpoint
        
        home = GrabJSON(self._g.BaseUrl)
        self._UpdateProfiles(home)      

        warnings.warn(json.dumps(home))      

        # Insert the watchlist
        db.beginTransaction()
        ordernr = 0
        watchlist = next((x for x in home['yourAccount']['links'] if '/watchlist/' in x['href']), None)        
        if watchlist != None:
            ordernr = ordernr +1
            db_addFolder("watchlist","root","pv/browse/watchlist",watchlist['text'], FQify(watchlist['href']), ordernr, 1, "watchlist")
    
        watchlist = next((x for x in home['mainMenu']['links'] if 'pv-nav-mystuff' in x['id']), None)
        if watchlist != None:   
            ordernr = ordernr +1                     
            db_addFolder("watchlist","root","pv/browse/watchlist",watchlist['text'], watchlist['href'], ordernr, 1, "watchlist")        

        # Insert the main sections, in order
        try:
            navigation = home['mainMenu']['links']
            
            for link in navigation:                
                # Skip watchlist
                detailurl = link['href']
                if 'pv-nav-mystuff' == link['id']:
                    continue
                id = self.genID(self._BeautifyText(link['text']))
                if "links" in link:
                    cn = 0
                    db.update("folderhierarchy",("active",),(0,),"WHERE parentid='%s'" % id)
                    for sublink in link["links"]:
                        
                        cn += 1
                        subid = id+'/'+self._BeautifyText(sublink['text'])
                        detailurl = ""
                        db_addFolder(subid, id, "pv/browse/"+subid, self._BeautifyText(sublink['text']), sublink['href'],cn, 1, "folder")                       
                ordernr = ordernr +1
                
                db_addFolder(id, "root", "pv/browse/"+id, self._BeautifyText(link['text']), detailurl,ordernr, 1, "folder")                

        except:
            self._g.dialog.notification(
                'PrimeVideo error',
                'You might be unable to access the service: check the website www.primevideo.com for more information'
                '' if 'cerberus' in home else ''
                'Unable to find the navigation menu for primevideo.com',
                xbmcgui.NOTIFICATION_ERROR
            )
            Log('Unable to parse the navigation menu for primevideo.com', Log.ERROR)
            return False
        
        ##Insert the searching mechanism
        try:
            sfa = home['searchBar']['searchFormAction']
            # Build the query parametrization
            query = ''
            if 'query' in sfa:
                query += '&'.join(['{}={}'.format(k, v) for k, v in sfa['query'].items()])
            query = query if not query else query + '&'
            ordernr = ordernr +1
            db_addFolder("search", "root", "pv/browse/search",self._BeautifyText(home['searchBar']['searchFormPlaceholder']),"",ordernr,1,"search")
            db_addFolder("dosearch", "search", 'pv/search/', self._BeautifyText(home['searchBar']['searchFormPlaceholder']), 
            '{}?{}phrase={{}}'.format(sfa['partialURL'], query),1, 1, "search")
            
        except:
            Log('Search functionality not found', Log.ERROR)
        
        db.commit()
        return True

    def GetExtendedInfoFromDB(self, itemid, path=None):
        tag = None
        db = self._g.db() 
        data = db.select("folders",("id, content", "title", "detailurl",),"WHERE id='"+db.escape(itemid)+"'" )  
        item = data[0]
        watchlist = None
        extid = itemid
        isPlayable = False
        isFolder = True
        infolabels = {
            "plot": "-"
        }
        if item[1]=="movie":
            isFolder=False
            data =  db.select("movies",("title","releaseyear","plot","duration", "isPlayable"),"WHERE id='%s'" % db.escape(item[0],))
            if len(data)>0:
                infolabels = {
                    'mediatype': "movie",
                    'title': data[0][0],
                    'year': data[0][1],
                    "plot": data[0][2] or "-",
                    "duration": data[0][3],                    
                }
                isPlayable = data[0][4]!=0
        elif item[1]=="series":
            data =  db.select("series",("title",),"WHERE id='%s'" % db.escape(item[0],))
            ## Use plot from last season
            season =  db.select("series se LEFT JOIN seasons s ON s.seriesid=se.id",
                ("s.plot","s.id"),
                "WHERE se.id='%s' ORDER BY s.seasonnumber DESC LIMIT 1" % db.escape(item[0],))
            if (len(data)>0) and (len(season)): 
                extid = season[0][1]
                infolabels = {
                    'mediatype': "tvshow",
                    'title': data[0][0],
                    'plot': season[0][0] or "-"
                }
        elif item[1]=="season":
            data =  db.select("seasons s LEFT JOIN series se ON s.seriesid=se.id",
                ("s.seasonnumber","s.releasedate","s.releaseyear","s.plot",'se.title'),
                "WHERE s.id='%s'" % db.escape(item[0],))
            if len(data)>0:  
                infolabels = {
                    'mediatype': "season",                    
                    'season': data[0][0],
                    'year': data[0][2],
                    'plot': data[0][3] or "-",
                    'tvshowtitle': data[0][4]
                }
        elif item[1]=="episode":                            
            isFolder=False
            data =  db.select("episodes e LEFT JOIN seasons s ON e.seasonsid=s.id LEFT JOIN series se ON s.seriesid=se.id",
            ("s.seasonnumber","e.episodenumber","e.plot","se.title", "e.duration","s.id","e.isPlayable"),
            "WHERE e.id='%s'" % db.escape(item[0],))            
            if len(data)>0: 
                extid = data[0][5]
                title = item[2]
                isPlayable = data[0][6]!=0
                if not isPlayable:
                    title = "[COLOR FFFF5550]"+title+"*[/COLOR]"                 
                infolabels = {
                    'mediatype': "episode",
                    'title': title,
                    'episode': data[0][1],  
                    'season': data[0][0],                                                                   
                    'plot': data[0][2] or "-",
                    'tvshowtitle': data[0][3],
                    'duration': data[0][4]
                }
                isPlayable = data[0][6]!=0
        if extid!=None: 
            genres = db.select("moviegenres mg INNER JOIN genres g ON mg.genresid=g.id",
            ("g.id","g.text"),
            "WHERE mg.mediaid='%s'" % db.escape(extid)
            )
            if len(genres)>0:
                infolabels["genre"] = []
                for genre in genres:                                         
                    infolabels["genre"].append(genre[1])
            
            watchlistdata = db.select("watchlist w INNER JOIN folders f ON w.id=f.id",
                ("w.id", "w.tag","f.title"),
                "WHERE w.id='%s'" % db.escape(extid)
            )
            if len(watchlistdata)>0:
                watchlist = watchlistdata[0]                


        title = item[2]                    
        if (item[1]=="movie") or (item[1]=="episode"):
            if not isPlayable:
                title = "[COLOR FFFF5550]"+title+"[/COLOR]"        
        li = xbmcgui.ListItem(title, path=path)
        art = db_getArt(itemid)
        
        li.setArt(art)
        li.setContentLookup(False)
        li.setInfo('video', infolabels)

        cmactions = []
        if isPlayable==True:
            li.setProperty('IsPlayable', 'true')                
        if (path ==None) and ((item[1]=="movie") or (item[1]=="episode")or (item[1]=="season")):
            cmactions.append(
                ("Infos", "RunPlugin("+self._g.pluginid +"pv/more/"+item[0]+")")
            )    
        if (path ==None) and ((item[1]=="folder") or (item[1]=="series") or (item[1]=="watchlist")):
            cmactions.append(
                ("Refresh", "RunPlugin("+self._g.pluginid +"?mode=refreshfolder&foldersid="+item[0]+")")
            )    
        if (path==None) and (watchlist != None):
            tag = watchlist[1]
        ## Look in watchlist-folders
        if(tag==None) and (path==None) and ((item[1]=="movie") or (item[1]=="episode")or (item[1]=="season")):
            watchlists = db.select("""folders f
                LEFT JOIN folderhierarchy fh ON fh.id=f.id
                LEFT JOIN folders fw ON fw.id=fh.parentid
                LEFT JOIN folderhierarchy fhw ON fhw.id=fw.id
                LEFT JOIN folders wl ON wl.id=fhw.parentid AND wl.content='watchlist'""",
                ("f.id","wl.id","f.title"),
                "WHERE f.id='%s' ORDER by wl.id DESC" % (db.escape(extid),))            
            if len(watchlists)>0:
                watchlist = watchlists[0]
                if watchlist[1] is None:
                    tag = "Add"
                else:
                    tag = "Remove"        
        if tag != None:
            if tag=="Add":
                cmactions.append(
                    (getString(30180) % (watchlist[2]), "RunPlugin("+self._g.pluginid +"?mode=WatchList&mediaid="+watchlist[0]+")")
                )
            else:
                cmactions.append(
                    (getString(30181) % (watchlist[2]), "RunPlugin("+self._g.pluginid +"?mode=WatchList&mediaid="+watchlist[0]+")")
                )                

        if len(cmactions)>0:
            li.addContextMenuItems(cmactions)
        return (li, isFolder, isPlayable)

    def setExtendedInfo(self, itemid, cnt):
        ## Call inside a transaction!
        db = self._g.db()
        details = self.getDetails(cnt)            
        detail = details[itemid]            
        if "state" in cnt:
            if "watchlist" in cnt["state"]:
                for wl in cnt["state"]["watchlist"]:
                    watchlist = cnt["state"]["watchlist"][wl]["endpoint"]
                    db.replace("watchlist",
                        ("id","tag","returnurl","token","partialurl","titleid"),
                        (wl, watchlist["query"]["tag"],watchlist["query"]["returnUrl"],watchlist["query"]["token"],watchlist["query"]["titleID"], watchlist["partialURL"]),
                        "WHERE id='%s'" % (db.escape(wl),)
                    )
        if "studios" in detail:
            for studio in detail["studios"]:
                db.replace("moviestudios",
                    ("mediaid","title"),
                    (itemid,studio),
                    "WHERE mediaid='%s' AND title='%s'" % (db.escape(itemid),db.escape(studio))
                )
        if "genres" in detail:
            db.delete("moviegenres","WHERE mediaid='%s'" % (db.escape(itemid),))
            for genre in detail["genres"]:
                db.replace("genres",
                    ("id","text","detailurl"),
                    (genre["id"],genre["text"],genre["searchLink"]),
                    "WHERE id='%s'" % (db.escape(genre["id"]),)
                )
                db.replace("moviegenres",
                    ("mediaid","genresid"),
                    (itemid, genre["id"]),
                    "WHERE mediaid='%s' and genresid='%s'" % (itemid, db.escape(genre["id"]),)
                )                    

    def GetExtendedInfo(self, compactgti, path=None):
        def Bool2Int(b):
            if b in detail:
                if detail[b]:
                    return 1
                else:
                    return 0
            else:
                return 0
        
        def GetData(b):
            if b in detail:
                return detail[b]
            else:
                return None
        
        db = self._g.db()        
        ## movie:
        data = db.select("folders",("id, content", "title", "detailurl",),"WHERE id='"+db.escape(compactgti)+"'" )          
        if len(data)==0: ## episode:
            ## ?mode=PlayVideo&name=0K66WS6AYTWV042PO8FTCANIH8&asin=B08LXP4PXJ
            data = db.select("folders",("id, content", "title", "detailurl",),"WHERE verb like '%"+db.escape(compactgti)+"%'" )                         
        item = data[0]                        
        itemid = item[0]
       
        if item[3]!="": ## episodes detail url?
            cnt = GrabJSON(item[3])                            
            details = self.getDetails(cnt)            
            detail = details[itemid]            
            imdb = None
            if "imdb" in cnt:
                imdb = cnt["state"]["imdb"][itemid]["score"]
            db.beginTransaction()        
            db.replace("extendedinfo",
                ("id","releasedate","releaseyear", "duration","rating","isPrime","isXRay","isClosedCaption","titletype"),
                (itemid, GetData("releaseDate"),GetData("releaseYear"), GetData("duration"),imdb,
                Bool2Int("isPrime"), Bool2Int("isXRay"), Bool2Int("isClosedCaption"),detail["titleType"]),
                "WHERE id='%s'" % (db.escape(itemid), )
            )
            self.setExtendedInfo(itemid, cnt)
            db.commit()

        data = self.GetExtendedInfoFromDB(itemid, path)                
        return data[0]


    def Info(self, path):       
        li = self.GetExtendedInfo(path)                
        ##self.GetExtendedInfo(path)
        dialog = xbmcgui.Dialog()
        return dialog.info(li)


    def Browse(self, path, doRefresh=False):
        """ Display and navigate the menu for PrimeVideo users """
        if path==None:
            path="root"
        path = path.replace("/page-","#")
        offset = path.find('#')
        pagination = self._s.pagination
        maxresults = self._s.MaxResults
        limit = ""        
        if offset>-1:
            page = (int)(path[offset+1:])
            path = path[:offset]
        else:
            page = 1 
        
        self.syncContent(path, doRefresh)        
        
        db = self._g.db()
        parent = db.select("folders",("content","title","verb"),"WHERE id='%s'" % (db.escape(path)))
        if len(parent)==0:
            return
        doPaginate = (
            (pagination["all"]) 
            or (pagination["search"] and (parent[0][0] == "search"))
            or (pagination["collections"] and (parent[0][0] == "folder"))
            or (pagination["watchlist"] and (parent[0][0] == "watchlist")) ## watchlist is grandparent folder?
            )
        if doPaginate:
            limit = " LIMIT %i, %i" %((page-1)*maxresults, maxresults+1)            

        if parent[0][0] in ["search","episode","season","series","root"]:
            items = db.select("folders f INNER JOIN folderhierarchy h ON f.id=h.id",
                ("f.id","f.title","f.verb","f.content"),
                "WHERE h.parentid='%s' AND h.active=1 ORDER BY h.ordernr %s" % (db.escape(path),limit))
        else:
            items = db.select("folders f INNER JOIN folderhierarchy h ON f.id=h.id",
                ("f.id","f.title","f.verb","f.content"),
                "WHERE h.parentid='%s' AND h.active=1 ORDER BY f.title %s" % (db.escape(path),limit))
        if len(parent)==0:
            return
        if parent[0][0] == "series":
            xbmcplugin.setContent(self._g.pluginhandle,"seasons")            
        if parent[0][0] == "season":
            xbmcplugin.setContent(self._g.pluginhandle,"episodes")
        else:
            xbmcplugin.setContent(self._g.pluginhandle,"videos")

        if parent[0][0] in ['movie', 'season', 'episode','series']:            
            xbmcplugin.addSortMethod(self._g.pluginhandle, xbmcplugin.SORT_METHOD_EPISODE) if parent[0][0] == 'season' else None            
            xbmcplugin.addSortMethod(self._g.pluginhandle, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
            ##xbmcplugin.addSortMethod(self._g.pluginhandle, xbmcplugin.SORT_METHOD_LASTPLAYED)
            ##xbmcplugin.addSortMethod(self._g.pluginhandle, xbmcplugin.SORT_METHOD_PLAYCOUNT)
        itemcount = 0
        for item in items:               
            itemcount = itemcount +1
            if (itemcount>maxresults) and (doPaginate):                
                self._AddDirectoryItem(getString(30242).format(page+1), None, parent[0][2]+'/page-'+str(page+1))                
            else:
                data = self.GetExtendedInfoFromDB(item[0])
                
                xbmcplugin.addDirectoryItem(
                    self._g.pluginhandle, 
                    self._g.pluginid + item[2], 
                    data[0], 
                    isFolder = data[1]
                )
                

        # Add multiuser menu if needed
        if (self._s.multiuser) and ('root' == path) and (1 < len(loadUsers())):
            li = xbmcgui.ListItem(getString(30134).format(loadUser('name')))
            li.addContextMenuItems(self._g.C, li, isFolder=False)
        if ('root' + self._separator + 'SwitchUser') == path:
            if switchUser():
                self.BuildRoot()
            return

        # Add Profiles
        #if self._s.profiles and ('root' == path) and ('profiles' in self._catalog):
        #    activeProfile = self._catalog['profiles'][self._catalog['profiles']['active']]
        #    self._AddDirectoryItem(activeProfile['title'], activeProfile['metadata']['artmeta'], 'pv/profiles/list')

        xbmcplugin.endOfDirectory(self._g.pluginhandle, succeeded=True, cacheToDisc=False, updateListing=False)

    def Search(self, searchString=None):
        """ Provide search functionality for PrimeVideo """
        if searchString is None:
            searchString = self._g.dialog.input(getString(24121)).strip(' \t\n\r')
        if 0 == len(searchString):
            xbmcplugin.endOfDirectory(self._g.pluginhandle, succeeded=False)
            return
        Log('Searching "{}"…'.format(searchString), Log.INFO)
        searchid = self.genID(searchString)
        db = self._g.db()
        data = db.select("folders",("detailurl",), "WHERE id='dosearch'")
        if len(data)>0:
            endpoint = data[0][0]
            db.beginTransaction()            
            db.execute("UPDATE folderhierarchy SET ordernr=ordernr+1 WHERE parentid='search' AND ordernr>1")  
            ##only save the last 20 items
            db.delete("folderhierarchy", "WHERE parentid='search' AND ordernr>20")   
            db_addFolder('search-'+searchid, "search", "pv/browse/search-"+searchid,
                searchString,endpoint.format(searchString),2,1,"search")
            db.commit()            
            self.Browse("search-"+searchid)

