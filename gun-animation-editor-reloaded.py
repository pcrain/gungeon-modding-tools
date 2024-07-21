#!/usr/bin/python
#Gungeon JSON visualizer and creator

#  Manually install missing packages with:
#    pip install --user --break-system-packages dearpygui numpy pillow screeninfo

import os, sys, subprocess, shlex, json, array, importlib, re, datetime, shutil
from collections import namedtuple

# Install missing packages as necessary
try:
  import dearpygui.dearpygui as dpg
  import numpy as np
  from PIL import Image
  import screeninfo
except:
  print("missing dearpygui, numpy, and/or pillow")
  sys.exit(2)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.realpath(__file__))

    return os.path.join(base_path, relative_path)

# Core
PROGRAM_NAME      = "gun-animation-editor-reloaded"
PROGRAM_TITLE     = "Gun Animation Editor Reloaded"
PROGRAM_VERSION   = "0.9.1"
PREVIEW_SCALE     = 8 # magnification factor for preview
PIXELS_PER_TILE   = 16.0 # Unity / Gungeon scaling factor for sprites

# Tags
MAIN_WINDOW_TAG            = "mainwindow"
FILE_PICKER_TAG            = "file picker box"
PREVIEW_IMAGE_TAG          = "preview_image"
HAND_IMAGE_TAG             = "hand_image"
OFF_IMAGE_TAG              = "hand_off"
FILE_SEARCH_BOX_TAG        = "file search box"
ANIMATION_ENABLED_TAG      = "animation enabled"
TOGGLE_ADVANCED_TAG        = "toggle advanced"
TOGGLE_OPTIONS_TAG         = "toggle options"
EDITOR_OPTIONS_TAG         = "editor options"
ADVANCED_CONTROLS_TAG      = "advanced controls"
IMAGE_PATH_TAG             = "image path"
IMAGE_NAME_TAG             = "image name"
IMAGE_SIZE_TAG             = "image size"
EXPORT_BUTTON_NP_TAG       = "export button noprompt"
EXPORT_BUTTON_TAG          = "export button"
NO_EXPORT_BUTTON_TAG       = "no export button"
REVERT_BUTTON_TAG          = "revert button"
NO_REVERT_BUTTON_TAG       = "no revert button"
PASTE_FILENAME_TAG         = "paste filename"
DRAWLIST_TAG               = "drawlist"
DRAWLIST_CLICK_HANDLER_TAG = "drawlist click handler"
SAVE_MODAL_TAG             = "save modal"
ANIMATION_FPS_TAG          = "animation fps"
FPS_UP1_TAG                = "fps +"
FPS_UP2_TAG                = "fps ++"
FPS_DOWN1_TAG              = "fps -"
FPS_DOWN2_TAG              = "fps --"
TRANSLATE_X_BOX_TAG        = "translate x box"
TRANSLATE_Y_BOX_TAG        = "translate y box"
TRANSLATE_BACKUPS_TAG      = "translate backups"
TRANSLATE_MODAL_TAG        = "translate modal"
TRANSLATE_HANDLER_TAG      = "translate keyboard handler"
GUN_LAYER_TAG = "gun layer"
IMPORT_DIALOG_TAG = "import dialog"
IMPORT_HANDLER_TAG = "import keyboard handler"
FILE_WIDGET_TAG = "filewidget"

# Misc
ENABLED_STRING    = " Enabled" #note the space
DISABLED_STRING   = "Disabled"
BACKUP_PREFIX     = "json_backup"
EXT_JSON          = ".json"
EXT_JTK2D         = ".jtk2d"
EXT_PNG           = ".png"
HAND_IMAGE_PATH   = resource_path("hand_main.png")
OFF_IMAGE_PATH    = resource_path("hand_off.png")
ENABLED_COLOR     = (64, 128, 64, 255)
DISABLED_COLOR    = (64, 0, 0, 255)
SHORTCUT_COLOR    = (192, 255, 255, 255)
BLACK             = (0, 0, 0, 255)
THIN_WHITE        = (255, 255, 255, 64)
DRAWLIST_PAD      = 64
WINDOW_PAD        = 100
DRAW_INNER_BORDER = False

CachedImage     = namedtuple('CachedImage', ['name', 'data', 'width', 'height'])
AttachPoint     = namedtuple('AttachPoint', ['tag_base', 'name', 'internal_name', 'color', 'shortcut', 'enabled_default'])
TAG_MAIN_HAND   = "main hand"
TAG_OFF_HAND    = "off hand"
TAG_CLIP        = "clip"
TAG_CASING      = "casing"
LABEL_MAIN_HAND = " Main Hand"
LABEL_OFF_HAND  = "  Off Hand"
LABEL_CLIP      = "      Clip"
LABEL_CASING    = "    Casing"
AP_MAIN_HAND    = "PrimaryHand"
AP_OFF_HAND     = "SecondaryHand"
AP_CLIP         = "Clip"
AP_CASING       = "Casing"
_attach_points  = [
  AttachPoint(TAG_MAIN_HAND, LABEL_MAIN_HAND, AP_MAIN_HAND, (255, 255,   0, 255), "Left Click",          ENABLED_STRING ),
  AttachPoint(TAG_OFF_HAND,  LABEL_OFF_HAND,  AP_OFF_HAND,  (255,   0, 255, 255), "Right Click",         DISABLED_STRING),
  AttachPoint(TAG_CLIP,      LABEL_CLIP,      AP_CLIP,      (128, 255, 255, 255), "Shift + Left Click",  DISABLED_STRING),
  AttachPoint(TAG_CASING,    LABEL_CASING,    AP_CASING,    (  0, 255,   0, 255), "Shift + Right Click", ENABLED_STRING),
]
_attach_point_dict   = { p.name : p for p in _attach_points}
_attach_point_coords = { p.name : (0,0) for p in _attach_points}
_attach_point_int    = { p.internal_name : p for p in _attach_points}
_active_attach_point = _attach_points[0]
_advanced_view_active = False;
_gui_scale = 1

#Globals that should probably be refactored
orig_width         = 0
orig_height        = 0
current_file       = ""
current_dir        = ""
current_search     = ""
dir_file_list      = []
filtered_file_list = []
clipboard          = None
clipboard_file     = None
unsaved_changes    = False
file_box           = None
animation_on       = False
animation_speed    = 30

#Config globals and defaults
jconf = {
  (NO_WARN_OVERWRITE := "no_warn_overwrite") : True,
  (NO_WARN_SWITCH    := "no_warn_switch")    : True,
  (AUTOSAVE          := "autosave")          : True,
  (SHOW_HANDS        := "show_hands")        : True,
  (MAKE_BACKUPS      := "make_backups")      : True,
  (USE_JTK2D         := "use_jtk2d")         : True,
  (AUTOSCROLL        := "autoscroll")        : False,
  (HIGH_DPI          := "high_dpi")          : False,
  (TOOLTIPS          := "show_tooltips")     : False,
  (LAST_FILE         := "last_file")         : None,
}

class BetterListBox:
    custom_listbox_theme  = None
    button_selected_theme = None
    button_normal_theme   = None
    custom_listbox        = None
    callback              = None
    items                 = []
    visible_items         = None
    width                 = None
    height                = None
    parent                = None
    force_autoscroll      = False

    cur_index             = 0

    def __init__(self, items: list, width: int = -1, height: int = -1, parent: int | str = None, callback: callable = None):
        parent = parent or dpg.last_container()
        self.callback = callback
        self.width    = width
        self.height   = height
        self.parent   = parent

        with dpg.theme() as self.custom_listbox_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0,0)
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0, 0.5)

        with dpg.theme() as self.button_selected_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (0,119,200,153))

        with dpg.theme() as self.button_normal_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (51, 51, 55, 255))

        # with dpg.child_window(height=self.height, width=self.width, border=False, parent=self.parent) as self.custom_listbox:
        with dpg.child_window(autosize_y=False, height=height, width=self.width, border=False, parent=self.parent) as self.custom_listbox:
          pass
        dpg.bind_item_theme(self.custom_listbox, self.custom_listbox_theme)

        self.replace_items(items)

    def replace_items(self, items):
        for i,item in enumerate(self.items):
          dpg.delete_item(item)

        self.cur_index = 0
        self.items         = []
        for i,item in enumerate(items): #TODO: figure out how to nuke old items so we don't leak memory
            newitem = dpg.add_button(parent=self.custom_listbox, label=item, width=-1, callback=self.scroll_and_invoke_callback)
            self.items.append(newitem)
        self.visible_items = range(len(self.items))

    def filter_items(self, query):
        self.visible_items = []
        sel_is_visible = True
        for i, item in enumerate(self.items):
          show = (query in dpg.get_item_label(item))
          dpg.configure_item(item, show=show)
          if show:
            self.visible_items.append(i)
          elif i == self.cur_index:
            sel_is_visible = False
        if (not sel_is_visible) and len(self.visible_items) > 0:
          self.scroll_and_invoke_callback(self.items[self.visible_items[0]])

    def scroll_and_invoke_callback(self, sender):
        if self.callback:
            self.callback(dpg.get_item_parent(sender), dpg.get_item_label(sender))
        dpg.bind_item_theme(self.items[self.cur_index], self.button_normal_theme)
        self.cur_index = self.items.index(sender)
        dpg.bind_item_theme(sender, self.button_selected_theme)
        if get_config(AUTOSCROLL) or self.force_autoscroll:
          self.force_autoscroll = False
          dpg.set_y_scroll(self.custom_listbox, max(0,dpg.get_item_state(sender)["pos"][1] - self.height / 2))

    def scroll_to_specific_item(self, itemname):
        truename = os.path.basename(itemname).replace(pref_ext(), "").replace(alt_ext() ,"")
        for item in self.items:
          if dpg.get_item_label(item) == truename:
            self.force_autoscroll = True
            self.scroll_and_invoke_callback(item)
            break

    def change_item(self, delta):
      num_vis_items = len(self.visible_items)
      if num_vis_items == 0:
        return # shouldn't do anything if nothing is visible

      try:
        vis_index = (num_vis_items + self.visible_items.index(self.cur_index) + delta) % num_vis_items
      except ValueError:
        vis_index = 0

      self.scroll_and_invoke_callback(self.items[self.visible_items[vis_index]])

    name_rx = re.compile(r"(.*)_[0-9]+(\.[^\.]*)?")
    def get_animation_root(self, name):
      return self.name_rx.sub(r"\1",name)

    root      = None # the root name of our current animation name
    frames    = None # indices of the frames corresponding to our current animation
    cur_frame = 0    # the current frame of our animation playing
    def advance_frame(self):
      if self.cur_index < len(self.items):
        cur_root = self.get_animation_root(dpg.get_item_label(self.items[self.cur_index]))
      else:
        cur_root = None

      # Figure out the name of our current animation if necessary
      if self.root != cur_root:
        self.root = cur_root
        self.frames = []
        self.cur_frame = 0
        for i,item in enumerate(self.items):
          if self.get_animation_root(dpg.get_item_label(item)) == cur_root:
            self.frames.append(i)

      if (self.root is None) or ((nframes := len(self.frames)) < 1):
        return
      self.cur_frame = (self.cur_frame + 1) % nframes
      self.scroll_and_invoke_callback(self.items[self.frames[self.cur_frame]])

def preview_scale():
  return PREVIEW_SCALE * _gui_scale

def get_config_path():
  if 'APPDATA' in os.environ:
    confighome = os.environ['APPDATA']
  elif 'XDG_CONFIG_HOME' in os.environ:
      confighome = os.environ['XDG_CONFIG_HOME']
  else:
      confighome = os.path.join(os.environ['HOME'], '.config')
  return os.path.join(confighome, f"{PROGRAM_NAME}-config.json")

def load_config():
  global jconf
  config_path = get_config_path()
  if not os.path.exists(config_path):
    set_config()

  with open(config_path, 'r') as fin:
    jconf.update(json.load(fin))

  for k, v in jconf.items():
    if dpg.does_item_exist(config_tag(k)):
      dpg.set_value(config_tag(k), v)

def config_tag(key):
  return f"config {key}"

def get_config(key):
  return jconf.get(key,False)

def set_config(key = None, value = None):
  if key is not None and value is not None:
    jconf[key] = value
  with open(get_config_path(), 'w') as fout:
    fout.write(json.dumps(jconf,indent=2))
  if unsaved_changes: # change the export button to the noprompt version if necessary
    mark_unsaved_changes()

def mark_unsaved_changes():
  global unsaved_changes
  unsaved_changes = True
  enable_save_modal()
  if get_config(NO_WARN_OVERWRITE):
    dpg.configure_item(EXPORT_BUTTON_NP_TAG, show=True)
    dpg.configure_item(EXPORT_BUTTON_TAG, show=False)
  else:
    dpg.configure_item(EXPORT_BUTTON_NP_TAG, show=False)
    dpg.configure_item(EXPORT_BUTTON_TAG, show=True)
  dpg.configure_item(REVERT_BUTTON_TAG, show=True)
  dpg.configure_item(NO_EXPORT_BUTTON_TAG, show=False)
  dpg.configure_item(NO_REVERT_BUTTON_TAG, show=False)

def clear_unsaved_changes():
  global unsaved_changes
  unsaved_changes = False
  disable_save_modal()
  dpg.configure_item(EXPORT_BUTTON_TAG, show=False)
  dpg.configure_item(EXPORT_BUTTON_NP_TAG, show=False)
  dpg.configure_item(REVERT_BUTTON_TAG, show=False)
  dpg.configure_item(NO_EXPORT_BUTTON_TAG, show=True)
  dpg.configure_item(NO_REVERT_BUTTON_TAG, show=True)

def pref_ext(): # preferred file extension
  if get_config(USE_JTK2D):
    return EXT_JTK2D
  return EXT_JSON

def alt_ext(): # alternate file extension
  if get_config(USE_JTK2D):
    return EXT_JSON
  return EXT_JTK2D

def enable_save_modal():
  if dpg.does_item_exist(SAVE_MODAL_TAG):
    return # no need to enable a modal that's already enabled

  export_path = os.path.join(current_dir,current_file).replace(EXT_PNG, pref_ext())
  if not os.path.exists(export_path):
    return # no need for a modal if we're saving to a new file

  with dpg.popup(EXPORT_BUTTON_TAG, modal=True, mousebutton=dpg.mvMouseButton_Left, no_move=True, tag=SAVE_MODAL_TAG):
    dpg.add_text(f"Overwite existing file?\n  {export_path}")
    dpg.add_separator()
    with dpg.group(horizontal=True):
      dpg.add_button(label="Yes", width=75, callback=lambda: export_callback())
      dpg.add_button(label="No", width=75, callback=lambda: dpg.configure_item(SAVE_MODAL_TAG, show=False))

def disable_save_modal():
  if dpg.does_item_exist(SAVE_MODAL_TAG):
    dpg.delete_item(SAVE_MODAL_TAG)

def colorize_button(button, color = None):
  if color is None:
    dpg.bind_item_theme(button, "")
    return

  theme_tag = f"{color} colored button theme"
  if not dpg.does_item_exist(theme_tag):
    with dpg.theme(tag=theme_tag):
      with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, color)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, color)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, color)

  dpg.bind_item_theme(button, theme_tag)

def copy_state():
  global clipboard, clipboard_file
  clipboard = get_json_for_current_gun()
  dpg.set_value(PASTE_FILENAME_TAG, f"from {current_file}")

def paste_state():
  if clipboard is not None:
    load_json_from_dict(clipboard)
    mark_unsaved_changes()

def colorize_last_button(color):
  colorize_button(dpg.last_item(), color)

def get_basic_gun_json(width, height):
  return {
    "name"   : None,
    "x"      : 0,
    "y"      : 0,
    "width"  : width,
    "height" : height,
    "flip"   : 1,
    "attachPoints": [
      {
        "."    : "arraytype",
        "name" : "array",
        "size" : 0,
      },
    ],
  }

def get_default_gun_json(width, height):
  return {
    "name"   : None,
    "x"      : 0,
    "y"      : 0,
    "width"  : width,
    "height" : height,
    "flip"   : 1,
    "attachPoints": [
      {
        "."    : "arraytype",
        "name" : "array",
        "size" : 2,
      },
      {
        "name"     : AP_MAIN_HAND,
        "position" : {
          "x" : 0.4375,
          "y" : 0.4375,
          "z" : 0.0
        },
        "angle": 0.0
      },
      {
        "name"    : AP_CASING,
        "position": {
          "x" : 0.5625,
          "y" : 0.375,
          "z" : 0.0
        },
      },
    ],
  }

def add_positional_element(basejson, name, x, y):
  basejson["attachPoints"] += [{
      "name"     : name,
      "position" : {
         "x": float(x),
         "y": float(y),
         "z": 0.0,
      },
      "angle"    : 0.0,
    }]
  basejson["attachPoints"][0]["size"] += 1

def apc_enabled(p)  : return f"{p.tag_base} enabled"
def apc_shortcut(p) : return f"{p.tag_base} shortcut box"
def apc_controls(p) : return f"{p.tag_base} controls"
def apc_x(p)        : return f"{p.tag_base} x box"
def apc_y(p)        : return f"{p.tag_base} y box"
def apc_layer(p)    : return f"{p.tag_base} layer"
def apc_circle(p)   : return f"{p.tag_base} circle"

def get_json_for_current_gun():
  basejson = get_basic_gun_json(orig_width, orig_height)
  for p in _attach_points:
    if dpg.get_item_label(apc_enabled(p)) == ENABLED_STRING:
      add_positional_element(basejson, p.internal_name, dpg.get_value(apc_x(p)), dpg.get_value(apc_y(p)))
  return basejson

def export_callback():
  global unsaved_changes
  if not unsaved_changes:
    return # no changes since last export

  export_path = os.path.join(current_dir,current_file).replace(EXT_PNG, pref_ext())
  with open(export_path,'w') as fout:
    fout.write(json.dumps(get_json_for_current_gun(),indent=2))
  # subprocess.Popen(shlex.split(f"subl {export_path}"))

  clear_unsaved_changes()

def revert_callback():
  global unsaved_changes
  if not unsaved_changes:
    return

  clear_unsaved_changes()
  fullpath = os.path.join(current_dir, current_file)
  load_gun_image(fullpath)
  jsonpath = fullpath.replace(EXT_PNG, pref_ext())
  if not os.path.exists(jsonpath):
    jsonpath = fullpath.replace(EXT_PNG, alt_ext())
  if os.path.exists(jsonpath):
    load_json_from_file(jsonpath)

def pos_in_drawing_area(x, y):
  dx, dy = dpg.get_item_rect_min(DRAWLIST_TAG)
  dy -= DRAWLIST_PAD / 2 #TODO: not really sure why the rectangle above is offset...
  dw, dh = dpg.get_item_rect_size(DRAWLIST_TAG)

  # print(f"checking {x},{y} within {dx,dy}...{dx+dw},{dy+dh}")
  return x >= dx and x <= (dx+dw) and y >= dy and y <= (dy+dh)

def fromJsonCoordinates(x,y):
  canvas_height = preview_scale() * float(orig_height)
  canvasx = DRAWLIST_PAD + (x * (preview_scale() * PIXELS_PER_TILE))
  canvasy = DRAWLIST_PAD + canvas_height - (y * (preview_scale() * PIXELS_PER_TILE)) # we have an inverted y axis
  return canvasx, canvasy

def toJsonCoordinates(x,y):
  canvas_height = preview_scale() * float(orig_height)
  jsonx = (x - DRAWLIST_PAD) / (preview_scale() * PIXELS_PER_TILE)
  jsony = (canvas_height - (y - DRAWLIST_PAD)) / (preview_scale() * PIXELS_PER_TILE) # we have an inverted y axis
  return jsonx, jsony

def redraw_attach_point(p):
  # Verify we're actually enabled
  if not attach_point_enabled(p):
    return

  # Delete and redraw the hand drawing layer
  layer = apc_layer(p)
  if dpg.does_alias_exist(layer):
    dpg.delete_item(layer)
  dpg.push_container_stack(DRAWLIST_TAG)
  dpg.add_draw_layer(tag=layer)
  dpg.pop_container_stack()

  # Redraw the hand at the designated position
  dpg.push_container_stack(layer)
  center = _attach_point_coords[p.name]
  if get_config(SHOW_HANDS) and ("hand" in p.tag_base):
    # offset = center+preview_scale()*(DRAWLIST_PAD,DRAWLIST_PAD)
    offset = (center[0] - 2*preview_scale(), center[1] - 2*preview_scale())
    # dpg.draw_image(HAND_IMAGE_TAG, center=_attach_point_coords[p.name], tag=f"{p.tag_base} hand")
    # dpg.draw_image(HAND_IMAGE_TAG, offset, offset + (4*preview_scale(), 4*preview_scale()), tag=f"{p.tag_base} circle")
    dpg.draw_image(HAND_IMAGE_PATH if "main" in p.tag_base else OFF_IMAGE_PATH, offset, (offset[0] + 4*preview_scale(), offset[1] + 4*preview_scale()), tag=apc_circle(p))
  else:
    dpg.draw_circle(center=center, radius=preview_scale(), color=BLACK, fill=p.color, tag=apc_circle(p))
  dpg.pop_container_stack()

def attach_point_enabled(p):
  return dpg.get_item_label(apc_enabled(p)) != DISABLED_STRING

def move_hand_preview(x, y, p=None):
  global _attach_point_coords

  # Get the active attach point from the environment if not specified
  if p is None:
    p = _active_attach_point
  if not attach_point_enabled(p):
    # print(f"{p.tag_base} is disabled")
    return # return if our element is disabled

  # Round x and y values as necessary to snap to the grid
  # x = max(DRAWLIST_PAD, min(DRAWLIST_PAD + orig_width * preview_scale(), round(x / preview_scale()) * preview_scale()))
  # y = max(DRAWLIST_PAD, min(DRAWLIST_PAD + orig_height * preview_scale(), round(y / preview_scale()) * preview_scale()))
  x = round(x / preview_scale()) * preview_scale() #NOTE: need to allow these to go offscreen for batch translating purposes
  y = round(y / preview_scale()) * preview_scale() #NOTE: need to allow these to go offscreen for batch translating purposes

  # Set the global coordinates (TODO: maybe don't use globals here)
  _attach_point_coords[p.name] = (x,y)
  # Get the real coordinates of the hand wrt what the JSON expects
  realx, realy = toJsonCoordinates(*_attach_point_coords[p.name])
  # ...and update the boxes
  dpg.set_value(apc_x(p), realx)
  dpg.set_value(apc_y(p), realy)

  # Redraw the attach point
  redraw_attach_point(p)

def on_plot_clicked(sender, app_data):
  toggle_animation(False)
  if dpg.is_key_down(dpg.mvKey_Shift):
    p=_attach_point_dict[LABEL_CLIP]
  else:
    p=_attach_point_dict[LABEL_MAIN_HAND]
  move_hand_preview(*dpg.get_drawing_mouse_pos(), p=p)
  # Mark our unsaved changes state
  mark_unsaved_changes()

def on_plot_right_clicked(sender, app_data):
  toggle_animation(False)
  if dpg.is_key_down(dpg.mvKey_Shift):
    p=_attach_point_dict[LABEL_CASING]
  else:
    p=_attach_point_dict[LABEL_OFF_HAND]
  move_hand_preview(*dpg.get_drawing_mouse_pos(), p=p)
  # Mark our unsaved changes state
  if dpg.get_item_label(apc_enabled(p)) != DISABLED_STRING:
    mark_unsaved_changes()

def on_mouse_dragged(sender, app_data):
  if not pos_in_drawing_area(*dpg.get_mouse_pos()):
    return #note get_mouse_pos() and get_drawing_mouse_pos() are not the same
  on_plot_clicked(sender, app_data)

def on_right_mouse_dragged(sender, app_data):
  if not pos_in_drawing_area(*dpg.get_mouse_pos()):
    return #note get_mouse_pos() and get_drawing_mouse_pos() are not the same
  on_plot_right_clicked(sender, app_data)

def change_active_attach_point(sender, app_data):
  global _active_attach_point
  _active_attach_point = _attach_point_dict[app_data]

def toggle_attach_point(p, override=None, refresh=False):
  cur_enabled = dpg.get_item_label(apc_enabled(p)) == ENABLED_STRING
  new_enabled = cur_enabled if refresh else (not cur_enabled) if override is None else override
  dpg.configure_item(apc_x(p), show=new_enabled and _advanced_view_active)
  dpg.configure_item(apc_y(p), show=new_enabled and _advanced_view_active)
  dpg.configure_item(apc_shortcut(p), show=new_enabled) #
  dpg.set_item_label(apc_enabled(p), ENABLED_STRING if new_enabled else DISABLED_STRING)
  colorize_button(apc_enabled(p), ENABLED_COLOR if new_enabled else DISABLED_COLOR)

  layer = apc_layer(p)
  if dpg.does_alias_exist(layer):
    dpg.configure_item(layer, show=new_enabled)
  mark_unsaved_changes()

def toggle_animation(override=None):
  global animation_on
  cur_enabled = dpg.get_item_label(ANIMATION_ENABLED_TAG) == ENABLED_STRING
  new_enabled = (not cur_enabled) if override is None else override
  animation_on = new_enabled
  dpg.set_item_label(ANIMATION_ENABLED_TAG, ENABLED_STRING if new_enabled else DISABLED_STRING)
  colorize_button(ANIMATION_ENABLED_TAG, ENABLED_COLOR if new_enabled else DISABLED_COLOR)
  dpg.configure_item(FPS_DOWN2_TAG, show=new_enabled) #
  dpg.configure_item(FPS_DOWN1_TAG, show=new_enabled) #
  dpg.configure_item(ANIMATION_FPS_TAG, show=new_enabled) #
  dpg.configure_item(FPS_UP1_TAG, show=new_enabled) #
  dpg.configure_item(FPS_UP2_TAG, show=new_enabled) #

def generate_controls(p):
  name = p.name
  tag_base = p.tag_base
  label = p.enabled_default
  with dpg.group(horizontal=True, tag=apc_controls(p)):
    dpg.add_text(f"{name}: ",color=p.color)
    dpg.add_button(label=label, callback=lambda: toggle_attach_point(p), tag=apc_enabled(p))
    with dpg.tooltip(dpg.last_item(), tag=auto_tooltip()): dpg.add_text(f"Shortcut: Ctrl + {1 + _attach_points.index(p)}")
    colorize_button(apc_enabled(p), ENABLED_COLOR if label==ENABLED_STRING else DISABLED_COLOR)
    dpg.add_input_text(label="x", width=70, readonly=True, show=label==ENABLED_STRING, tag=apc_x(p), default_value="0.0000")
    dpg.add_input_text(label="y", width=70, readonly=True, show=label==ENABLED_STRING, tag=apc_y(p), default_value="0.0000")
    dpg.add_text(f"{p.shortcut}", color=p.color, tag=apc_shortcut(p))

image_cache = {}
def load_scaled_image(filename):
  if (filename in image_cache):
    # print(f"using cached {filename}")
    return image_cache[filename]

  scale = preview_scale()
  pil_image = Image.open(filename)
  if pil_image.mode != "RGBA":
    pil_image = pil_image.convert(mode='RGBA')
  orig_width, orig_height = pil_image.size
  scaled_width, scaled_height = scale * orig_width, scale * orig_height
  scaled_image = pil_image.resize((scaled_width, scaled_height), resample=Image.Resampling.NEAREST)
  dpg_image = np.frombuffer(scaled_image.tobytes(), dtype=np.uint8) / 255.0
  image_cache[filename] = (dpg_image, orig_width, orig_height)
  with dpg.texture_registry():
    if dpg.does_alias_exist(filename):
      print("should be impossible")
      dpg.remove_alias(filename)
      dpg.delete_item(filename)
    dpg.add_static_texture(width=scaled_width, height=scaled_height, default_value=dpg_image, tag=filename)
  return image_cache[filename]

def refresh_file_list():
  global dir_file_list, filtered_file_list
  dir_file_list = sorted([f[:-4] for f in filter(lambda x: x.endswith(EXT_PNG), os.listdir(current_dir))])
  filtered_file_list = dir_file_list
  update_file_list(filtered_file_list)

def load_gun_image(filename):
  global orig_width, orig_height, current_file, current_dir

  # Export our current image if we have unsaved changes and autosave is on
  if unsaved_changes and get_config(AUTOSAVE):
    export_callback()

  # Load and resize the image internally since pygui doesn't seem to support nearest neighbor scaling
  pil_image, orig_width, orig_height = load_scaled_image(filename)
  scaled_width, scaled_height = preview_scale() * orig_width, preview_scale() * orig_height

  # Set our current file as appropriate
  old_dir      = current_dir
  current_dir  = os.path.dirname(filename)
  changed_dir  = current_dir != old_dir
  current_file = os.path.basename(filename)

  # Refresh all of our canvas and metadata data
  dpg.set_value(IMAGE_PATH_TAG, f"Working Dir: {current_dir}")
  dpg.set_value(IMAGE_NAME_TAG, f"Image Name:  {current_file}")
  dpg.set_value(IMAGE_SIZE_TAG, f"Image Size:  {orig_width} x {orig_height} pixels")
  dpg.configure_item(DRAWLIST_TAG, width=DRAWLIST_PAD*2+scaled_width, height=DRAWLIST_PAD*2+scaled_height)
  if dpg.does_alias_exist(GUN_LAYER_TAG):
    dpg.delete_item(GUN_LAYER_TAG)
  dpg.push_container_stack(DRAWLIST_TAG)
  with dpg.draw_layer(tag=GUN_LAYER_TAG):
    #Draw outer border
    dpg.draw_rectangle((0,0), (DRAWLIST_PAD*2+scaled_width,DRAWLIST_PAD*2+scaled_height))
    #Draw inner border
    if DRAW_INNER_BORDER:
      dpg.draw_rectangle((DRAWLIST_PAD,DRAWLIST_PAD), (DRAWLIST_PAD+scaled_width,DRAWLIST_PAD+scaled_height),color=THIN_WHITE)
    #Draw sprite itself
    dpg.draw_image(filename, (DRAWLIST_PAD,DRAWLIST_PAD), (DRAWLIST_PAD+scaled_width, DRAWLIST_PAD+scaled_height))
  dpg.pop_container_stack()

  if changed_dir:
    refresh_file_list()

  load_json_from_dict(get_default_gun_json(orig_width, orig_height)) #TODO: can possibly be removed, i can't remember if this is a hack to make something work
  clear_unsaved_changes()
  set_config(LAST_FILE, filename)

def update_file_list(filelist):
    # dpg.configure_item(FILE_PICKER_TAG, items=filelist, default_value=current_file.replace(".png",""))
    file_box.replace_items(filelist)

def load_json_from_dict(jdata):
  midx = (jdata.get("width", 0) // 2) / 16.0
  midy = (jdata.get("height", 0) // 2) / 16.0
  jpoints = jdata.get("attachPoints", [])
  # Temporarily disable all previews
  for p in _attach_points:
    toggle_attach_point(p, override=True)
    found = False
    for a in jpoints:
      if a["name"] != p.internal_name:
        continue
      px = a.get("position",{}).get("x", 0)
      py = a.get("position",{}).get("y", 0)
      cx, cy = fromJsonCoordinates(px,py)
      move_hand_preview(cx, cy, p)
      found = True
      break
    if found:
      continue
    # Disable previews for undefined attach points, and put the offsets at sane positios
    cx, cy = fromJsonCoordinates(midx, midy)
    move_hand_preview(cx, cy, p)
    toggle_attach_point(p, override=False)

def load_json_from_file(filename):
  # Load the JSON data
  with open(filename, 'r') as fin:
    jdata = json.load(fin)
  load_json_from_dict(jdata)

def set_current_file_from_import_dialog(sender, app_data):
  dpg.configure_item(IMPORT_DIALOG_TAG, show=False)

  items = app_data.get("selections",{}).items()
  if len(items) == 0:
    newpath = app_data.get("current_path", None)
    if newpath is not None: # navigate to a new directory if we have no files selected
      open_import_dialog(override_dir = newpath)
    return

  stem = None
  for _, filename in items:
    stem = filename.replace(pref_ext(), "").replace(alt_ext(), "").replace(EXT_PNG,"")
    break

  if stem is None:
    return
  if not os.path.exists(f"{stem}{EXT_PNG}"):
    return

  load_gun_image(f"{stem}{EXT_PNG}")
  if os.path.exists(f"{stem}{pref_ext()}"):
    load_json_from_file(f"{stem}{pref_ext()}")
  elif os.path.exists(f"{stem}{alt_ext()}"):
    load_json_from_file(f"{stem}{alt_ext()}")
  file_box.scroll_to_specific_item(f"{stem}")

def set_current_file_from_picker_box(sender, file_stem):
  fullpath = os.path.join(current_dir, file_stem)
  if os.path.exists(f"{fullpath}{EXT_PNG}"):
    load_gun_image(f"{fullpath}{EXT_PNG}")
    if os.path.exists(f"{fullpath}{pref_ext()}"):
      load_json_from_file(f"{fullpath}{pref_ext()}")
    if os.path.exists(f"{fullpath}{alt_ext()}"):
      load_json_from_file(f"{fullpath}{alt_ext()}")
    clear_unsaved_changes()

def open_import_dialog(override_dir = None):
  if override_dir is None:
    override_dir = current_dir
  if dpg.does_item_exist(IMPORT_DIALOG_TAG):
    if dpg.does_item_exist(IMPORT_HANDLER_TAG):
      dpg.delete_item(IMPORT_HANDLER_TAG)
    dpg.delete_item(IMPORT_DIALOG_TAG)
  with dpg.file_dialog(label="Open Gun PNG or JSON", width=700, height=400, modal=True, show=True, default_path=override_dir, callback=set_current_file_from_import_dialog, tag=IMPORT_DIALOG_TAG):
    dpg.add_file_extension("Gungeon Data files {.png,.json,.jtk2d}", color=(0, 255, 255, 255))
    dpg.add_file_extension(EXT_PNG, color=(255, 255, 0, 255))
    dpg.add_file_extension(pref_ext(), color=(255, 0, 255, 255))
    dpg.add_file_extension(alt_ext(), color=(255, 0, 255, 255))
    with dpg.handler_registry(tag=IMPORT_HANDLER_TAG):
      dpg.add_key_release_handler(key=dpg.mvKey_Escape, callback=lambda: dpg.configure_item(IMPORT_DIALOG_TAG, show=False))
      dpg.add_key_release_handler(key=dpg.mvKey_Return, callback=lambda: set_current_file_from_import_dialog(None, dpg.get_file_dialog_info(IMPORT_DIALOG_TAG)))

def filter_files(_, query):
  global current_search, filtered_file_list, dir_file_list
  # if current_search in query:
  #   base_list = filtered_file_list # slight optimization for not looking through whole file list
  # else:
  #   base_list = dir_file_list
  # filtered_file_list = [f for f in base_list if query in f]
  # update_file_list(filtered_file_list)
  file_box.filter_items(query)
  current_search = query

def save_changes_from_shortcut():
  toggle_animation(False)
  if jconf[NO_WARN_OVERWRITE]:
    export_callback()
  else:
    print("checking...")
    if dpg.does_item_exist(SAVE_MODAL_TAG):
      # print("found modal")
      dpg.configure_item(SAVE_MODAL_TAG, show=True)
    else:
      export_callback()

def toggle_hands(switch, value):
  set_config(SHOW_HANDS, value)
  redraw_attach_point(_attach_point_dict[LABEL_MAIN_HAND])
  redraw_attach_point(_attach_point_dict[LABEL_OFF_HAND])

def toggle_backups(switch, value):
  set_config(MAKE_BACKUPS, value)

def toggle_jtk2d(switch, value):
  set_config(USE_JTK2D, value)

_tooltips = []
def auto_tooltip():
  tt = f"auto tooltip {len(_tooltips)}"
  _tooltips.append(tt)
  return tt

def toggle_tooltips(switch, value):
  set_config(TOOLTIPS, value)
  for tt in _tooltips:
    dpg.configure_item(tt, show=value)

def toggle_high_dpi(switch, value):
  set_config(HIGH_DPI, value)
  resize_gui(reload = True)

def resize_gui(reload = False):
  global _gui_scale
  _gui_scale = 2 if get_config(HIGH_DPI) else 1
  dpg.set_global_font_scale(_gui_scale)
  dpg.configure_item(FILE_WIDGET_TAG, width=_gui_scale * 300)
  if reload:
    load_gun_image(os.path.join(current_dir, current_file))

def next_file(delta):
  file_box.change_item(delta)

def change_animation_speed(delta):
  global animation_speed
  animation_speed += delta
  if (animation_speed < 1):
    animation_speed = 1
  elif (animation_speed > 60):
    animation_speed = 60
  dpg.set_value(ANIMATION_FPS_TAG, f"{animation_speed} FPS")

def show_translate_modal():
  toggle_animation(False)
  cur_json = os.path.join(current_dir,current_file.replace(EXT_PNG, pref_ext()))
  if not os.path.exists(cur_json):
    cur_json = os.path.join(current_dir,current_file.replace(EXT_PNG, alt_ext()))
  if not os.path.exists(cur_json):
    return # bail out if we the current json doesn't exist

  # try to get the current gun's saved attach points
  oldx = None
  oldy = None
  with open(cur_json, 'r') as fin:
    jdata = json.load(fin)
    if "attachPoints" not in jdata:
      return
    for i in range(1, len(jdata["attachPoints"])):
      if jdata["attachPoints"][i]["name"] != AP_MAIN_HAND:
        continue
      pos = jdata["attachPoints"][i]["position"]
      oldx = pos["x"]
      oldy = pos["y"]
      break
  if (oldx is None) or (oldy is None):
    return # failed to read necessary JSON data
  newx, newy = toJsonCoordinates(*_attach_point_coords[LABEL_MAIN_HAND])

  if dpg.does_item_exist(TRANSLATE_MODAL_TAG):
    dpg.configure_item(TRANSLATE_MODAL_TAG, show=True)
    return # if the dialog is already created, just show it

  # get the base animation name and load all available jsons with the same name
  root_name = file_box.get_animation_root(current_file)
  jsons = []
  for i,item in enumerate(file_box.items):
    label = dpg.get_item_label(item)
    if file_box.get_animation_root(label) != root_name:
      continue
    jpath = os.path.join(current_dir,f"{label}{pref_ext()}")
    if not os.path.exists(jpath):
      continue
    jsons.append(jpath)

  # create a modal dialog for translating all attach points corresponding to a sprite by the specified amount
  with dpg.popup(EXPORT_BUTTON_TAG, modal=True, mousebutton=dpg.mvMouseButton_Left, no_move=True, tag=TRANSLATE_MODAL_TAG):
    dpg.add_text(f"Translating {len(jsons)} sprites matching:")
    dpg.add_text(f"{root_name}_###", color=(192,255,128))
    dpg.add_separator()
    # dpg.add_checkbox(label="Translate All Animations for This Gun", tag="translate all")
    dpg.add_checkbox(label="Make Backups", tag=TRANSLATE_BACKUPS_TAG, default_value=get_config(MAKE_BACKUPS))
    dpg.add_input_float(label=f"x: {int(16 * (newx - oldx))}px", width=150, tag=TRANSLATE_X_BOX_TAG, format="%.04f", step=1.0/16.0, default_value=(newx - oldx),
      callback=lambda: dpg.configure_item(TRANSLATE_X_BOX_TAG, label=f"""x: {int(16 * dpg.get_value(TRANSLATE_X_BOX_TAG))}px"""))
    dpg.add_input_float(label=f"y: {int(16 * (newy - oldy))}px", width=150, tag=TRANSLATE_Y_BOX_TAG, format="%.04f", step=1.0/16.0, default_value=(newy - oldy),
      callback=lambda: dpg.configure_item(TRANSLATE_Y_BOX_TAG, label=f"""y: {int(16 * dpg.get_value(TRANSLATE_Y_BOX_TAG))}px"""))
    dpg.add_separator()
    dpg.add_text(f"TIP: you can prepopulate the fields above by moving the primary hand attach point in the editor")
    dpg.add_separator()
    with dpg.group(horizontal=True):
      dpg.add_button(label="Translate", width=75, callback=lambda: translate_jsons(jsons))
      dpg.add_button(label="Cancel", width=75, callback=lambda: hide_translate_modal())
    with dpg.handler_registry(tag=TRANSLATE_HANDLER_TAG):
      dpg.add_key_release_handler(key=dpg.mvKey_Escape, callback=lambda: hide_translate_modal())
  dpg.configure_item(TRANSLATE_MODAL_TAG, show=True)

def translate_jsons(jsons):
  # get necessary paramters
  xshift = dpg.get_value(TRANSLATE_X_BOX_TAG)
  yshift = dpg.get_value(TRANSLATE_Y_BOX_TAG)
  backup = dpg.get_value(TRANSLATE_BACKUPS_TAG)

  # make backups as necessary
  if backup:
    bpath = os.path.join(current_dir,f"{BACKUP_PREFIX}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
    os.makedirs(bpath)
    for j in jsons:
      shutil.copy(j, os.path.join(bpath,os.path.basename(j)))

  # Adjust attach points for all JSONs in the batch
  for j in jsons:
    with open(j, 'r') as fin:
      jdata = json.load(fin)
    if "attachPoints" not in jdata:
      continue
    for i in range(1, len(jdata["attachPoints"])):
      jdata["attachPoints"][i]["position"]["x"] += xshift
      jdata["attachPoints"][i]["position"]["y"] += yshift
    with open(j, 'w') as fout:
      fout.write(json.dumps(jdata, indent=2))

  # Hide the modal and reload the current gun's JSON
  hide_translate_modal()
  load_json_from_file(os.path.join(current_dir,current_file.replace(EXT_PNG, pref_ext())))

def hide_translate_modal():
  if dpg.does_item_exist(TRANSLATE_HANDLER_TAG):
    dpg.delete_item(TRANSLATE_HANDLER_TAG)
  if dpg.does_item_exist(TRANSLATE_MODAL_TAG):
    dpg.configure_item(TRANSLATE_MODAL_TAG, show=False)
    dpg.delete_item(TRANSLATE_MODAL_TAG)

def control_pressed():
  return dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)

def no_modal_open():
  return dpg.get_item_state(MAIN_WINDOW_TAG)["focused"]

def toggle_advanced_view():
  global _advanced_view_active
  _advanced_view_active = not dpg.is_item_visible(ADVANCED_CONTROLS_TAG)
  dpg.configure_item(ADVANCED_CONTROLS_TAG, show=_advanced_view_active)
  dpg.configure_item(TOGGLE_ADVANCED_TAG, label="Show Basic View" if _advanced_view_active else "Show Advanced View")
  for p in _attach_points:
    toggle_attach_point(p, refresh=True)

def toggle_options():
  newoptions = not dpg.is_item_visible(EDITOR_OPTIONS_TAG)
  dpg.configure_item(EDITOR_OPTIONS_TAG, show=newoptions)
  dpg.configure_item(TOGGLE_OPTIONS_TAG, label="Hide Options" if newoptions else "More Options")

def main(filename):
  global orig_width, orig_height, file_box

  # Make sure we actually have a valid filename passed (or None)
  if (filename is not None) and (not os.path.exists(filename)):
    print(f"{filename} doesn't exist!")
    return

  # Get main monitor info
  for m in screeninfo.get_monitors():
    mw, mh = m.width, m.height
    break

  # Compute window dimensions
  ww = mw - 2 * WINDOW_PAD
  wh = mh - 2 * WINDOW_PAD

  # Set up dearpygui
  dpg.create_context()
  dpg.create_viewport(title=f"Enter the Gungeon - {PROGRAM_TITLE} - v{PROGRAM_VERSION}", x_pos=WINDOW_PAD, y_pos=WINDOW_PAD, width=ww, height=wh, resizable=False)
  dpg.setup_dearpygui()

  # Load necessary assets
  load_scaled_image(HAND_IMAGE_PATH)
  load_scaled_image(OFF_IMAGE_PATH)

  # Load fonts
  # FONT_PATH = "/xmedia/bigbois/texmf-dist/fonts/truetype/public/gnu-freefont/FreeMonoBold.ttf"
  # if os.path.exists(FONT_PATH):
  #   with dpg.font_registry():
  #     default_font = dpg.add_font(FONT_PATH, 30)
  #   dpg.bind_font(default_font)

  # Set up the main window
  with dpg.window(label="Files List", tag=MAIN_WINDOW_TAG, width=ww, height=wh, no_resize=True, autosize=False, no_close=True, no_collapse=True, no_title_bar=True, no_move=True):
    with dpg.group(horizontal=True, tag="topwidget"):
      # Set up our file picker box
      with dpg.group(horizontal=False, width=300, tag=FILE_WIDGET_TAG) as filewidgetgroup: # need vertical buttons or dpg doesn't size them properly
        dpg.add_button(label="Open Gun For Editing", callback=lambda: open_import_dialog(), tag="import button", show=True)
        with dpg.tooltip(dpg.last_item(), tag=auto_tooltip()): dpg.add_text("Shortcut: Ctrl + O")
        dpg.add_button(label="Refresh Gun List", callback=lambda: refresh_file_list(), tag=f"refresh files")
        with dpg.tooltip(dpg.last_item(), tag=auto_tooltip()): dpg.add_text("Shortcut: F5")
        dpg.add_button(label="Show Advanced View", callback=toggle_advanced_view, tag=TOGGLE_ADVANCED_TAG, show=True)
        dpg.add_button(label="More Options", callback=toggle_options, tag=TOGGLE_OPTIONS_TAG)
        with dpg.group(horizontal=False, tag=EDITOR_OPTIONS_TAG, show=False):
          # dpg.add_separator()
          dpg.add_checkbox(label="Autosave on switch / exit", callback=lambda s, a: set_config(AUTOSAVE, a), tag=config_tag(AUTOSAVE))
          # no easy way to get this to work with listpicker, so hidden by default
          dpg.add_checkbox(label="Don't warn about unsaved changes", callback=lambda s, a: set_config(NO_WARN_SWITCH, a), tag=config_tag(NO_WARN_SWITCH), show=False)
          dpg.add_checkbox(label="Don't warn about overwriting files", callback=lambda s, a: set_config(NO_WARN_OVERWRITE, a), tag=config_tag(NO_WARN_OVERWRITE))
          dpg.add_checkbox(label="Show hand sprite overlay", callback=toggle_hands, tag=config_tag(SHOW_HANDS))
          dpg.add_checkbox(label="Make backups when batch translating", callback=toggle_backups, tag=config_tag(MAKE_BACKUPS))
          dpg.add_checkbox(label="Export as .jtk2d instead of .json", callback=toggle_jtk2d, tag=config_tag(USE_JTK2D))
          dpg.add_checkbox(label="Autoscroll file sidebar", callback=lambda s, a: set_config(AUTOSCROLL, a), tag=config_tag(AUTOSCROLL))
          dpg.add_checkbox(label="Show Tooltips", callback=toggle_tooltips, tag=config_tag(TOOLTIPS))
          dpg.add_checkbox(label="High DPI Display (WIP)", callback=toggle_high_dpi, tag=config_tag(HIGH_DPI))
        dpg.add_input_text(hint="Click here or Ctrl+F to filter files", callback=filter_files, tag=FILE_SEARCH_BOX_TAG) # can't set size???
        # file_box = BetterListBox(items=[], width=300, height=wh-64, parent=filewidgetgroup, callback=set_current_file_from_picker_box)
        file_box = BetterListBox(items=[], parent=filewidgetgroup, callback=set_current_file_from_picker_box)

      # Set up the rest our widget
      with dpg.group(horizontal=False, tag="rightwidget"):

        with dpg.group(horizontal=True, tag="info bar"):
          # Set up our control box
          with dpg.group(horizontal=False, tag="controls"):
            for p in _attach_points:
              generate_controls(p)
            # dpg.add_text(f"")
            with dpg.group(horizontal=True, tag=f"animation controls"):
              dpg.add_text(f" Animation: ")
              dpg.add_button(label=DISABLED_STRING, callback=lambda: toggle_animation(), tag=ANIMATION_ENABLED_TAG)
              with dpg.tooltip(dpg.last_item(), tag=auto_tooltip()): dpg.add_text("Shortcut: Ctrl + A")
              colorize_button(ANIMATION_ENABLED_TAG, DISABLED_COLOR)
              dpg.add_button(label="-5", callback=lambda: change_animation_speed(-5), tag=FPS_DOWN2_TAG, show=False)
              dpg.add_button(label="-1", callback=lambda: change_animation_speed(-1), tag=FPS_DOWN1_TAG, show=False)
              dpg.add_text(f"{animation_speed} FPS", tag=ANIMATION_FPS_TAG, show=False)
              dpg.add_button(label="+1", callback=lambda: change_animation_speed(1), tag=FPS_UP1_TAG, show=False)
              dpg.add_button(label="+5", callback=lambda: change_animation_speed(5), tag=FPS_UP2_TAG, show=False)

          # Set up our config / import / export / copy buttons
          with dpg.group(horizontal=False, tag=ADVANCED_CONTROLS_TAG, show=False):
            dpg.add_text(f"Working Dir: ", tag=IMAGE_PATH_TAG)
            dpg.add_text(f"Image Name:  ", tag=IMAGE_NAME_TAG)
            dpg.add_text(f"Image Size:  0 x 0 pixels", tag=IMAGE_SIZE_TAG)
            # Save button
            with dpg.group(horizontal=True):
              dpg.add_text("Ctrl+S", color=SHORTCUT_COLOR)
              # with modal
              dpg.add_button(label="Save Changes", callback=export_callback, tag=EXPORT_BUTTON_TAG, show=False)
              colorize_button(EXPORT_BUTTON_TAG, (0,128,128,255))
              # without modal
              dpg.add_button(label="Save Changes", callback=export_callback, tag=EXPORT_BUTTON_NP_TAG, show=False)
              colorize_button(EXPORT_BUTTON_NP_TAG, (0,128,128,255))
              dpg.add_button(label="No Changes To Save", callback=export_callback, tag=NO_EXPORT_BUTTON_TAG, show=False)
            # Revert button
            with dpg.group(horizontal=True):
              dpg.add_text("Ctrl+Z", color=SHORTCUT_COLOR)
              dpg.add_button(label="Revert Changes", callback=revert_callback, tag=REVERT_BUTTON_TAG, show=False)
              colorize_button(REVERT_BUTTON_TAG, (128,64,64,255))
              dpg.add_button(label="No Changes To Revert", callback=revert_callback, tag=NO_REVERT_BUTTON_TAG, show=False)
            # Copy Button
            with dpg.group(horizontal=True):
              dpg.add_text("Ctrl+C", color=SHORTCUT_COLOR)
              dpg.add_button(label="Copy Gun Data", callback=copy_state, tag="copy button")
            # Paste Button
            with dpg.group(horizontal=True, tag="paste box"):
              dpg.add_text("Ctrl+V", color=SHORTCUT_COLOR)
              dpg.add_button(label="Paste Gun Data", callback=paste_state, tag="paste button")
              dpg.add_text("", tag=PASTE_FILENAME_TAG)
            # Translate Button
            with dpg.group(horizontal=True, tag="translate box"):
              dpg.add_text("Ctrl+T", color=SHORTCUT_COLOR)
              dpg.add_button(label="Translate Gun Data", callback=show_translate_modal, tag="translate button")

        # Set up the main drawing list
        with dpg.drawlist(width=1, height=1, tag=DRAWLIST_TAG):
          pass # deferred until load_gun_image()

        # Set up a click handler for our drawing list
        with dpg.item_handler_registry(tag=DRAWLIST_CLICK_HANDLER_TAG):
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left, callback=on_plot_clicked)
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right, callback=on_plot_right_clicked)
        dpg.bind_item_handler_registry(DRAWLIST_TAG, DRAWLIST_CLICK_HANDLER_TAG)

  # Set up a global mouse handler
  with dpg.handler_registry(tag="global mouse handler"):
    m_drag = dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Left, callback=on_mouse_dragged)
    m_drag = dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Right, callback=on_right_mouse_dragged)

  # Set up some global keyboard shortcuts
  with dpg.handler_registry(tag="global keyboard handler"):
    # Ctrl + C = copy gun data
    dpg.add_key_press_handler(key=dpg.mvKey_C, callback=lambda: no_modal_open() and control_pressed() and copy_state())
    # Ctrl + V = paste gun data
    dpg.add_key_press_handler(key=dpg.mvKey_V, callback=lambda: no_modal_open() and control_pressed() and paste_state())
    # Ctrl + O = open gun data
    dpg.add_key_press_handler(key=dpg.mvKey_O, callback=lambda: no_modal_open() and control_pressed() and open_import_dialog())
    # Ctrl + F = focus file filter box
    dpg.add_key_press_handler(key=dpg.mvKey_F, callback=lambda: no_modal_open() and control_pressed() and dpg.focus_item(FILE_SEARCH_BOX_TAG))
    # Ctrl + S = save active gun changes
    dpg.add_key_press_handler(key=dpg.mvKey_S, callback=lambda: no_modal_open() and control_pressed() and save_changes_from_shortcut())
    # Ctrl + Z = revert active gun changes
    dpg.add_key_press_handler(key=dpg.mvKey_Z, callback=lambda: no_modal_open() and control_pressed() and revert_callback())
    # Ctrl + T = show attach point translate modal
    dpg.add_key_press_handler(key=dpg.mvKey_T, callback=lambda: no_modal_open() and control_pressed() and show_translate_modal())
    # Ctrl + A = toggle animation
    dpg.add_key_press_handler(key=dpg.mvKey_A, callback=lambda: no_modal_open() and control_pressed() and toggle_animation())
    # Ctrl + Down = next file in picker
    dpg.add_key_press_handler(key=dpg.mvKey_Down, callback=lambda: no_modal_open() and control_pressed() and next_file(1))
    # Ctrl + Up = previous file in picker
    dpg.add_key_press_handler(key=dpg.mvKey_Up, callback=lambda: no_modal_open() and control_pressed() and next_file(-1))
    # F5 = refresh file list
    dpg.add_key_press_handler(key=dpg.mvKey_F5, callback=lambda: no_modal_open() and refresh_file_list())
    # 1-4 = toggle attach points
    dpg.add_key_press_handler(key=dpg.mvKey_1, callback=lambda: no_modal_open() and control_pressed() and toggle_attach_point(_attach_points[0]))
    dpg.add_key_press_handler(key=dpg.mvKey_2, callback=lambda: no_modal_open() and control_pressed() and toggle_attach_point(_attach_points[1]))
    dpg.add_key_press_handler(key=dpg.mvKey_3, callback=lambda: no_modal_open() and control_pressed() and toggle_attach_point(_attach_points[2]))
    dpg.add_key_press_handler(key=dpg.mvKey_4, callback=lambda: no_modal_open() and control_pressed() and toggle_attach_point(_attach_points[3]))

  # Load our initial file either from the command line, our config, or a file picker
  load_config()
  resize_gui()
  last_file = None
  if filename is None:
    filename = get_config(LAST_FILE) or None
    if (filename is None) or (not os.path.exists(filename)):
      filename = None
  if filename is not None:
    load_gun_image(filename)
    if os.path.exists(jf := filename.replace(EXT_PNG, pref_ext())):
      load_json_from_file(jf)
      last_file = jf
    elif os.path.exists(jf := filename.replace(EXT_PNG, alt_ext())):
      load_json_from_file(jf)
      last_file = jf
  else:
    open_import_dialog()

  # Perform some final setup
  clear_unsaved_changes()

  # Show the app
  dpg.show_viewport()
  # dpg.start_dearpygui()

  # Render a single frame and scroll to our last opened file
  if dpg.is_dearpygui_running():
      dpg.render_dearpygui_frame()
      if last_file is not None:
        file_box.scroll_to_specific_item(last_file)

  # below replaces, start_dearpygui()
  frametime = 0
  while dpg.is_dearpygui_running():
      # Animate if necessary
      if animation_on:
        frametime += dpg.get_delta_time()
        frame_speed = 1.0 / animation_speed
        if (frametime > frame_speed):
          frametime %= frame_speed
          file_box.advance_frame()

      dpg.render_dearpygui_frame()

  # Before we exit, export our current image if we have unsaved changes and autosave is on
  if dpg.does_item_exist(SAVE_MODAL_TAG) and get_config(AUTOSAVE):
    export_callback()

  # Finish up
  dpg.destroy_context()

def maindemo():
  dpg.create_context()
  dpg.create_viewport(title='Custom Title', width=1200, height=800)
  dpg.setup_dearpygui()

  import dearpygui.demo as demo
  demo.show_demo()

  dpg.show_viewport()
  dpg.start_dearpygui()
  dpg.destroy_context()

if __name__ == "__main__":
  # maindemo()
  main(None if len(sys.argv) == 1 else sys.argv[1])
