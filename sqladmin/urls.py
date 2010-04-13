from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^databases\.json$', 'imp5.sqladmin.views.database_tree'),
    (r'^tables\/?$', 'imp5.sqladmin.views.tables'),
    (r'^fetch\/?$', 'imp5.sqladmin.views.fetch'),
#    (r'^_meta\/(?P<id>[^\/]+)\/?$', 'imp5.sqladmin.views.table_metadata'),
#    (r'^_meta\/?$', 'imp5.sqladmin.views.table_metadata'),
#    (r'^(?P<db>[^\/]+)__(?P<table>[^\/]+)\.csv$', 'imp5.sqladmin.views.render_csv'),
    (r'^(?P<db>[^\/]+)/(?P<table>[^\/]+)\/?$', 'imp5.sqladmin.views.table'),
    (r'^(?P<db>[^\/]+)/(?P<table>[^\/]+)/(?P<row>[^\/]+)\/?$', 'imp5.sqladmin.views.row'),
#    (r'^(?P<db>[^\/]+)/(?P<table>[^\/]+)\/?$', 'imp5.sqladmin.views.table'),
#    (r'^(?P<db>[^\/]+)\/?$', 'imp5.sqladmin.views.db'),
    (r'^$', 'imp5.sqladmin.views.index')
)