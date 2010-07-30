import csv, re, json
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.template import RequestContext
from django.conf import settings
from imp5.sqladmin import dbx
import django.db.models.fields
from dojango.decorators import json_response, __prepare_json_ret
from dojango.util import json_encode
import datetime

TABLE_NAME_SEPARATOR='/'

#@staff_member_required
#def table(request, db, table):
#    print "Request: " + str(request)
#    conn = dbx.Conn()
#    data = conn.select(table, limit=100)
#    table_obj = conn.db(db).table(table)
#    context = {
#        'root_path': '/',
#        'table': table_obj, 'data': data, 'table_name': table, 'db_name': db,
#    }
#
#    return render_to_response("sqladmin/table.html", context, context_instance=RequestContext(request))

def debug(*msg):
    import logging
    logging.debug(''.join(msg))

@staff_member_required
@json_response
def database_tree(request):
    conn = dbx.Conn()
    return {
      'identifier': 'id',
      'label': 'name',
      'items': [
        { 'id': '.root', 'children': [
            {
              'id': str(db),
              'name': str(db),
              'type': 'database',
              'children': [{
                  'id': "%s%s%s" % (db, TABLE_NAME_SEPARATOR, table),
                  'name': str(table),
                  'type': 'table',
                  'subtype': table.subtype,
                  'writable': table.writable,
                } for table in db.tables_and_views if str(table)[0] != '_']
            } for db in conn.dbs if db.tables_and_views]
        }]
      }

@staff_member_required
@json_response
def tables(request, db=None, table=None, table_id=None):
    table_id = table_id or request.REQUEST.get('table_id', None)
    if not table_id:
        return HttpResponseBadRequest()
    db_name, table_name = table_id.split(TABLE_NAME_SEPARATOR)
    table = dbx.Table(db=db_name, table=table_name)
    return {
      'table_id': table_id,
      'pk': table.pk,
      'columns': [{
            'id': table_id+TABLE_NAME_SEPARATOR+col['name'],
            'table_id': table_id,
            'name': col['name'],
            'type': 'column',
            'data_type': col['data_type'],
            'data_length': col['length'],
            'default': col['default'],
            'is_nullable': col['is_nullable']
        } for col in table.columns]
    }

@staff_member_required #@json_response
def fetch(request, db=None, table=None):
    debug(repr(request))
    q = request.REQUEST.get('q', None)
    callback_param_name = request.REQUEST.get('callback', None)
    #items = re.match('items=(\d+)-(\d+)', request.META.get('Range', ''))
    #start = items and items.group(1)
    #stop = items and items.group(2)
    ##return dbx.fetch_hash(q, start=start, stop=stop)
    items = re.match('items=(\d+)-(\d+)', request.META.get('HTTP_RANGE', ''))
    if items:
        bottom = int(items.group(1))
        top = int(items.group(2))
    else:
        #return HttpResponseBadRequest()
        bottom = 1
        top = 100

    try:
        if db and table:
            table = dbx.Table(db=db, table=table)
            data = table.fetch_rows(bottom, top)
        elif q:
            result = dbx.fetch(q, bottom=bottom, top=top, return_columns=True)
            data = {
                'columns': result[1],
                'data': result[0],
            }
            #data = dbx.fetch_hash(q, bottom=bottom, top=top)
    except dbx.QueryError as error:
        return HttpResponseBadRequest(str(error))

    data = json_encode(data)
    if callback_param_name:
        data = "%s(%s)" % (callback_param_name, data)

    response = HttpResponse(data, mimetype="application/json; charset=%s" % settings.DEFAULT_CHARSET)
    # XXX need to fix this for raw queries
    if db and table:
        response['Content-Range'] = 'items %s-%s/%s' % (bottom, top, table.total_rows)
    # The following are for IE especially
    response['Pragma'] = "no-cache"
    response['Cache-Control'] = "must-revalidate"
    response['If-Modified-Since'] = str(datetime.datetime.now())

    return response

@staff_member_required
def table(request, db, table):
    # Listing table contents
    if request.method == 'GET':
        return fetch(request, db=db, table=table)
    # Adding a new row
    elif request.method == 'POST':
        return add_row(request, db=db, table=table)
    # Changing fields on tables
    elif request.method == 'PUT':
        return modify_table(request, db=db, table=table)
    else:
        raise HttpResponseNotAllowed(['GET', 'POST', 'PUT'])

@staff_member_required
def row(request, db, table, row):
    debug(repr(request))

    if request.method == 'GET':
        # XXX: Will this happen?
        raise RuntimeError
    elif request.method == 'PUT':
        return update_row(request, db=db, table=table, row=row)
    elif request.method == 'DELETE':
        return delete_row(request, db=db, table=table, row=row)
    else:
        raise HttpResponseNotAllowed(['GET', 'PUT', 'DELETE'])

@staff_member_required
def update_row(request, db, table, row):
    assert False, repr(request)

@staff_member_required
def add_row(request, db, table):
    pass

@staff_member_required
def modify_table(request, db, table):
    pass

@staff_member_required
def fetch_table(request, db, table):
    items = re.match('items=(\d+)-(\d+)', request.META.get('HTTP_RANGE', ''))
    if items:
        bottom = int(items.group(1))
        top = int(items.group(2))
    else:
        #return HttpResponseBadRequest()
        bottom = 1
        top = 100

    table = dbx.Table(db=db, table=table)
    data = table.fetch_rows(bottom, top)
    #data = {'identifier': table.pk, 'items': items}
    #ret = __prepare_json_ret(request, items)
    data = json_encode(data)
    response = HttpResponse(data, mimetype="application/json; charset=%s" % settings.DEFAULT_CHARSET)
    response['Content-Range'] = 'items %s-%s/%s' % (bottom, top, table.total_rows)
    # The following are for IE especially
    response['Pragma'] = "no-cache"
    response['Cache-Control'] = "must-revalidate"
    response['If-Modified-Since'] = str(datetime.datetime.now())

    return response

@staff_member_required
def render_csv(request, db, table):
    table = dbx.Table(db=db, table=table)
    #data = conn.select(table, limit=100)
    data = table.fetch_rows(bottom=1, top=100)

    response = HttpResponse(mimetype='text/csv')
    writer = csv.writer(response)
    writer.writerow([unicode(col['name']).encode("utf-8") for col in table.columns])

    for row in data:
        writer.writerow([unicode(col).encode("utf-8") for col in row])

    return response

@staff_member_required
def index(request):
    user = request.user
    field_types = []
    for name, field in django.db.models.fields.__dict__.iteritems():
        if not (issubclass(type(field), type) and \
           issubclass(field, django.db.models.fields.Field)):
            continue
        name = re.sub('([a-z])([A-Z])', r'\1 \2', re.sub('Field$', '', name))
        if name and field:
            # XXX: This should use a connection object to get the right db type
            field_types.append((name, field(primary_key=True).db_type()))

    context = { 'conn': dbx.Conn(), 'field_types': field_types }
    return render_to_response("sqladmin/index.html", context, context_instance=RequestContext(request))
