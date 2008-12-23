# Notes
# 
# gnxs won't work, because they belong to tnodes, not vnodes
# 
# backling will store all its stuff in v.unknownAttributes['_bklnk']
# 
# the vnode's id will be v.unknownAttributes['_bklnk']['id']
# 
# unless Edward decides otherwise, backlink will use 
# leo.core.leoNodes.nodeIndices.getNewIndex() to make these ids
# 
# when nodes are copied and pasted unknownAttributes are duplicated
# 
# during load, backlink will create a dict. of vnode ids.  Duplicates
# will be split, so that a node linking to a node which is copied and
# pasted will link to both nodes after the paste, *after* a save and
# load cycle.  Before a save and load cycle it will link to whichever
# vnode originally held the id

'''Backlink - allow arbitrary links between nodes
'''

__version__ = '0.1'
# 
# Put notes about each version here.

import leo.core.leoGlobals as g
import leo.core.leoPlugins as leoPlugins

# can this happen?
# if g.app.gui is None:
#     g.app.createTkGui(__file__)

Tk = None
Qt = None
if g.app.gui.guiName() == "tkinter":
    Tk  = g.importExtension('Tkinter',pluginName=__name__,verbose=True,required=True)
elif g.app.gui.guiName() == "qt":
    from PyQt4 import QtCore, QtGui, uic
    Qt = QtCore.Qt

def init ():

    leoPlugins.registerHandler('after-create-leo-frame',onCreate)
    # can't use before-create-leo-frame because Qt dock's not ready
    g.plugin_signon(__name__)
        
    return True
def onCreate (tag, keys):
    
    c = keys.get('c')
    if not c: return
    
    thePluginController = backlinkController(c)
class backlinkController:
    
    def __init__ (self,c):

        self.c = c
        self.initIvars()
        leoPlugins.registerHandler('open2', self.loadLinks)
        # already missed initial 'open2' because of after-create-leo-frame
        self.loadLinksInt()

        if Tk:
            #leoPlugins.registerHandler('iconrclick2', self.showMenu)
            #leoPlugins.registerHandler('select3', self.showLinksLog)
            leoPlugins.registerHandler('select3', self.updateTkTab)
            self.makeTkTab()
        if Qt:
            # for now, remove when Qt UI works
            leoPlugins.registerHandler('select3', self.showLinksLog)
    
            uiPath = g.os_path_join(g.app.leoDir, 'plugins', 'Backlink.ui')
            form_class, base_class = uic.loadUiType(uiPath)

            # define UI class now form_class exists
            class BacklinkTab(QtGui.QWidget, form_class):

                """Class to wrap QDesigner ui object and provide glue code to make it work."""

                def __init__(self, *args):
                    QtGui.QWidget.__init__(self, *args)
                    self.setupUi(self)

                    self.connect(self.markSource, QtCore.SIGNAL("clicked()"), self, QtCore.SLOT('markSource(self)'))

                def markSource(self):
                    print 'markSource'
                    pass
                def markDest(self):
                    print 'markDest'
                    pass
                def linkSource(self):
                    print 'linkSource'
                    pass
                def linkDest(self):
                    print 'linkDest'
                    pass
                def undirected(self):
                    print 'undirected'
                    pass
                def rescanX(self):
                    print 'rescan'
                    pass

            top = c.frame.top

            self.form = BacklinkTab()

            dock = QtGui.QDockWidget("Links", top)
            dock.setAllowedAreas(Qt.AllDockWidgetAreas)
            dock.setWidget(self.form)
            top.addDockWidget(Qt.TopDockWidgetArea, dock)
            dock.setFloating(True) 

    def initIvars(self):
        self.linkDestination = None
        self.linkSource = None
        self.vnode = {}
        self.positions = {}
    def makeTkTab(self):
    
        c = self.c
        c.frame.log.createTab('Links', createText=False)
        w = c.frame.log.frameDict['Links']

        self.listbox = Tk.Listbox(w)
        self.listbox.pack(side=Tk.TOP, fill=Tk.BOTH, expand=True)
        self.listbox.bind("<ButtonRelease-1>", self.tkListClicked)

        commands = [
            ('Mark source', self.markSrc),
            ('Mark  dest.', self.markDst),
            ('Link source', self.linkSrc),
            ('Link dest.', self.linkDst),
            ('Undirected link', self.linkUnd),
            ('Rescan links', self.loadLinksInt),
        ]

        comms = iter(commands)
        for i in range(3):
            f = Tk.Frame(w)
            for j in range(2):
                txt, com = comms.next()
                b = Tk.Button(f, text=txt, width=10, command=com)
                b.pack(side=Tk.LEFT, fill=Tk.BOTH)
            f.pack(side=Tk.TOP, fill=Tk.BOTH)
    def updateTkTab(self,tag,k):

        if k['c'] != self.c: return  # not our problem

        self.updateTkTabInt()
    def updateTkTabInt(self):

        c = self.c
        p = c.currentPosition()
        v = p.v

        self.listbox.delete(0,Tk.END)

        if hasattr(v, 'unknownAttributes') and '_bklnk' in v.unknownAttributes:
            i = 0
            links = v.unknownAttributes['_bklnk']['links']
            dests = []
            while i < len(links):
                linkType, other = links[i]
                otherV = self.vnode[other]
                otherP = self.vnodePosition(otherV)
                if not otherP:
                    g.es('Deleting lost link')
                    del links[i]
                else:
                    i += 1
                    dests.append((linkType, otherP))
            if dests:
                for i in dests:
                    def goThere(where = i[1]): c.selectPosition(where)
                    txt = {'S':'->','D':'<-','U':'--'}[i[0]] + ' ' + i[1].headString()
                    self.listbox.insert(Tk.END, txt)
                    def delLink(on=v,
                        to=i[1].v.unknownAttributes['_bklnk']['id'],
                        type_=i[0]): self.deleteLink(on,to,type_)
                self.dests = dests
    def tkListClicked(self, event):
    
        selected = self.listbox.curselection()
        if not selected:
            return  # click on empty list of unlinked node
        selected = int(selected[0])  # not some fancy smancy Tk value
        self.c.selectPosition(self.dests[selected][1])
    def initBacklink(self, v):

        if not hasattr(v, 'unknownAttributes'):
            v.unknownAttributes = {}

        if '_bklnk' not in v.unknownAttributes:
            vid = g.app.nodeIndices.toString(g.app.nodeIndices.getNewIndex())
            v.unknownAttributes['_bklnk'] = {'id':vid, 'links':[]}

        self.vnode[v.unknownAttributes['_bklnk']['id']] = v
    def loadLinks(self, tag, keywords):

        if self.c != keywords['c']:
            return  # not our problem

        self.loadLinksInt()
    def loadLinksInt(self):

        c = self.c  # checked in loadLinks()

        self.initIvars()

        ids = {}
        idsSeen = set()

        # /here id should be a dict of lists of "aliases"

        for p in c.allNodes_iter():
            self.positions[p.v] = p
            v = p.v
            if hasattr(v, 'unknownAttributes') and '_bklnk' in v.unknownAttributes:
                vid = v.unknownAttributes['_bklnk']['id']
                if vid in ids:
                    ids[vid].append(v)
                else:
                    ids[vid] = [v]
                idsSeen.add(vid)

        rvid = {}
        for i in ids:
            rvid[i] = [ids[i][0]]
            self.vnode[i] = ids[i][0]
            for x in ids[i][1:]:
                idx = 1
                def nvid(): return vid+'.'+str(idx)
                while nvid() in idsSeen and idx <= 100:
                    idx += 1
                if nvid() in idsSeen:
                    g.es('backlink: Massive duplication of vnode ids', color='red')
                idsSeen.add(nvid())
                rvid[i].append(x)
                x.unknownAttributes['_bklnk']['id'] = nvid()
                self.vnode[nvid()] = x
    
        for vnode in self.vnode:  # just the vnodes with link info.
            links = self.vnode[vnode].unknownAttributes['_bklnk']['links']
            nl = []
            for link in links:
                if link[1] not in rvid:
                    lt = ('to', 'from')
                    if link[0] == 'S':
                        lt = ('from', 'to')
                    g.es('backlink: link %s %s %s ??? lost' % (
                        lt[0], self.vnode[vnode].headString(), lt[1]), color='red')
                    continue
                for x in rvid[link[1]]:
                    nl.append((link[0], x.unknownAttributes['_bklnk']['id']))
            self.vnode[vnode].unknownAttributes['_bklnk']['links'] = nl
    
        g.es('backlink: link info. loaded on %d nodes' % len(self.vnode))
    def showMenu(self,tag,k):

        g.app.gui.killPopupMenu()

        if k['c'] != self.c: return  # not our problem

        p = k['p']
        self.c.selectPosition(p)
        v = p.v
    
        c = self.c

        # Create the menu.
        menu = Tk.Menu(None,tearoff=0,takefocus=0)

        commands = [
            (True, 'Mark as link source', self.markSrc),
            (True, 'Mark as link dest.', self.markDst),
            (True, 'Link to source', self.linkSrc),
            (True, 'Link to dest.', self.linkDst),
            (True, 'Undirected link', self.linkUnd),
            (True, 'Rescan links', self.loadLinksInt),
        ]

        if hasattr(v, 'unknownAttributes') and '_bklnk' in v.unknownAttributes:
            i = 0
            links = v.unknownAttributes['_bklnk']['links']
            dests = []
            while i < len(links):
                linkType, other = links[i]
                otherV = self.vnode[other]
                otherP = self.vnodePosition(otherV)
                if not otherP:
                    g.es('Deleting lost link')
                    del links[i]
                else:
                    i += 1
                    dests.append((linkType, otherP))
            if dests:
                smenu = Tk.Menu(menu,tearoff=0,takefocus=1)
                for i in dests:
                    def goThere(where = i[1]): c.selectPosition(where)
                    c.add_command(menu,label={'S':'->','D':'<-','U':'--'}[i[0]]
                        + i[1].headString(),
                        underline=0,command=goThere)
                    def delLink(on=v,
                        to=i[1].v.unknownAttributes['_bklnk']['id'],
                        type_=i[0]): self.deleteLink(on,to,type_)
                    c.add_command(smenu,label={'S':'->','D':'<-','U':'--'}[i[0]]
                        + i[1].headString(),
                        underline=0,command=delLink)
                menu.add_cascade(label='Delete link', menu=smenu,underline=1)
                menu.add_separator()

        for command in commands:
            available, text, com = command
            if not available:
                continue
            c.add_command(menu,label=text,
                underline=0,command=com)
        

        # Show the menu.
        event = k['event']
        g.app.gui.postPopupMenu(self.c, menu, event.x_root,event.y_root)

        return None # 'break' # EKR: Prevent other right clicks.
    def showLinksLog(self,tag,k):

        if k['c'] != self.c: return  # not our problem

        p = k['new_p']
        v = p.v

        if hasattr(v, 'unknownAttributes') and '_bklnk' in v.unknownAttributes:
            i = 0
            links = v.unknownAttributes['_bklnk']['links']
            dests = []
            while i < len(links):
                linkType, other = links[i]
        
                if other not in self.vnode:
                    return
                    # called before load hook?
        
                otherV = self.vnode[other]
                otherP = self.vnodePosition(otherV)
                if not otherP:
                    g.es('Deleting lost link')
                    del links[i]
                else:
                    i += 1
                    dests.append((linkType, otherP))
            if dests:
                g.es("- link info -")
                for i in dests:
                    g.es("%s %s" %({'S':'->','D':'<-','U':'--'}[i[0]],
                        i[1].headString()))
    def deleteLink(self, on, to, type_):

        vid = on.unknownAttributes['_bklnk']['id']
        links = on.unknownAttributes['_bklnk']['links']

        for n,link in enumerate(links):
            if type_ == link[0] and to == link[1]:
                del links[n]
                v = self.vnode[to]
                links = v.unknownAttributes['_bklnk']['links']
                if type_ == 'S':
                    type_ = 'D'
                elif type_ == 'D':
                    type_ = 'S'
                for n,link in enumerate(links):
                    if type_ == link[0] and link[1] == vid:
                        del links[n]
                        break
                else:
                    g.es("backlink: Note: couldn't find other side of link")
                break
        else:
            g.es("backlink: Error: no such link")
    def vnodePosition(self, v):

        if v in self.positions:
            p = self.positions[v]
            if p.v is v and self.c.positionExists(p):
                return p

        for p in self.c.allNodes_iter():
            self.positions[v] = p
            if p.v is v:
                return p

        return None
    def markSrc(self):
        self.linkSource = self.c.currentPosition().copy()
    def markDst(self):
        self.linkDestination = self.c.currentPosition().copy()
    def linkDst(self):

        if not self.linkDestination or not self.c.positionExists(self.linkDestination):
            g.es('Link destination not specified or no longer valid', color='red')
            return

        self.link(self.c.currentPosition(), self.linkDestination)
    def linkSrc(self):

        if not self.linkSource or not self.c.positionExists(self.linkSource):
            g.es('Link source not specified or no longer valid', color='red')
            return

        self.link(self.linkSource, self.c.currentPosition())
    def linkUnd(self):

        source = None
        if self.linkSource and self.c.positionExists(self.linkSource):
            source = self.linkSource
        elif not self.linkDestination or not self.c.positionExists(self.linkDestination):
            g.es('Link source/dest. not specified or no longer valid', color='red')
            return
        else:
            source = self.linkDestination

        self.link(source, self.c.currentPosition(), mode='undirected')
    def link(self, from_, to, mode='directed'):

        v0 = from_.v
        v1 = to.v
        self.initBacklink(v0)
        self.initBacklink(v1)

        linkType = 'U'

        if mode == 'directed':
            linkType = 'S'
        v0.unknownAttributes['_bklnk']['links'].append( (linkType,
            v1.unknownAttributes['_bklnk']['id']) )

        if mode == 'directed':
            linkType = 'D'
        v1.unknownAttributes['_bklnk']['links'].append( (linkType,
            v0.unknownAttributes['_bklnk']['id']) )

        if hasattr(self, 'listbox'):
            self.updateTkTabInt()
