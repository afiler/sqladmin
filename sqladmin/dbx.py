import django.db

DEFAULT_PK='id'

def quote_table(db, table):
    return Conn.quote_table(db, table)

def fetch_hash(*args, **kw):
    return Conn().fetch_hash(*args, **kw)

def fetch(*args, **kw):
    return Conn().fetch(*args, **kw)

def table(*args, **kw):
    return Conn().table(*args, **kw)

class QueryError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Conn(object):
    def __init__(self, conn=None):
        if conn is not None:
            self.dbconn = conn
        else:
            self.dbconn = django.db.connection

        self._dbs = None

    def execute(self, query, args=[]):
        cursor = self.dbconn.connection.cursor()
        args = [x.encode('utf-8') for x in args]
        #print q
        #print args
        try:
            return cursor.execute(query, args)
        except Exception as err:
            raise QueryError(str(err))

    def fetch_hash(self, q, args=[], **kw):
        return self.fetch(q, args, hash=True, **kw)

    def fetch_one(self, q, args=[], **kw):
        return self.fetch(q, args, fetch_one=True, **kw)

    def fetch(self, q, args=[], hash=False, fetch_one=False, db=None, return_columns=False, **kw):
        c = self.dbconn.connection.cursor()
        #if db:
        #    c.execute(('use %s' % self.quote_db(db)).encode('utf-8'))
        args = [x.encode('utf-8') for x in args]
        #print repr(q % args)
        #print repr(args)
        try:
            c.execute(q.encode('utf-8'), args)
        except Exception as err:
            raise QueryError(str(err))

        if fetch_one:
            result = c.fetchone()
            ##print '*** fetchone result %s' % result
            if hash:
                return dict(zip([col[0] for col in c.description], result))
            else:
                return result
        else:
            result = c.fetchall()
            ##print '*** fetchall result %s' % result
            if hash:
                return [dict(zip([col[0] for col in c.description], row)) for row in result]
            elif return_columns:
                columns = [[col[0], col[1].__name__, (col[3] or 40)/4, col[6]] for col in c.description]
                return [[dict(zip([col[0] for col in c.description], row)) for row in result], columns]
            else:
                return result

    def db(self, name):
        return DB(name, self)

    def table(self, db, table):
        return DB(db, self).table(table)

    #@property
    #def dbs(self):
    #    q = self.fetch('select name from master..sysdatabases order by name')
    #    return [{'name': x[0]} for x in q]

    @property
    def dbs(self):
        if self._dbs is not None:
            return self._dbs

        q = self.fetch('select name from master..sysdatabases order by name')
        self._dbs = [self.db(x[0]) for x in q]

        return self._dbs

    @classmethod
    def quote_name(cls, name):
        return '"%s"' % name.replace('"', '""')

    @classmethod
    def quote_db(cls, db):
        return '"%s"' % db.replace('"', '""')

    @classmethod
    def quote_table(cls, db, table):
        return '"%s".."%s"' % (db.replace('"', '""'), table.replace('"', '""'))

    @classmethod
    def quote_string(cls, s):
        return "'%s'" % s.replace("'", "''")

class DB(object):
    def __init__(self, name, conn=None):
        self.db_name = name
        self.conn = conn or Conn()

        self._tables = None
        self._views = None
        self._tables_and_views = None

    def __str__(self):
        return self.db_name

    def fetch(self, q, args=[]):
        return self.conn.fetch(q, args, db=self.db_name)

    @property
    def quoted_name(self):
        return self.conn.quote_db(self.db_name)

    @property
    def tables(self):
        if self._tables is not None:
            return self._tables

        try:
            q = self.fetch("select name from %s..sysobjects where xtype='U' order by name" % \
                    self.quoted_name)
            self._tables = [self.table(x[0], 'U') for x in q]
        except:
            self._tables = []
        return self._tables

    @property
    def views(self):
        if self._tables is not None:
            return self._tables

        try:
            q = self.fetch("select name from %s..sysobjects where xtype='V' order by name" % \
                    self.quoted_name)
            self._tables = [self.table(x[0], 'V') for x in q]
        except:
            self._tables = []
        return self._tables

    @property
    def tables_and_views(self):
        if self._tables is not None:
            return self._tables

        try:
            # Get PKs
            pks = {}
            db_name = self.quoted_name
            q = """select ku.table_name, ku.column_name from %s.information_schema.table_constraints as tc
                inner join %s.information_schema.key_column_usage as ku
                    on tc.constraint_type = 'primary key' and tc.constraint_name = ku.constraint_name
                where ku.table_catalog=?;""" % (db_name, db_name)
            for row in self.conn.fetch(q, (self.db_name,)): pks[row[0]] = row[1]
            #print pks
            # Get tables/views
            q = self.fetch("select name, xtype from %s..sysobjects where xtype in ('U', 'V') order by name" % \
                    self.quoted_name)
            self._tables = [Table(db=self, table=x[0], subtype=x[1], pk=pks.get(x[0], DEFAULT_PK)) for x in q]
        except:
            self._tables = []
        return self._tables

class Table(object):
    def __init__(self, db, table, subtype='U', pk=None):
        self.table_name = table
        if isinstance(db, basestring):
            db = DB(db)
        self.db = db
        self.db_name = db.db_name
        self.conn = db.conn
        self.subtype = 'view' if subtype.strip() in ('V', 'view') else 'table'
        #print '%s: %s - %s' % (table, subtype, self.subtype)
        self.writable = (self.subtype == 'view')
        self._pk = pk
        self._columns = None

    def __str__(self):
        return self.table_name

    def fetch_hash(self, *args, **kw):
        kw['db'] = self.db_name
        return self.conn.fetch_hash(*args, **kw)

    def fetch_rows(self, bottom=1, top=100):
        previous_top = bottom - 1
        count = top - previous_top
        pk = self.conn.quote_name(self.pk)
        table_name = self.quoted_name

        if previous_top < 1:
            q = 'select top %d * from %s' % (top, table_name)
        else:
            q = 'select top %d * from %s where %s not in (select top %s %s from %s)' % \
              (count, table_name, pk, previous_top, pk, table_name)
        return self.fetch_hash(q)

    @property
    def total_rows(self):
        return self.conn.fetch_one('select count(*) from %s' % self.quoted_name)[0]

    @property
    def pk(self):
        if self._pk is not None:
            return self._pk

        # XXX!
        try:
            db_name = self.db.quoted_name
            data = self.conn.fetch_one("""select ku.column_name from %s.information_schema.table_constraints as tc
              inner join %s.information_schema.key_column_usage as ku on tc.constraint_type = 'primary key'
                and tc.constraint_name = ku.constraint_name
              where ku.table_catalog=? and ku.table_name=?;""" % (db_name, db_name), (self.db_name, self.table_name))
            self._pk = data[0]
        except:
            self._pk = DEFAULT_PK

        return self._pk

    @property
    def quoted_name(self):
        return self.conn.quote_table(self.db_name, self.table_name)

    @property
    def columns(self):
        if self._columns is not None:
            return self._columns

        q = """select
                column_name as name,
                data_type,
                coalesce(numeric_precision, character_maximum_length, datetime_precision) as length,
                numeric_precision_radix,
                numeric_scale,
                column_default as "default",
                case is_nullable when 'YES' then 1 else 0 end as is_nullable
            from %s.information_schema.columns where table_name=?
            order by name""" % self.db.quoted_name

        self._columns = self.conn.fetch_hash(q, [self.table_name])
        return self._columns

class Query(object):
    def __init__(self):
        self.limit = 0
        self.offset = 0
        self.params = []

    def limit(self, i):
        self.limit = i

    def offset(self, i):
        self.offset = i

    @property
    def sql(self):
        pass

    def go(self):
        cursor = connection.cursor()
        cursor.execute(self.sql, self.params)

