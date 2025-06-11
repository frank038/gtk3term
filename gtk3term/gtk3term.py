#!/usr/bin/env python3

# V. 0.8

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Vte, GLib, Pango, Gio, Gdk, GObject
import os,sys,shutil,signal,subprocess,time
import json
from threading import Thread, Event

curr_path = os.getcwd()
my_home = os.getenv("HOME")
if my_home == None or my_home == "":
    _tmp_path = curr_path.split("/")
    my_home = os.path.join(_tmp_path[1],_tmp_path[2])

WINW = 1000
WINH = 600
MAXIMIZED = "False"
GEOMETRY_CHANGED = False

##
# font name - font size - background colour - foreground colour - open new terminal in the same anchestor terminal path
default_config = {"font-name": "", "font-size": 10, "background": "#000000000000", "foreground": "#ffffffffffff", "same-dir": 1}
config_path = os.path.join(curr_path,"settings")
config_file = os.path.join(config_path,"settings.json")
_settings = None
CONFIG_CHANGED = False
if (os.path.exists(config_path) and os.access(config_path, os.W_OK)):
    try:
        _ff = open(config_file,"r")
        _settings = json.load(_ff)
        _ff.close()
    except:
        _settings = default_config

if not _settings:
    _settings = default_config

FONT_NAME = _settings["font-name"]
FONT_SIZE = _settings["font-size"]
FOREGROUND_COLOR = _settings["foreground"]
BACKGROUND_COLOR = _settings["background"]
SAME_DIR = _settings["same-dir"]

# window size and state
try:
    _f = open(os.path.join(curr_path,"settings","cfgsize.txt"), "r")
    _tmp = _f.read()
    _f.close()
    WINW, WINH, MAXIMIZED = _tmp.strip("\n").split(";")
    WINW = int(WINW)
    WINH = int(WINH)
except:
    WINW = 1000
    WINH = 600

_command = None
_directory = None
class TheWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Terminal")
        self.set_default_size(WINW, WINH)
        self.set_icon_from_file(os.path.join(curr_path,"icons","terminal.png"))
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.main_box)
        
        self.connect("configure-event", self.window_resize)
        self.connect("destroy", self.on_destroy)
        self.connect('delete_event', self.close_window)
        
        self._config_changed = 0
        self.closed_by_user = False
        
        self.main_tab = Gtk.Notebook()
        self.main_tab.set_scrollable(True)
        self.main_tab.connect("page-reordered", self.on_page_reordered)
        self.main_tab.connect("switch-page", self.on_page_switched)
        # self.main_tab.connect("page-removed", self.on_page_removed)
        self.main_box.add(self.main_tab)
        
        # list of new terminal: [terminal, task] - ready function
        self.list_terminal = []
        
        self._event = Event()
        self._signal = SignalObject()
        self._signal.connect("notify::propList", self.athreadslot)
        
        a = Gdk.RGBA(0.0,0.0,0.0) # also background
        b = Gdk.RGBA(1.0,0.41,0.4)
        c = Gdk.RGBA(0.275,0.75,0.0) # prompt
        d = Gdk.RGBA(0.67,0.65,0.0)
        e = Gdk.RGBA(0.44,0.61,1.0) # path and folders
        f = Gdk.RGBA(0.85,0.41,0.96) # images videos
        g = Gdk.RGBA(0.0,0.72,0.75)
        h = Gdk.RGBA(0.74,0.74,0.74) # also foreground
        
        a2 = Gdk.RGBA(0.47,0.47,0.47) # backup files
        b2 = Gdk.RGBA(1.0,0.70,0.56)
        c2 = Gdk.RGBA(0.0,0.93,0.48) #
        d2 = Gdk.RGBA(0.71,0.85,0.0)
        e2 = Gdk.RGBA(0.75,0.75,1.0) # path and folders?
        f2 = Gdk.RGBA(1.0,0.65,0.875)
        g2 = Gdk.RGBA(0.235,0.86,1.0)
        h2 = Gdk.RGBA(1.0,1.0,1.0) # also foreground
        
        self._palette = [a,b,c,d,e,f,g,h,a2,b2,c2,d2,e2,f2,g2,h2]
        
        if not (os.path.exists(my_home) and os.access(my_home, os.R_OK)):
            self._message_dialog_yes("Home directory not accessible.")
        else:
            # self.first_tab()
            if _directory:
                if (os.path.exists(my_home) and os.access(my_home, os.R_OK)):
                    self.on_add_tab(_directory, None)
                else:
                    self.on_add_tab("", None)
            else:
                self.on_add_tab("", None)
            self.main_tab.set_current_page(1)
    
    def save_config(self, font_name, font_size,fcolor,bcolor,same_dir):
        global FONT_NAME
        global FONT_SIZE
        global FOREGROUND_COLOR
        global BACKGROUND_COLOR
        global SAME_DIR
        global _settings
        if font_name != FONT_NAME or font_size != FONT_SIZE or fcolor != FOREGROUND_COLOR \
                or bcolor != BACKGROUND_COLOR or same_dir != SAME_DIR:
            try:
                _settings["font-name"] = font_name
                _settings["font-size"] = int(font_size)
                _settings["foreground"] = fcolor
                _settings["background"] = bcolor
                _settings["same-dir"] = same_dir
                #
                _ff = open(config_file,"w")
                json.dump(_settings, _ff, indent = 4)
                _ff.close()
                #
                FONT_NAME = font_name
                FONT_SIZE = int(font_size)
                FOREGROUND_COLOR = fcolor
                BACKGROUND_COLOR = bcolor
                SAME_DIR = same_dir
            except Exception as E:
                self.dialog_y_response(str(E), self)
        
    def on_close_destroy_window(self):
        num_tabs = self.main_tab.get_n_pages()
        if num_tabs > 0:
            for i in range(num_tabs):
                _page = self.main_tab.get_nth_page(i)
                _ch = self.main_tab.get_tab_label(_page).get_children()
                for el in _ch:
                    if isinstance(el,Gtk.Button):
                        el.do_activate(el)
                        break
        
    def close_window(self, w, e):
        self.on_close_destroy_window()
        return True
        
    def on_destroy(self, widget):
        # self._event.set()
        # num_tabs = self.main_tab.get_n_pages()
        # for i in range(num_tabs):
            # _page = self.main_tab.get_nth_page(i)
            # self.main_tab.remove_page(0)
        #
        self.on_close_destroy_window()
        #
        if GEOMETRY_CHANGED:
            try:
                _f = open(os.path.join(curr_path,"settings","cfgsize.txt"), "w")
                _f.write("{};{};{}".format(WINW,WINH,MAXIMIZED))
                _f.close()
            except Exception as E:
                self.dialog_y_response(str(E), self)
        Gtk.main_quit()
    
    def window_resize(self, widget, event):
        global WINW
        global WINH
        global MAXIMIZED
        global GEOMETRY_CHANGED
        _window = self.get_window()
        if bool(_window.get_state() & Gdk.WindowState.MAXIMIZED):
            if MAXIMIZED == "False":
                MAXIMIZED = "True"
                GEOMETRY_CHANGED = True
        elif not bool(_window.get_state() & Gdk.WindowState.MAXIMIZED) or not \
                        (WINW == event.width or WINH == event.height):
            if MAXIMIZED == "True":
                MAXIMIZED = "False"
                GEOMETRY_CHANGED = True
            else:
                WINW = event.width
                WINH = event.height
                GEOMETRY_CHANGED = True
    
    def on_page_reordered(self, _notebook, _page, _num):
        terminal = _page._term
        terminal.grab_focus()
    
    def on_page_switched(self, _notebook, _page, _n_page):
        # set the window title
        if hasattr(_page, "_term"):
            terminal = _page._term
            _name = terminal.get_termprop_string("xterm.title")
            if _name:
                self.set_title(_name[0] or "")
            #
            terminal.grab_focus()
    
    def find_page_from_terminal(self, terminal):
        t_page = None
        num_tabs = self.main_tab.get_n_pages()
        for i in range(num_tabs):
            _page = self.main_tab.get_nth_page(i)
            if _page._term == terminal:
                t_page = _page
                break
        return t_page
    
    def on_termprop_changed(self, terminal, _prop):
        _name = terminal.get_termprop_string(_prop)
        if _name:
            _page = self.find_page_from_terminal(terminal)
            if _page:
                _box_ch = self.main_tab.get_tab_label(_page).get_children() # _page.get_children()[0]
                if _box_ch:
                    _label = _box_ch[0]
                    _label.set_text(_name[0])
                    _label.set_tooltip_text(_name[0])
                    # window title
                    _curr_page = self.main_tab.get_nth_page(self.main_tab.get_current_page())
                    if _curr_page == _page:
                        self.set_title(_name[0])
    
    def on_font_changed(self, terminal, _type):
        global FONT_SIZE
        global CONFIG_CHANGED
        if FONT_SIZE and FONT_SIZE > 4:
            _font_desc = terminal.get_font()
            FONT_SIZE += _type
            _font_desc.set_size((FONT_SIZE)*Pango.SCALE)
            terminal.set_font(_font_desc)
            CONFIG_CHANGED = True
        
    def on_child_exited(self, terminal, _status):
        if self.closed_by_user:
            self.closed_by_user = False
            return
        num_tabs = self.main_tab.get_n_pages()
        if num_tabs == 1:
            # quit the programma
            self.hide()
            tab_page = self.main_tab.get_nth_page(0)
            page_num = self.main_tab.page_num(tab_page)
            self.main_tab.remove_page(page_num)
            Gtk.main_quit()
            return
        for i in range(num_tabs):
            _page = self.main_tab.get_nth_page(i)
            if _page._term == terminal:
                self.main_tab.remove_page(i)
                break
        #
        curr_page = self.main_tab.get_nth_page(self.main_tab.get_current_page())
        if curr_page:
            terminal = curr_page._term
            terminal.grab_focus()
            
    def on_new_tab(self):
        if SAME_DIR:
            curr_page = self.main_tab.get_nth_page(self.main_tab.get_current_page())
            terminal = curr_page._term
            _name = terminal.get_termprop_string("xterm.title")
            if _name[0]:
                _path_tmp = _name[0].split(":")[1].lstrip(" ")
                _path = os.path.expanduser(_path_tmp)
                if os.path.exists(_path) and os.access(_path, os.R_OK):
                    self.on_add_tab(_path, self.main_tab.get_current_page()+1)
                    return
                else:
                    self._message_dialog_yes("Directory not accessible:\n{}".format(_path))
            else:
                self.on_add_tab(my_home, None)
        else:
            self.on_add_tab(my_home, None)
        
    def on_add_tab(self, _path=None, _pos=None):
        terminal = Vte.Terminal()
        if FONT_SIZE and FONT_SIZE > 4:
            _font_desc = terminal.get_font()
            _font_desc.set_size(FONT_SIZE*Pango.SCALE)
            if FONT_NAME:
                _font_desc.set_family("{}, monospace".format(FONT_NAME))
            terminal.set_font(_font_desc)
        #
        _color_fore = Gdk.RGBA()
        _color_fore.parse(FOREGROUND_COLOR)
        _color_back = Gdk.RGBA()
        _color_back.parse(BACKGROUND_COLOR)
        terminal.set_colors(_color_fore, _color_back, self._palette)
        #
        terminal.set_enable_bidi(True)
        terminal.set_enable_shaping(True)
        #
        terminal.connect("termprop-changed", self.on_termprop_changed)
        terminal.connect("decrease-font-size", self.on_font_changed, -1)
        terminal.connect("increase-font-size", self.on_font_changed, 1)
        terminal.connect("child-exited", self.on_child_exited)
        # the page
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroller = Gtk.ScrolledWindow()
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.add(terminal)
        box.pack_start(scroller, False, True, 2)
        #
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        _label = _path
        tab_label = Gtk.Label(label=_label)
        tab_label.set_tooltip_text(_label)
        tab_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        tab_label.set_hexpand(True)
        tab_box.pack_start(tab_label,False,False,0)
        tab_btn = Gtk.Button()
        tab_btn.set_relief(Gtk.ReliefStyle.NONE)
        _img = Gtk.Image.new_from_icon_name(Gtk.STOCK_CLOSE, 22)
        tab_btn.set_image(_img)
        tab_btn.connect("clicked", self.on_tab_btn)
        tab_box.pack_start(tab_btn,False,False,0)
        # child - tab_label or widget - position
        if _pos == None:
            self.main_tab.insert_page(box,tab_box, self.main_tab.get_n_pages())
        else:
            self.main_tab.insert_page(box,tab_box, _pos)
        box._term = terminal
        tab_btn._page = box
        self.main_tab.set_tab_reorderable(box, True)
        tab_label.show()
        tab_btn.show()
        self.main_tab.show_all()
        if _pos == None:
            self.main_tab.set_current_page(self.main_tab.get_n_pages()-1)
        else:
            self.main_tab.set_current_page(_pos)
        #### contextual menu
        menu = Gtk.Menu()
        terminal.set_context_menu(menu)
        ## actions
        #
        _act_new_tab = Gtk.MenuItem.new_with_label("New tab")
        _act_new_tab.connect("activate", self.on_action_selected, "new", terminal)
        menu.append(_act_new_tab)
        _act_new_tab.show()
        #
        _act_sep = Gtk.SeparatorMenuItem()
        menu.append(_act_sep)
        _act_sep.show()
        #
        _act_copy = Gtk.MenuItem.new_with_label("Copy")
        _act_copy.connect("activate", self.on_action_selected, "copy", terminal)
        menu.append(_act_copy)
        _act_copy.show()
        #
        _act_paste = Gtk.MenuItem.new_with_label("Paste")
        _act_paste.connect("activate", self.on_action_selected, "paste", terminal)
        menu.append(_act_paste)
        _act_paste.show()
        #
        _act_sep = Gtk.SeparatorMenuItem()
        menu.append(_act_sep)
        _act_sep.show()
        #
        _act_settings = Gtk.MenuItem.new_with_label("Settings")
        _act_settings.connect("activate", self.on_action_selected, "settings")
        menu.append(_act_settings)
        _act_settings.show()
        #
        if _command and shutil.which(_command):
             _cmd = ["/usr/bin/bash", "-c", _command]
             self.set_title(_command)
        else:
            _cmd = ["/usr/bin/bash"]
        try:
            terminal.spawn_async(
                Vte.PtyFlags.DEFAULT,
                _path,
                _cmd,
                None,
                GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                None,
                None,
                -1,
                None,
                self.ready,
                [box]
                )
        except:
            _cmd = ["/usr/bin/bash"]
            terminal.spawn_async(
                Vte.PtyFlags.DEFAULT,
                _path,
                _cmd,
                None,
                GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                None,
                None,
                -1,
                None,
                self.ready,
                [self.main_tab.get_n_pages(), tab_btn]
                )
        # grab the focus
        terminal.grab_focus()
    
    def ready(self, pty, task, _pid, args):
        # <Vte.Terminal object at 0x7f6e83e6f8c0 (VteTerminal at 0x2a5ba090)>
        # 15027
        # None 
        # [<Gtk.Box object at 0x7f8918460240 (GtkBox at 0x27ac6150)>]
        self.list_terminal.append([pty,task])
        return
    
    def on_action_selected(self, _act, _type = None, terminal = None):
        if _type == "new":
            self.on_new_tab()
        elif _type == "copy":
            terminal.copy_clipboard_format(Vte.Format.TEXT) # .TEXT or .HTML
        elif _type == "paste":
            terminal.paste_clipboard()
        elif _type == "settings":
            configWin(self)
    
    # tab close button
    def on_tab_btn(self, btn):
        self.closed_by_user = True
        ret = None
        if self.main_tab.get_n_pages() == 1:
            # quit the program
            tab_page = btn._page
            ret = self.terminate_process(tab_page._term)
            # check the process
            if ret != None:
                self.athread = pidThread(ret[1], self._signal, 1, self._event, self)
                self.athread.daemon = True
                self.athread.start()
            # # moved to athreadslot
            # self.hide()
            # page_num = self.main_tab.page_num(tab_page)
            # self.main_tab.remove_page(page_num)
            # self.on_destroy(self)
            return
        #
        tab_page = btn._page
        ret = self.terminate_process(tab_page._term)
        #
        page_num = self.main_tab.page_num(tab_page)
        self.main_tab.remove_page(page_num)
        #
        curr_page = self.main_tab.get_nth_page(self.main_tab.get_current_page())
        terminal = curr_page._term
        terminal.grab_focus()
        # check the process
        if ret != None:
            self.athread = pidThread(ret[1], self._signal, 2, self._event, self)
            self.athread.daemon = True
            self.athread.start()
    
    # def on_page_removed(self, notebook, child, page_num):
        # pass
        
    
    # terminate the working process before exiting
    def terminate_process(self, _terminal):
        _pid = None
        for t in self.list_terminal[:]:
            if t[0] == _terminal:
                _pid = t[1]
                try:
                    # ret=os.kill(t[1], signal.SIGTERM)
                    os.kill(t[1], signal.SIGKILL)
                except Exception as E:
                    return [str(E),t[1]]
                    # try:
                        # os.kill(t[1], signal.SIGKILL)
                    # except Exception as E:
                        # return t[1]
                self.list_terminal.remove(t)
                break
        return [0, _pid]
    
    def athreadslot(self,_signal,_param):
        _list = _signal.propList[0]
        # _list = ["pid-thread-error" or "pid-thread-success", process_pid, num_of_tabs: 1 only one tab - 2 more than 1 tab]
        _num_of_tabs = _list[2]
        #
        if _list[0] == "pid-thread-error":
            self._message_dialog_yes("Is the process {} terminated?".format(_list[1]))
            # if _num_of_tabs == 1:
                # return
            # elif _num_of_tabs == 2:
                # return
        elif _list[0] == "pid-thread-success":
            # only one tab opened
            if _num_of_tabs == 1:
                self._event.set()
                self.hide()
                self.main_tab.remove_page(0)
                self.on_destroy(self)
    
    def _message_dialog_yesno(self, _msg):
        messagedialog = Gtk.MessageDialog(parent=self,
                                          modal=True,
                                          message_type=Gtk.MessageType.INFO,
                                          buttons=Gtk.ButtonsType.OK_CANCEL,
                                          text=_msg)
        messagedialog.connect("response", self.dialog_yn_response)
        messagedialog.show()
    
    def dialog_yn_response(self, messagedialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            messagedialog.destroy()
        elif response_id == Gtk.ResponseType.CANCEL:
            messagedialog.destroy()
        elif response_id == Gtk.ResponseType.DELETE_EVENT:
            messagedialog.destroy()
    
    def _message_dialog_yes(self, _msg):
        messagedialog = Gtk.MessageDialog(parent=self,
                                          modal=True,
                                          message_type=Gtk.MessageType.INFO,
                                          buttons=Gtk.ButtonsType.OK,
                                          text=_msg)
        messagedialog.connect("response", self.dialog_y_response)
        messagedialog.show()
    
    def dialog_y_response(self, messagedialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            messagedialog.destroy()
        elif response_id == Gtk.ResponseType.DELETE_EVENT:
            messagedialog.destroy()


class pidThread(Thread):
    def __init__(self, _pid, _signal, _n, _event, _parent):
        super(pidThread, self).__init__()
        self._pid = _pid
        self._signal = _signal
        self._n = _n
        self._event = _event
        self._parent = _parent
        
    def run(self):
        if self._event.is_set():
            return
        # check the process
        list_pid = None
        try:
            i = 0
            while i < 6:
                list_pid = subprocess.check_output("pstree -p {}".format(self._pid), shell=True, universal_newlines=True).split("\n")
                list_pid.remove('')
                if list_pid == []:
                    self._signal.propList = ["pid-thread-success", self._pid, self._n]
                    return
                time.sleep(2)
                i += 1
        except Exception as E:
            pass
        #
        if list_pid != None:
            self._signal.propList = ["pid-thread-error", self._pid, self._n]
        return
        #########

class SignalObject(GObject.Object):
    
    def __init__(self):
        GObject.Object.__init__(self)
        self._name = ""
        self.value = -99
        self._list = []
    
    @GObject.Property(type=str)
    def propName(self):
        'Read-write integer property.'
        return self._name

    @propName.setter
    def propName(self, name):
        self._name = name
    
    @GObject.Property(type=int)
    def propInt(self):
        'Read-write integer property.'
        return self.value

    @propInt.setter
    def propInt(self, value):
        self.value = value
    
    @GObject.Property(type=object)
    def propList(self):
        'Read-write integer property.'
        return self._list

    @propList.setter
    def propList(self, data):
        self._list = [data]


class configWin(Gtk.Window):
    def __init__(self, _parent):
        super().__init__()
        self.parent = _parent
        self.main_box = Gtk.Box.new(1,0)
        self.add(self.main_box)
        #
        ### settings FONT_NAME FONT_SIZE FOREGROUND_COLOR BACKGROUND_COLOR SAME_DIR
        ## font name
        font_name_box = Gtk.Box.new(0,0)
        self.main_box.pack_start(font_name_box,0,0,0)
        font_name_lbl = Gtk.Label(label="Font name")
        font_name_box.pack_start(font_name_lbl,1,1,0)
        font_name_lbl.props.halign = 1
        #
        self.font_name_family = ""
        self.font_name_btn = Gtk.Button(label="Choose a font")
        if FONT_NAME:
            self.font_name_btn.set_label(FONT_NAME)
        self.font_name_btn.connect("clicked", self.on_font_name)
        font_name_box.pack_start(self.font_name_btn,0,0,0)
        #
        self.font_name_clear = Gtk.Button(label="Reset")
        self.font_name_clear.connect("clicked", self.on_font_reset)
        self.main_box.pack_start(self.font_name_clear,0,0,0)
        ## font size
        font_size_box = Gtk.Box.new(0,0)
        self.main_box.pack_start(font_size_box,0,0,0)
        font_size_lbl = Gtk.Label(label="Font size")
        font_size_box.pack_start(font_size_lbl,1,1,0)
        font_size_lbl.props.halign = 1
        # 
        self.font_size_sb = Gtk.SpinButton()
        self.font_size_sb.set_numeric(True)
        self.font_size_sb.set_increments(1.0,1.0)
        self.font_size_sb.set_range(4.0,96.0)
        self.font_size_sb.set_value(FONT_SIZE)
        font_size_box.pack_start(self.font_size_sb,0,0,0)
        ## text colour
        box_foreground = Gtk.Box.new(0,0)
        self.main_box.pack_start(box_foreground,0,0,0)
        #
        foreground_lbl = Gtk.Label("Text color ")
        box_foreground.pack_start(foreground_lbl,1,1,0)
        foreground_lbl.props.halign = 1
        #
        self.fcolor_btn = Gtk.ColorButton()
        _color = Gdk.RGBA()
        _color.parse(FOREGROUND_COLOR)
        self.fcolor_btn.set_rgba(_color)
        box_foreground.pack_start(self.fcolor_btn,0,0,0)
        #
        ## background colour
        box_background = Gtk.Box.new(0,0)
        self.main_box.pack_start(box_background,0,0,0)
        #
        background_lbl = Gtk.Label("Background color ")
        box_background.pack_start(background_lbl,1,1,0)
        background_lbl.props.halign = 1
        #
        self.bcolor_btn = Gtk.ColorButton()
        _color = Gdk.RGBA()
        _color.parse(BACKGROUND_COLOR)
        self.bcolor_btn.set_rgba(_color)
        # self.main_grid.attach(self.color_btn,1,1,0,0)
        box_background.pack_start(self.bcolor_btn,0,0,0)
        #
        ## same directory
        box_same_dir = Gtk.Box.new(0,0)
        self.main_box.pack_start(box_same_dir,0,0,0)
        same_dir_lbl = Gtk.Label(label="Same directory")
        same_dir_lbl.set_tooltip_text("Open the new terminal in the same ancestor directory.")
        box_same_dir.pack_start(same_dir_lbl,1,1,0)
        same_dir_lbl.props.halign = 1
        #
        self.same_dir_cb = Gtk.ComboBoxText()
        self.same_dir_cb.append_text("No")
        self.same_dir_cb.append_text("Yes")
        self.same_dir_cb.set_active(SAME_DIR)
        box_same_dir.pack_start(self.same_dir_cb,0,0,0)
        #
        ### buttons
        btn_box = Gtk.Box.new(0,0)
        self.main_box.pack_start(btn_box,1,0,0)
        #
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", self.on_cancel)
        btn_box.pack_start(cancel_btn,1,1,0)
        cancel_btn.show()
        #
        accept_btn = Gtk.Button(label="Accept")
        accept_btn.connect("clicked", self.on_accept)
        btn_box.pack_start(accept_btn,1,1,0)
        #
        self.show_all()
    
    def on_font_reset(self, btn):
        self.font_name_btn.set_label("Choose a font")
        self.font_name_family = ""
    
    def on_font_name(self, btn):
        _f = Gtk.FontChooserDialog()#.new(None,self)
        _font_dsc = _f.get_font_desc()
        _font_dsc.set_size(FONT_SIZE * Pango.SCALE)
        if FONT_NAME:
            _font_dsc.set_family(FONT_NAME)
        _f.set_font_desc(_font_dsc)
        response = _f.run()
        if response == Gtk.ResponseType.OK:
            self.font_name_btn.set_label(_f.get_font_face().get_family().get_name())
            self.font_name_family = _f.get_font_face().get_family().get_name()
            _font_size = int(_f.get_font_size()/1024)
            self.font_size_sb.set_value(_font_size)
            _f.destroy()
        elif response == Gtk.ResponseType.CANCEL:
            _f.destroy()

        
    def on_accept(self, btn):
        self.parent.save_config(self.font_name_family, self.font_size_sb.get_value(),self.fcolor_btn.get_rgba().to_color().to_string(),self.bcolor_btn.get_rgba().to_color().to_string(),self.same_dir_cb.get_active())
        self.close()
        
    def on_cancel(self, btn):
        self.close()

if __name__ == '__main__':
    _argv = sys.argv
    if "-e" in _argv:
        _command = _argv[_argv.index("-e")+1]
    if "-d" in _argv:
        _directory = _argv[_argv.index("-d")+1]
    #
    win=TheWindow()
    win.show_all()
    if MAXIMIZED == "True":
        _window = win.get_window()
        _window.maximize()
    Gtk.main()
