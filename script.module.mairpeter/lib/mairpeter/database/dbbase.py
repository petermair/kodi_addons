from abc import abstractmethod

class BaseDB(object):
    
    def __init__(self):              
        self._conn = None
        self._cursor = None 
        self._dbtype = "unknown"
        self._tablereplace = {}    
    
    def AddTableReplace(self, tablename, replacename):
        self._tablereplace[tablename] = replacename

    def ReplaceTableName(self, tablename):        
        for tn in self._tablereplace:
            if tn == tablename:
                return self._tablereplace[tn]
        return tablename

    @abstractmethod
    def connect(self, config):
        pass        

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def beginTransaction(self):
        pass     

    @abstractmethod
    def commit(self):
        pass

    @abstractmethod
    def rollback(self):
        pass

    @abstractmethod
    def createTable(self, tablename, definition):
        pass

    @abstractmethod
    def select(self, tablename, fieldnames, wheresql = ""):
        pass

    @abstractmethod
    def insert(self, tablename, fieldnames, values):
        pass

    @abstractmethod
    def update(self, tablename, fieldnames, values, wheresql = ""):
        pass

    @abstractmethod
    def delete(self, tablename,wheresql = ""):
        pass    

    @abstractmethod
    def execute(self, cmd):
        pass
        
    def replace(self, tablename, fieldnames, values, wheresql = ""):
        data = self.select(tablename, "*", wheresql)
        if len(data)==0:            
            self.insert(tablename, fieldnames, values)
        else:
            self.update(tablename, fieldnames, values, wheresql)            

    def exists(self, tablename, wheresql = ""):
        data = self.select(tablename, ("count(*)",), wheresql)
        return data[0][0]>0

    @abstractmethod
    def TableList(self):
        pass

    @property
    def conn(self):        
        return self._conn

    @property
    def cursor(self):        
        return self._cursor

    @property 
    def dbtype(self):    
        return self._dbtype
    
    @abstractmethod
    def escape(self, str):
        pass


