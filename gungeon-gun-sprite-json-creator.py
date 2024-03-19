#!/usr/bin/python3.11
#Gungeon JSON visualizer and creator

#  Manually install missing packages with:
#    pip install --user --break-system-packages dearpygui numpy pillow screeninfo

# Todo:
#   - figure out previewing indexed color images
#   - hand previews

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
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

PROGRAM_NAME      = "gungeon-json-editor"
TEST_IMAGE_2      = "/home/pretzel/uploads/omitb-gun-sprites-jsons/alphabeam_idle_003.png"
PREVIEW_SCALE     = 8 # magnification factor for preview
PIXELS_PER_TILE   = 16.0 # Unity / Gungeon scaling factor for sprites

ENABLED_STRING    = " Enabled" #note the space
DISABLED_STRING   = "Disabled"
FILE_PICKER_TAG   = "file picker box"
PREVIEW_IMAGE_TAG = "preview_image"
HAND_IMAGE_TAG    = "hand_image"
HAND_IMAGE_PATH   = resource_path("hand_main.png")
OFF_IMAGE_TAG     = "hand_off"
OFF_IMAGE_PATH    = resource_path("hand_off.png")
ENABLED_COLOR     = (64, 128, 64, 255)
DISABLED_COLOR    = (64, 0, 0, 255)
SHORTCUT_COLOR    = (192, 255, 255, 255)
BLACK             = (0, 0, 0, 255)
THIN_WHITE        = (255, 255, 255, 64)
DRAWLIST_PAD      = 64
WINDOW_PAD        = 100
DRAW_INNER_BORDER = False
LIST_ITEM_HEIGHT  = 18 # estimated through experimentation

CachedImage = namedtuple('CachedImage', ['name', 'data', 'width', 'height'])
AttachPoint = namedtuple('AttachPoint', ['name', 'tag_base', 'internal_name', 'color', 'shortcut', 'enabled_default'])
_attach_points = [
  AttachPoint(" Main Hand","main hand", "PrimaryHand",   (255, 255,   0, 255), "Left Click",          ENABLED_STRING ),
  AttachPoint("  Off Hand","off hand",  "SecondaryHand", (255,   0, 255, 255), "Right Click",         DISABLED_STRING),
  AttachPoint("      Clip","clip",      "Clip",          (128, 255, 255, 255), "Shift + Left Click",  DISABLED_STRING),
  AttachPoint("    Casing","casing",    "Casing",        (  0, 255,   0, 255), "Shift + Right Click", ENABLED_STRING),
]
_attach_point_dict   = { p.name : p for p in _attach_points}
_attach_point_coords = { p.name : (0,0) for p in _attach_points}
_active_attach_point = _attach_points[0]

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

#Config globals
jconf = {
  "no_warn_overwrite" : False,
  "no_warn_switch"    : False,
  "autosave"          : False,
  "show_hands"        : True,
  "make_backups"      : True,
  "last_file"         : None,
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

    cur_index             = 0

    def __init__(self, items: list, width: int = 250, height: int = 70, parent: int | str = None, callback: callable = None):
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
        with dpg.child_window(autosize_y=False, height=100, width=self.width, border=False, parent=self.parent) as self.custom_listbox:
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
          show = (dpg.get_item_label(item).startswith(query))
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
        dpg.set_y_scroll(self.custom_listbox, max(0,dpg.get_item_state(sender)["pos"][1] - self.height / 2))

    def scroll_to_specific_item(self, itemname):
        truename = os.path.basename(itemname).replace(".json","")
        for item in self.items:
          if dpg.get_item_label(item) == truename:
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
      cur_root = self.get_animation_root(dpg.get_item_label(self.items[self.cur_index]))
      # Figure out the name of our current animation if necessary
      if self.root != cur_root:
        self.root = cur_root
        self.frames = []
        self.cur_frame = 0
        for i,item in enumerate(self.items):
          if self.get_animation_root(dpg.get_item_label(item)) == cur_root:
            self.frames.append(i)

      self.cur_frame = (self.cur_frame + 1) % len(self.frames)
      self.scroll_and_invoke_callback(self.items[self.frames[self.cur_frame]])

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
    return

  with open(config_path, 'r') as fin:
    jconf = json.load(fin)

  for k, v in jconf.items():
    if dpg.does_item_exist(f"config {k}"):
      dpg.set_value(f"config {k}", v)

def get_config(key):
  return jconf.get(key,False)

def set_config(key, value):
  jconf[key] = value
  with open(get_config_path(), 'w') as fout:
    fout.write(json.dumps(jconf,indent=2))
  if unsaved_changes: # change the export button to the noprompt version if necessary
    mark_unsaved_changes()

def mark_unsaved_changes():
  global unsaved_changes
  unsaved_changes = True
  enable_save_modal()
  if get_config("no_warn_overwrite"):
    dpg.configure_item("export button noprompt", show=True)
    dpg.configure_item("export button", show=False)
  else:
    dpg.configure_item("export button noprompt", show=False)
    dpg.configure_item("export button", show=True)
  dpg.configure_item("revert button", show=True)
  dpg.configure_item("no export button", show=False)
  dpg.configure_item("no revert button", show=False)

def clear_unsaved_changes():
  global unsaved_changes
  unsaved_changes = False
  disable_save_modal()
  dpg.configure_item("export button", show=False)
  dpg.configure_item("export button noprompt", show=False)
  dpg.configure_item("revert button", show=False)
  dpg.configure_item("no export button", show=True)
  dpg.configure_item("no revert button", show=True)

def enable_save_modal():
  if dpg.does_item_exist("save modal"):
    return # no need to enable a modal that's already enabled

  export_path = os.path.join(current_dir,current_file).replace(".png",".json")
  if not os.path.exists(export_path):
    return # no need for a modal if we're saving to a new file

  with dpg.popup("export button", modal=True, mousebutton=dpg.mvMouseButton_Left, no_move=True, tag="save modal"):
    dpg.add_text(f"Overwite existing file?\n  {export_path}")
    dpg.add_separator()
    with dpg.group(horizontal=True):
      dpg.add_button(label="Yes", width=75, callback=lambda: export_callback())
      dpg.add_button(label="No", width=75, callback=lambda: dpg.configure_item("save modal", show=False))

def disable_save_modal():
  if dpg.does_item_exist("save modal"):
    dpg.delete_item("save modal")

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
  dpg.set_value("paste filename", f"from {current_file}")

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
        "name"     : "PrimaryHand",
        "position" : {
          "x" : 0.4375,
          "y" : 0.4375,
          "z" : 0.0
        },
        "angle": 0.0
      },
      {
        "name"    : "Casing",
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

def get_json_for_current_gun():
  basejson = get_basic_gun_json(orig_width, orig_height)
  for p in _attach_points:
    if dpg.get_item_label(f"{p.tag_base} enabled") == ENABLED_STRING:
      add_positional_element(basejson, p.internal_name, dpg.get_value(f"{p.tag_base} x box"), dpg.get_value(f"{p.tag_base} y box"))
  return basejson

def export_callback():
  global unsaved_changes
  if not unsaved_changes:
    return # no changes since last export

  export_path = os.path.join(current_dir,current_file).replace(".png",".json")
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
  jsonpath = fullpath.replace(".png",".json")
  if os.path.exists(jsonpath):
    load_json_from_file(jsonpath)

def pos_in_drawing_area(x, y):
  dx, dy = dpg.get_item_rect_min("drawlist")
  dy -= DRAWLIST_PAD / 2 #TODO: not really sure why the rectangle above is offset...
  dw, dh = dpg.get_item_rect_size("drawlist")

  # print(f"checking {x},{y} within {dx,dy}...{dx+dw},{dy+dh}")
  return x >= dx and x <= (dx+dw) and y >= dy and y <= (dy+dh)

def fromJsonCoordinates(x,y):
  canvas_height = PREVIEW_SCALE * float(orig_height)
  canvasx = DRAWLIST_PAD + (x * (PREVIEW_SCALE * PIXELS_PER_TILE))
  canvasy = DRAWLIST_PAD + canvas_height - (y * (PREVIEW_SCALE * PIXELS_PER_TILE)) # we have an inverted y axis
  return canvasx, canvasy

def toJsonCoordinates(x,y):
  canvas_height = PREVIEW_SCALE * float(orig_height)
  jsonx = (x - DRAWLIST_PAD) / (PREVIEW_SCALE * PIXELS_PER_TILE)
  jsony = (canvas_height - (y - DRAWLIST_PAD)) / (PREVIEW_SCALE * PIXELS_PER_TILE) # we have an inverted y axis
  return jsonx, jsony

def redraw_attach_point(p):
  # Verify we're actually enabled
  if not attach_point_enabled(p):
    return

  # Delete and redraw the hand drawing layer
  layer = f"{p.tag_base} layer"
  if dpg.does_alias_exist(layer):
    dpg.delete_item(layer)
  dpg.push_container_stack("drawlist")
  dpg.add_draw_layer(tag=layer)
  dpg.pop_container_stack()

  # Redraw the hand at the designated position
  dpg.push_container_stack(layer)
  center = _attach_point_coords[p.name]
  if get_config("show_hands") and ("hand" in p.tag_base):
    # offset = center+PREVIEW_SCALE*(DRAWLIST_PAD,DRAWLIST_PAD)
    offset = (center[0] - 2*PREVIEW_SCALE, center[1] - 2*PREVIEW_SCALE)
    # dpg.draw_image(HAND_IMAGE_TAG, center=_attach_point_coords[p.name], tag=f"{p.tag_base} hand")
    # dpg.draw_image(HAND_IMAGE_TAG, offset, offset + (4*PREVIEW_SCALE, 4*PREVIEW_SCALE), tag=f"{p.tag_base} circle")
    dpg.draw_image(HAND_IMAGE_PATH if "main" in p.tag_base else OFF_IMAGE_PATH, offset, (offset[0] + 4*PREVIEW_SCALE, offset[1] + 4*PREVIEW_SCALE), tag=f"{p.tag_base} circle")
  else:
    dpg.draw_circle(center=center, radius=PREVIEW_SCALE, color=BLACK, fill=p.color, tag=f"{p.tag_base} circle")
  dpg.pop_container_stack()

def attach_point_enabled(p):
  return dpg.get_item_label(f"{p.tag_base} enabled") != DISABLED_STRING

def move_hand_preview(x, y, p=None):
  global _attach_point_coords

  # Get the active attach point from the environment if not specified
  if p is None:
    p = _active_attach_point
  if not attach_point_enabled(p):
    # print(f"{p.tag_base} is disabled")
    return # return if our element is disabled

  # Round x and y values as necessary to snap to the grid
  # x = max(DRAWLIST_PAD, min(DRAWLIST_PAD + orig_width * PREVIEW_SCALE, round(x / PREVIEW_SCALE) * PREVIEW_SCALE))
  # y = max(DRAWLIST_PAD, min(DRAWLIST_PAD + orig_height * PREVIEW_SCALE, round(y / PREVIEW_SCALE) * PREVIEW_SCALE))
  x = round(x / PREVIEW_SCALE) * PREVIEW_SCALE #NOTE: need to allow these to go offscreen for batch translating purposes
  y = round(y / PREVIEW_SCALE) * PREVIEW_SCALE #NOTE: need to allow these to go offscreen for batch translating purposes

  # Set the global coordinates (TODO: maybe don't use globals here)
  _attach_point_coords[p.name] = (x,y)
  # Get the real coordinates of the hand wrt what the JSON expects
  realx, realy = toJsonCoordinates(*_attach_point_coords[p.name])
  # ...and update the boxes
  dpg.set_value(f"{p.tag_base} x box", realx)
  dpg.set_value(f"{p.tag_base} y box", realy)

  # Redraw the attach point
  redraw_attach_point(p)

def on_plot_clicked(sender, app_data):
  toggle_animation(False)
  if dpg.is_key_down(dpg.mvKey_Shift):
    p=_attach_point_dict["      Clip"]
  else:
    p=_attach_point_dict[" Main Hand"]
  move_hand_preview(*dpg.get_drawing_mouse_pos(), p=p)
  # Mark our unsaved changes state
  mark_unsaved_changes()

def on_plot_right_clicked(sender, app_data):
  toggle_animation(False)
  if dpg.is_key_down(dpg.mvKey_Shift):
    p=_attach_point_dict["    Casing"]
  else:
    p=_attach_point_dict["  Off Hand"]
  move_hand_preview(*dpg.get_drawing_mouse_pos(), p=p)
  # Mark our unsaved changes state
  if dpg.get_item_label(f"{p.tag_base} enabled") != DISABLED_STRING:
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

def toggle_element(element, override=None):
  cur_enabled = dpg.get_item_label(f"{element} enabled") == ENABLED_STRING
  new_enabled = (not cur_enabled) if override is None else override
  dpg.configure_item(f"{element} x box", show=new_enabled)
  dpg.configure_item(f"{element} y box", show=new_enabled)
  dpg.configure_item(f"{element} shortcut box", show=new_enabled)
  dpg.set_item_label(f"{element} enabled", ENABLED_STRING if new_enabled else DISABLED_STRING)
  colorize_button(f"{element} enabled", ENABLED_COLOR if new_enabled else DISABLED_COLOR)

  layer = f"{element} layer"
  if dpg.does_alias_exist(layer):
    dpg.configure_item(layer, show=new_enabled)
  mark_unsaved_changes()

def toggle_animation(override=None):
  global animation_on
  cur_enabled = dpg.get_item_label(f"animation enabled") == ENABLED_STRING
  new_enabled = (not cur_enabled) if override is None else override
  animation_on = new_enabled
  dpg.set_item_label(f"animation enabled", ENABLED_STRING if new_enabled else DISABLED_STRING)
  colorize_button(f"animation enabled", ENABLED_COLOR if new_enabled else DISABLED_COLOR)

def generate_controls(p):
  name = p.name
  tag_base = p.tag_base
  label = p.enabled_default
  with dpg.group(horizontal=True, tag=f"{tag_base} controls"):
    dpg.add_text(f"{name}: ",color=p.color)
    dpg.add_button(label=label, callback=lambda: toggle_element(f"{tag_base}"), tag=f"{tag_base} enabled")
    colorize_button(f"{tag_base} enabled", ENABLED_COLOR if label==ENABLED_STRING else DISABLED_COLOR)
    dpg.add_input_text(label="x", width=70, readonly=True, show=label==ENABLED_STRING, tag=f"{tag_base} x box", default_value="0.0000")
    dpg.add_input_text(label="y", width=70, readonly=True, show=label==ENABLED_STRING, tag=f"{tag_base} y box", default_value="0.0000")
    dpg.add_text(f"{p.shortcut}", color=p.color, tag=f"{tag_base} shortcut box")

image_cache = {}
def load_scaled_image(filename):
  if (filename in image_cache):
    # print(f"using cached {filename}")
    (dpg_image, orig_width, orig_height) = image_cache[filename]
    scaled_width, scaled_height = PREVIEW_SCALE * orig_width, PREVIEW_SCALE * orig_height
  else:
    pil_image = Image.open(filename)
    if pil_image.mode != "RGBA":
      pil_image = pil_image.convert(mode='RGBA')
    orig_width, orig_height = pil_image.size
    scaled_width, scaled_height = PREVIEW_SCALE * orig_width, PREVIEW_SCALE * orig_height
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

def load_gun_image(filename):
  global orig_width, orig_height, current_file, current_dir

  # Export our current image if we have unsaved changes and autosave is on
  if unsaved_changes and get_config("autosave"):
    export_callback()

  # Load and resize the image internally since pygui doesn't seem to support nearest neighbor scaling
  pil_image, orig_width, orig_height = load_scaled_image(filename)
  scaled_width, scaled_height = PREVIEW_SCALE * orig_width, PREVIEW_SCALE * orig_height

  # Set our current file as appropriate
  old_dir      = current_dir
  current_dir  = os.path.dirname(filename)
  changed_dir  = current_dir != old_dir
  current_file = os.path.basename(filename)

  # Refresh all of our canvas and metadata data
  dpg.set_value(f"image path", f"Working Dir: {current_dir}")
  dpg.set_value(f"image name", f"Image Name:  {current_file}")
  dpg.set_value(f"image size", f"Image Size:  {orig_width} x {orig_height} pixels")
  dpg.configure_item("drawlist", width=DRAWLIST_PAD*2+scaled_width, height=DRAWLIST_PAD*2+scaled_height)
  layer_tag = f"gun layer"
  if dpg.does_alias_exist(layer_tag):
    dpg.delete_item(layer_tag)
  dpg.push_container_stack("drawlist")
  with dpg.draw_layer(tag=layer_tag):
    #Draw outer border
    dpg.draw_rectangle((0,0), (DRAWLIST_PAD*2+scaled_width,DRAWLIST_PAD*2+scaled_height))
    #Draw inner border
    if DRAW_INNER_BORDER:
      dpg.draw_rectangle((DRAWLIST_PAD,DRAWLIST_PAD), (DRAWLIST_PAD+scaled_width,DRAWLIST_PAD+scaled_height),color=THIN_WHITE)
    #Draw sprite itself
    dpg.draw_image(filename, (DRAWLIST_PAD,DRAWLIST_PAD), (DRAWLIST_PAD+scaled_width, DRAWLIST_PAD+scaled_height))
  dpg.pop_container_stack()

  if changed_dir:
    global dir_file_list, filtered_file_list
    dir_file_list = sorted([f[:-4] for f in filter(lambda x: x.endswith(".png"), os.listdir(current_dir))])
    filtered_file_list = dir_file_list
    update_file_list(filtered_file_list)

  load_json_from_dict(get_default_gun_json(orig_width, orig_height))
  clear_unsaved_changes()
  set_config("last_file", filename)

def update_file_list(filelist):
    # dpg.configure_item(FILE_PICKER_TAG, items=filelist, default_value=current_file.replace(".png",""))
    file_box.replace_items(filelist)

def load_json_from_dict(jdata):
  # Temporarily disable all previews
  for p in _attach_points:
    toggle_element(p.tag_base, override=False)

  # Reenable previews for each defined attach point
  for a in jdata.get("attachPoints", []):
    if "position" not in a:
      continue

    for p in _attach_points:
      if a["name"] != p.internal_name:
        continue
      toggle_element(p.tag_base, override=True)
      px = a.get("position",{}).get("x", 0)
      py = a.get("position",{}).get("y", 0)
      cx, cy = fromJsonCoordinates(px,py)
      move_hand_preview(cx, cy, p)
      break

def load_json_from_file(filename):
  # Load the JSON data
  with open(filename, 'r') as fin:
    jdata = json.load(fin)
  load_json_from_dict(jdata)

def set_current_file_from_import_dialog(sender, app_data):
  dpg.configure_item("import dialog", show=False)

  for _, filename in app_data.get("selections",{}).items():
    stem = filename.replace(".json","").replace(".png","")
    break

  if not os.path.exists(f"{stem}.png"):
    return

  load_gun_image(f"{stem}.png")
  if os.path.exists(f"{stem}.json"):
    load_json_from_file(f"{stem}.json")
  file_box.scroll_to_specific_item(f"{stem}")

def set_current_file_from_picker_box(sender, file_stem):
  fullpath = os.path.join(current_dir, file_stem)
  if os.path.exists(f"{fullpath}.png"):
    load_gun_image(f"{fullpath}.png")
    if os.path.exists(f"{fullpath}.json"):
      load_json_from_file(f"{fullpath}.json")
    clear_unsaved_changes()

def open_import_dialog():
  if dpg.does_item_exist("import dialog"):
    if dpg.does_item_exist("import keyboard handler"):
      dpg.delete_item("import keyboard handler")
    dpg.delete_item("import dialog")
  with dpg.file_dialog(label="Edit Gun Data", width=700, height=400, modal=True, show=True, default_path=current_dir, callback=set_current_file_from_import_dialog, tag="import dialog"):
    dpg.add_file_extension("Gungeon Data files {.png,.json}", color=(0, 255, 255, 255))
    dpg.add_file_extension(".png", color=(255, 255, 0, 255))
    dpg.add_file_extension(".json", color=(255, 0, 255, 255))
    with dpg.handler_registry(tag="import keyboard handler"):
      dpg.add_key_release_handler(key=dpg.mvKey_Escape, callback=lambda: dpg.configure_item("import dialog", show=False))
      dpg.add_key_release_handler(key=dpg.mvKey_Return, callback=lambda: set_current_file_from_import_dialog(None, dpg.get_file_dialog_info("import dialog")))

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
  if jconf["no_warn_overwrite"]:
    export_callback()
  else:
    print("checking...")
    if dpg.does_item_exist("save modal"):
      # print("found modal")
      dpg.configure_item("save modal", show=True)
    else:
      export_callback()

def toggle_hands(switch, value):
  set_config("show_hands", value)
  am = _attach_point_dict[" Main Hand"]
  ao = _attach_point_dict["  Off Hand"]
  redraw_attach_point(am)
  redraw_attach_point(ao)
  # for p in _attach_points:
  #   toggle_element(p.tag_base, override=False)

def toggle_backups(switch, value):
  set_config("make_backups", value)

def next_file(delta):
  file_box.change_item(delta)

def change_animation_speed(delta):
  global animation_speed
  animation_speed += delta
  if (animation_speed < 1):
    animation_speed = 1
  elif (animation_speed > 60):
    animation_speed = 60
  dpg.set_value(f"animation fps", f"{animation_speed} FPS")

def show_translate_modal():
  toggle_animation(False)
  cur_json = os.path.join(current_dir,current_file.replace(".png",".json"))
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
      if jdata["attachPoints"][i]["name"] != "PrimaryHand":
        continue
      pos = jdata["attachPoints"][i]["position"]
      oldx = pos["x"]
      oldy = pos["y"]
      break
  if (oldx is None) or (oldy is None):
    return # failed to read necessary JSON data
  newx, newy = toJsonCoordinates(*_attach_point_coords[" Main Hand"])

  if dpg.does_item_exist("translate modal"):
    dpg.configure_item("translate modal", show=True)
    return # if the dialog is already created, just show it

  # get the base animation name and load all available jsons with the same name
  root_name = file_box.get_animation_root(current_file)
  jsons = []
  for i,item in enumerate(file_box.items):
    label = dpg.get_item_label(item)
    if file_box.get_animation_root(label) != root_name:
      continue
    jpath = os.path.join(current_dir,f"{label}.json")
    if not os.path.exists(jpath):
      continue
    jsons.append(jpath)

  # create a modal dialog for translating all attach points corresponding to a sprite by the specified amount
  with dpg.popup("export button", modal=True, mousebutton=dpg.mvMouseButton_Left, no_move=True, tag="translate modal"):
    dpg.add_text(f"Translating {len(jsons)} sprites matching:")
    dpg.add_text(f"{root_name}_###", color=(192,255,128))
    dpg.add_separator()
    # dpg.add_checkbox(label="Translate All Animations for This Gun", tag="translate all")
    dpg.add_checkbox(label="Make Backups", tag="translate backups", default_value=get_config("make_backups"))
    dpg.add_input_float(label=f"x: {int(16 * (newx - oldx))}px", width=150, tag=f"translate x box", format="%.04f", step=1.0/16.0, default_value=(newx - oldx),
      callback=lambda: dpg.configure_item("translate x box", label=f"""x: {int(16 * dpg.get_value("translate x box"))}px"""))
    dpg.add_input_float(label=f"y: {int(16 * (newy - oldy))}px", width=150, tag=f"translate y box", format="%.04f", step=1.0/16.0, default_value=(newy - oldy),
    callback=lambda: dpg.configure_item("translate y box", label=f"""y: {int(16 * dpg.get_value("translate y box"))}px"""))
    dpg.add_separator()
    dpg.add_text(f"TIP: you can prepopulate the fields above by moving the primary hand attach point in the editor")
    dpg.add_separator()
    with dpg.group(horizontal=True):
      dpg.add_button(label="Translate", width=75, callback=lambda: translate_jsons(jsons))
      dpg.add_button(label="Cancel", width=75, callback=lambda: hide_translate_modal())
    with dpg.handler_registry(tag="translate keyboard handler"):
      dpg.add_key_release_handler(key=dpg.mvKey_Escape, callback=lambda: hide_translate_modal())
  dpg.configure_item("translate modal", show=True)

def translate_jsons(jsons):
  # get necessary paramters
  xshift = dpg.get_value("translate x box")
  yshift = dpg.get_value("translate y box")
  backup = dpg.get_value("translate backups")

  # make backups as necessary
  if backup:
    bpath = os.path.join(current_dir,f"json_backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
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
  load_json_from_file(os.path.join(current_dir,current_file.replace(".png",".json")))

def hide_translate_modal():
  if dpg.does_item_exist("translate keyboard handler"):
    dpg.delete_item("translate keyboard handler")
  if dpg.does_item_exist("translate modal"):
    dpg.configure_item("translate modal", show=False)
    dpg.delete_item("translate modal")

def control_pressed():
  return dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)

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
  dpg.create_viewport(title='Enter the Gungeon - Gun JSON editor', x_pos=WINDOW_PAD, y_pos=WINDOW_PAD, width=ww, height=wh, resizable=False)
  dpg.setup_dearpygui()

  # Load necessary assets
  load_scaled_image(HAND_IMAGE_PATH)
  load_scaled_image(OFF_IMAGE_PATH)

  # Set up the main window
  with dpg.window(label="Files List", tag="mainwindow", width=ww, height=wh, no_resize=True, autosize=False, no_close=True, no_collapse=True, no_title_bar=True, no_move=True):
    with dpg.group(horizontal=True, tag="topwidget"):
      # Set up our file picker box
      # with dpg.group(horizontal=False, width=300, height=wh, tag="filewidget", tracked=True):
      with dpg.group(horizontal=False, width=300, height=wh - 40, tag="filewidget") as filewidgetgroup:
        dpg.add_input_text(width=256, hint="Click here or Ctrl+F to filter files", callback=filter_files, tag="file search box")
        # dpg.add_listbox([], tag=FILE_PICKER_TAG, num_items=wh / LIST_ITEM_HEIGHT, tracked=True, track_offset=0.5, callback=set_current_file_from_picker_box)
        # dpg.add_listbox([], tag=FILE_PICKER_TAG, num_items=wh / LIST_ITEM_HEIGHT, callback=set_current_file_from_picker_box)
        file_box = BetterListBox(items=[], parent=filewidgetgroup, height=wh, width=100, callback=set_current_file_from_picker_box)
        pass
      # Set up the rest our widget
      with dpg.group(horizontal=False, tag="rightwidget"):
        with dpg.group(horizontal=False, tag="main column"):
          with dpg.group(horizontal=True, tag="info bar"):
            # Set up our control box
            with dpg.group(horizontal=False, tag="controls"):
              dpg.add_text(f"Working Dir: ", tag="image path")
              dpg.add_text(f"Image Name:  ", tag="image name")
              dpg.add_text(f"Image Size:  0 x 0 pixels", tag="image size")
              for p in _attach_points:
                generate_controls(p)
              dpg.add_text(f"")
              with dpg.group(horizontal=True, tag=f"animation controls"):
                dpg.add_text(f" Animation: ")
                dpg.add_button(label=DISABLED_STRING, callback=lambda: toggle_animation(), tag=f"animation enabled")
                colorize_button(f"animation enabled", DISABLED_COLOR)
                dpg.add_button(label="-5", callback=lambda: change_animation_speed(-5), tag=f"fps --")
                dpg.add_button(label="-1", callback=lambda: change_animation_speed(-1), tag=f"fps -")
                dpg.add_text(f"{animation_speed} FPS", tag="animation fps")
                dpg.add_button(label="+1", callback=lambda: change_animation_speed(1), tag=f"fps +")
                dpg.add_button(label="+5", callback=lambda: change_animation_speed(5), tag=f"fps ++")
                # dpg.add_input_text(label="x", width=70, readonly=True, show=label==ENABLED_STRING, tag=f"{tag_base} x box", default_value="0.0000")
                # dpg.add_input_text(label="y", width=70, readonly=True, show=label==ENABLED_STRING, tag=f"{tag_base} y box", default_value="0.0000")
                dpg.add_text(f" Ctrl+A", color=SHORTCUT_COLOR, tag=f"animation shortcut box")

            # dpg.add_separator()

            # Set up our config / import / export / copy buttons
            with dpg.group(horizontal=False, tag="file controls"):
              # dpg.add_separator()
              dpg.add_checkbox(label="Autosave on switch / exit", callback=lambda s, a: set_config("autosave", a), tag="config autosave")
              # no easy way to get this to work with listpicker, so hidden by default
              dpg.add_checkbox(label="Don't warn about unsaved changes", callback=lambda s, a: set_config("no_warn_switch", a), tag="config no_warn_switch", show=False)
              dpg.add_checkbox(label="Don't warn about overwriting files", callback=lambda s, a: set_config("no_warn_overwrite", a), tag="config no_warn_overwrite")
              dpg.add_checkbox(label="Show hand sprite overlay", callback=toggle_hands, tag="config show_hands")
              dpg.add_checkbox(label="Make backups when batch translating", callback=toggle_backups, tag="config make_backups")
              # dpg.add_separator()

              # Import button
              with dpg.group(horizontal=True):
                dpg.add_text("Ctrl+O", color=SHORTCUT_COLOR)
                dpg.add_button(label="Import / Edit Gun Data", callback=open_import_dialog, tag="import button", show=True)
              # Save button
              with dpg.group(horizontal=True):
                dpg.add_text("Ctrl+S", color=SHORTCUT_COLOR)
                # with modal
                dpg.add_button(label="Save Changes", callback=export_callback, tag="export button", show=False)
                colorize_button("export button", (0,128,128,255))
                # without modal
                dpg.add_button(label="Save Changes", callback=export_callback, tag="export button noprompt", show=False)
                colorize_button("export button noprompt", (0,128,128,255))
                dpg.add_button(label="No Changes To Save", callback=export_callback, tag="no export button", show=False)
              # Revert button
              with dpg.group(horizontal=True):
                dpg.add_text("Ctrl+Z", color=SHORTCUT_COLOR)
                dpg.add_button(label="Revert Changes", callback=revert_callback, tag="revert button", show=False)
                colorize_button("revert button", (128,64,64,255))
                dpg.add_button(label="No Changes To Revert", callback=revert_callback, tag="no revert button", show=False)
              # Copy Button
              with dpg.group(horizontal=True):
                dpg.add_text("Ctrl+C", color=SHORTCUT_COLOR)
                dpg.add_button(label="Copy Gun Data", callback=copy_state, tag="copy button")
              # Paste Button
              with dpg.group(horizontal=True, tag="paste box"):
                dpg.add_text("Ctrl+V", color=SHORTCUT_COLOR)
                dpg.add_button(label="Paste Gun Data", callback=paste_state, tag="paste button")
                dpg.add_text("", tag="paste filename")
              # Translate Button
              with dpg.group(horizontal=True, tag="translate box"):
                dpg.add_text("Ctrl+T", color=SHORTCUT_COLOR)
                dpg.add_button(label="Translate Gun Data", callback=show_translate_modal, tag="translate button")
                # dpg.add_text("", tag="paste filename")

        # Set up the main drawing list
        with dpg.drawlist(width=1, height=1, tag="drawlist"):
          pass # deferred until load_gun_image()

        # Set up a click handler for our drawing list
        with dpg.item_handler_registry(tag="drawlist click handler"):
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left, callback=on_plot_clicked)
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right, callback=on_plot_right_clicked)
        dpg.bind_item_handler_registry("drawlist", "drawlist click handler")

  # Set up a global mouse handler
  with dpg.handler_registry(tag="global mouse handler"):
    m_drag = dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Left, callback=on_mouse_dragged)
    m_drag = dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Right, callback=on_right_mouse_dragged)

  # Set up some global keyboard shortcuts
  with dpg.handler_registry(tag="global keyboard handler"):
    # Ctrl + C = copy gun data
    dpg.add_key_press_handler(key=dpg.mvKey_C, callback=lambda: control_pressed() and copy_state())
    # Ctrl + V = paste gun data
    dpg.add_key_press_handler(key=dpg.mvKey_V, callback=lambda: control_pressed() and paste_state())
    # Ctrl + O = open gun data
    dpg.add_key_press_handler(key=dpg.mvKey_O, callback=lambda: control_pressed() and open_import_dialog())
    # Ctrl + F = focus file filter box
    dpg.add_key_press_handler(key=dpg.mvKey_F, callback=lambda: control_pressed() and dpg.focus_item("file search box"))
    # Ctrl + S = save active gun changes
    dpg.add_key_press_handler(key=dpg.mvKey_S, callback=lambda: control_pressed() and save_changes_from_shortcut())
    # Ctrl + Z = revert active gun changes
    dpg.add_key_press_handler(key=dpg.mvKey_Z, callback=lambda: control_pressed() and revert_callback())
    # Ctrl + T = show attach point translate modal
    dpg.add_key_press_handler(key=dpg.mvKey_T, callback=lambda: control_pressed() and show_translate_modal())
    # Ctrl + A = show attach point translate modal
    dpg.add_key_press_handler(key=dpg.mvKey_A, callback=lambda: control_pressed() and toggle_animation())
    # Ctrl + Down = next file in picker
    dpg.add_key_press_handler(key=dpg.mvKey_Down, callback=lambda: control_pressed() and next_file(1))
    # Ctrl + Up = previous file in picker
    dpg.add_key_press_handler(key=dpg.mvKey_Up, callback=lambda: control_pressed() and next_file(-1))

  # Load our initial file either from the command line, our config, or a file picker
  load_config()
  last_file = None
  if filename is None:
    filename = get_config("last_file") or None
    if (filename is None) or (not os.path.exists(filename)):
      filename = None
  if filename is not None:
    load_gun_image(filename)
    if os.path.exists(jf := filename.replace(".png",".json")):
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
  time = 0
  while dpg.is_dearpygui_running():
      # Animate if necessary
      if animation_on:
        time += dpg.get_delta_time()
        frame_speed = 1.0 / animation_speed
        if (time > frame_speed):
          time %= frame_speed
          file_box.advance_frame()

      dpg.render_dearpygui_frame()

  # Before we exit, export our current image if we have unsaved changes and autosave is on
  if dpg.does_item_exist("save modal") and get_config("autosave"):
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
