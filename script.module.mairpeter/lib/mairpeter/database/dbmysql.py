from dbbase import BaseDB
import mysql.connector

class MySQLDB(BaseDB):
    
    def connect(self, config):
        self._dbtype = "mysql"
        if self._conn == None:                       
            self._conn = mysql.connector.Connect(
                **config
            )
            self._conn.autocommit = False

            self._cursor = self._conn.cursor()
    
    def disconnect(self):
        self._cursor.close()
        self._conn.close()

    
    def beginTransaction(self):        
        self._cursor.execute("START TRANSACTION")

    def commit(self):        
        self._cursor.execute("COMMIT")

    def rollback(self):
        self._cursor.execute("ROLLBACK")

    ## createTable(
    ##   tablename,
    ##   ({fieldname: "...", "fieldtype": "varchar", "fieldsize": 20, "notnull": True}),
    ##   (id, id2)
    ## )

    def createTable(self, tablename, definition, primarykey):
        sql = ""
        pk = ""        
        for fielddef in definition:
            if sql != "":
                sql = sql + ","
            sql = sql + "`"+fielddef["fieldname"]+"`"+' '+fielddef["fieldtype"]
            if fielddef["fieldsize"]>0:
              sql = sql + "("+str(fielddef["fieldsize"])+")"            
            if fielddef["notnull"] == True:
                sql = sql + " NOT NULL"

        for p in primarykey:
            if pk != "":
                pk = pk + ","
            pk = pk + "`"+p+"`"

        sql = sql = 'CREATE TABLE IF NOT EXISTS `'+tablename+'`(' + sql
        if pk != "":
            sql = sql + ", PRIMARY KEY("+pk+")"
        sql = sql + ") COLLATE 'utf32_unicode_ci'"        
        self._cursor.execute(sql)

    def select(self, tablename, fieldnames, wheresql = ""):
        tablename = self.ReplaceTableName(tablename)
        sql = ""
        for fieldname in fieldnames:
            if sql!="":
                sql = sql + ","            
            sql=sql + fieldname            
        sql = "SELECT "+sql+" FROM "+tablename+' '+wheresql        
        self._cursor.execute(sql)
        data = self._cursor.fetchall()
        return data


    def insert(self, tablename, fieldnames, values):
        tablename = self.ReplaceTableName(tablename)
        ins = ""
        val = ""
        for fieldname in fieldnames:
            if ins != "":
                ins = ins + ", "
                val = val + ", "
            ins=ins + "`"+fieldname+"`"
            val=val + "%s"
        sql = "INSERT INTO  `"+tablename+"`("+ins+") VALUES("+val+")"        
        self._cursor.execute(sql, values)
        return self._cursor.lastrowid


    def update(self, tablename, fieldnames, values, wheresql = ""):
        tablename = self.ReplaceTableName(tablename)            
        upd = ""
        for fieldname in fieldnames:
            if upd != "":
                upd = upd + ", "                
            upd=upd + "`"+fieldname+"`"+"=%s"
            
        sql = "UPDATE `"+tablename+"` SET "+upd+" "+wheresql
        self._cursor.execute(sql, values)

    def delete(self, tablename,wheresql = ""):
        tablename = self.ReplaceTableName(tablename)
        self._cursor.execute("DELETE FROM `"+tablename+"` "+wheresql)

    def execute(self, cmd):
        self._cursor.execute(cmd)

    def TableList(self):
        self._cursor.execute("show FULL tables where Table_Type != 'VIEW'")
        data = self._cursor.fetchall()
        return data
    
    def escape(self, str):
        str = str.replace("\\","\\\\")
        return str.replace("'","\\'")        
