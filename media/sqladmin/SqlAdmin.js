dojo.require("dojo.parser");
dojo.require("dojo.io.script");
dojo.require("dojo.data.ItemFileReadStore");
dojo.require("dojox.data.JsonRestStore");
dojo.require("dojox.data.CsvStore");
dojo.require("dojox.grid.DataGrid");
dojo.require("dijit.layout.TabContainer");
dojo.require("dijit.layout.BorderContainer");
dojo.require("dijit.layout.ContentPane");
dojo.require("dijit.form.ValidationTextBox");
dojo.require("dijit.form.CheckBox");
dojo.require("dijit.Tree");
dojo.require("dijit.tree.TreeStoreModel");
dojo.require("dijit._Widget");
dojo.require("dijit._Container");
dojo.require("dijit.layout._LayoutWidget");
dojo.provide("dijit._Templated");
dojo.require("dijit.Toolbar");
dojo.require("dijit.form.Button");
//dojo.io.script.attach("codemirror", "/media/codemirror/js/codemirror.js");

var textAreaId = 0;

function error(e, x) {
  console.log('*** Error');
  console.log(e);
  console.log(console.trace());
}

function debug(s) { console.log(s); }
function keys(o) { var a = []; for (var k in o) a.push(k); return a; }

dojo.provide('sqladmin.TemplatedWidget');
dojo.declare('sqladmin.TemplatedWidget', [dijit.layout._LayoutWidget, dijit._Templated], {
  widgetsInTemplate: true,
  parseOnLoad: true,
  doLayout: true,
  isContainer: true,
  isLayoutContainer: true,

  startup: function() {
    dojo.forEach(this._startupWidgets, function(w) { if (w.startup) w.startup() });
    this.resize();
  },

  resize: function() {
    dojo.forEach(this._startupWidgets, function(w) { if (w.resize) w.resize() });
  },
});


dojo.provide('sqladmin.SqlAdmin');
dojo.declare('sqladmin.SqlAdmin', sqladmin.TemplatedWidget, {
  maxColWidth: 30,
  dbMetaPath: 'databases.json',
  tablePath: 'tables',
  fetchPath: "https://dev.imp.wiktel.com/sqladmin/fetch", //'fetch',
  templateString: dojo.cache("sqladmin", "SqlAdmin.html"),

  constructor: function() {
    this.dbStore = new dojo.data.ItemFileReadStore({url: this.dbMetaPath});
    this.dbModel = new dijit.tree.TreeStoreModel({store: this.dbStore, query: {id: '*'}})
    this.tableStore = new dojox.data.JsonRestStore({target: this.tablePath, idAttribute:"id"});
    this.tableDataStores = {};
  },

  //buildRendering: function() {},
  //postMixInProperties: function() {},

  postCreate: function() {
    self = this;
    debug('sqladmin.SqlAdminCore.postCreate');
    debug(this.treeNode);
    this.tree = new dijit.Tree({
      model: this.dbModel,
      showRoot: false,
      onClick: function(obj, widget) { self.onTreeClick(self, obj, widget); }, // XXX: hitch
      getIconClass: dojo.hitch(this, this.getIconClass),
    }, dojo.create('div'));
    this.tree.placeAt(this.treeNode, 'only');
    this.loadEditor();
    this.loadDatabase();

    dojo.connect(this.runButton, "onClick", this, this.runQuery);
  },

  editorOptions: {
    height: "450px",
    parserfile: "../contrib/sql/js/parsesql.js",
    stylesheet: "/media/codemirror/contrib/sql/css/sqlcolors.css",
    path: "/media/codemirror/js/",
    textWrapping: true,
    lineNumbers: true,
    saveFunction: function() { sqa.runQuery() },//dojo.hitch(this, this.onQuerySend),
  },

  loadEditor: function() {
    var self = this;
    this.sqlTextArea.id='textArea'+textAreaId++;
    var options = dojo.mixin(this.editorOptions, {});
    this.editor = CodeMirror.fromTextArea(this.sqlTextArea.id, options);
    //this.editor.grabKeys(dojo.hitch(this, this.onEditorKeypress), function(code) {
    /*this.editor.grabKeys(function() { self.runQuery() }, function(code) {
      if (code == 116) return true;
      return false;
    });*/
  },

  onEditorKeypress: function(e) {
    // XXX
    this.editor.saveFunction();
  },

  //onQueryPost: function(self, id, content) {
  runQuery: function() {
    self = this;
    query = self.editor.selection() || self.editor.getCode();
    debug('Sending query: '+query);
    /*var deferred = dojo.xhrQueryPost({
      url: this.fetchPath,
      handleAs: "json",
      postData: "q="+content,
    });*/
    dojo.io.script.get({
      url: self.fetchPath,
      jsonp: "callback",
      content: { q: query },
      load: function(result, request) {
          console.log("Got response to query: "+request.args.content.q);
          console.log(result);
          structure = dojo.map(result.columns, function(field)
            { return {field: field[0], name: field[0], width: Math.min(Number(field[2]),self.maxColWidth)+'em'}});
          self.rawQueryGrid.setStructure(structure);
          debug(structure);
          self.rawQueryStore = new dojo.data.ItemFileReadStore({data: {identifier: 'id', items: result.data}});
          self.rawQueryGrid.setStore(self.rawQueryStore);
      },
      error: error,
    });
  },

  hideTabs: function() {
    self=this;
    dojo.forEach(self.tabs.getChildren(), function(tab) {
      // XXX
      if (tab.title != 'SQL') self.tabs.removeChild(tab);
    });
  },

  showTabs: function() {
    self=this;
    self.hideTabs();
    dojo.forEach(arguments, function(tab) {
      self.tabs.addChild(tab, 1);
    });
    //self.loadEditor();
  },

  getIconClass: function(item, opened){
    //(opened ? "dijitFolderOpened" : "dijitFolderClosed") : "dijitLeaf";
    type = this.dbStore.getValue(item, 'type');
    if (type == 'table') return this.dbStore.getValue(item, 'subtype')+'Icon';
    return type+'Icon';
  },

  onTreeClick: function(self, obj, widget) {
    var type = obj.type[0];
    var id = obj.id[0];
    debug(type);
    debug(id);
    if (type=='table') {
      //dijit.byId('MyTabContainer').removeChild(dijit.byId('MyTab'));
      /*tableView = new sqladmin.TableView(id, this.getTableDataStore);
      dojo.place(tableView, this.tabs, 'only');*/
      this.showTabs(self.dataTab, self.structureTab);
      this.tableStore.fetch({query: {table_id: id}, onError: error,
        onComplete: dojo.hitch(this, this.loadTable)});
        //dojo.hitch(this, function(table) { this.loadTable(table, id)});
    } else if (type=='database') {
      this.loadDatabase(id);
    }
  },

  getColWidth: function(field) {
    if (field.data_type=='float') return '12em';
    else if (field.data_type=='varchar' || field.data_type=='nvarchar') return Math.min(field.data_length, 25)+'em';
    else return '8em';
  },

  getTableDataStore: function(table_id, pk) {
    debug('getTableDataStore('+table_id+','+pk+')');
    return this.tableDataStores[table_id] = this.tableDataStores[table_id] || new dojox.data.JsonRestStore({target:table_id, idAttribute:pk})
  },

  loadDatabase: function() {
      this.showTabs(self.databaseTab);
  },

  loadTable: function(table) {
    debug('loadTable');
    self = this;
    structure = dojo.map(table.columns, function(field) {
        return {field: field.name, name: field.name, width: self.getColWidth(field)}
      });
    this.dataGrid.setStore(this.getTableDataStore(table.table_id, table.pk));
    this.dataGrid.setStructure(structure);

    // DataGrid gives an error if __parent exists
    // I'd prefer to just use columnStore anyway, but that doesn't seem to work
    dojo.map(table.columns, function(field) { delete field.__parent; return field; })
    this.structureGrid.setStore(new dojo.data.ItemFileReadStore({data: {identifier: 'id', items: table.columns}}));
  //}
  //}});
  },
});

dojo.declare('sqladmin.ColumnDefRow', [dijit._Widget, dijit._Templated], {
  constructor: function(col) {
    if (this instanceof sqladmin.ColumnDefRow) {
      this.col = col;
    } else {
      columnDefRow = new sqladmin.ColumnDefRow(col);
      return columnDefRow;
    }
  },

  start: function() {
    //this.fieldType = new dijit.form.Select();
    //this.fieldType.addOption(dojo.map(FIELD_TYPES, function(field) {
      return {value: field[1], label: field[0]};
    //}));
    dojo.forEach(FIELD_TYPES, function(field) {
      this.fieldType.add(new Option(field[0], field[1]));
    });
    dojo.connect(this.fieldType, 'onChange', this, 'onFieldTypeChange');
    dojo.connect(this.deleteRowButton, 'onclick', this, function() { this.destroyRecursive(); });
    //dojo.place(this.fieldType.domNode, this.fieldTypeCell);
  },

  onFieldTypeChange: function(newValue) {
    if (val = newValue.match(/[\d,]+(?=\)$)/)) {
      //this.fieldLength.setAttribute('disabled', true);
      //this.fieldLength.setAttribute('hidden', false);
      this.fieldLength.value = val;
    } else if (vals = newValue.match(/((None)|(,))+(?=\)$)/g)) {
      //this.fieldLength.setAttribute('disabled', false);
      //this.fieldLength.setAttribute('hidden', false);
      this.fieldLength.value = vals[0].replace('None', 0);
    } else {
      //this.fieldLength.setAttribute('disabled', true);
      //this.fieldLength.setAttribute('hidden', true);
      this.fieldLength.value = '';
    }
  },

  templateString: ' \
    <tr> \
      <td><input dojoAttachPoint="name" type="text" /></td> \
      <td dojoAttachPoint="fieldTypeCell"><select name="fieldType" dojoAttachPoint="fieldType" /></td> \
      <td><input dojoAttachPoint="fieldLength" type="text" size="5" dojoType="dijit.form.ValidationTextBox" regExp="[\d,]+" /></td> \
      <td><input dojoAttachPoint="pk" dojoType="dijit.form.CheckBox" /></td> \
      <td dojoAttachPoint="deleteRowButton">Del</td> \
    </tr>',
});

var state = {
    back: function() { },
    forward: function() { }
};
//dojo.back.setInitialState(state); */