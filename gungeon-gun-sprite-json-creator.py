#!/usr/bin/python
#Gungeon JSON visualizer and creator

#  Manually install missing packages with:
#    pip install --user --break-system-packages dearpygui numpy pillow

import os, sys, subprocess, shlex, json, array, importlib
from collections import namedtuple

# Install missing packages as necessary
try:
  import dearpygui.dearpygui as dpg
  import numpy as np
  from PIL import Image
except:
  def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
  try:
    for package in ["dearpygui", "numpy", "pillow"]:
      install_package(package)
    import dearpygui.dearpygui as dpg
    import numpy as np
    from PIL import Image
  except:
    print("failed to install dearpygui, numpy, and/or pillow")
    sys.exit(2)

PROGRAM_NAME      = "gungeon-json-editor"
TEST_IMAGE_2      = "/home/pretzel/uploads/omitb-gun-sprites-jsons/alphabeam_idle_003.png"
PREVIEW_SCALE     = 8 # magnification factor for preview
PIXELS_PER_TILE   = 16.0 # Unity / Gungeon scaling factor for sprites

ENABLED_STRING    = " Enabled" #note the space
DISABLED_STRING   = "Disabled"
ENABLED_COLOR     = (64, 128, 64, 255)
DISABLED_COLOR    = (64, 0, 0, 255)
SHORTCUT_COLOR    = (192, 255, 255, 255)
BLACK             = (0, 0, 0, 255)
THIN_WHITE        = (255, 255, 255, 64)
DRAWLIST_PAD      = 64
DRAW_INNER_BORDER = False

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

#Config globals
jconf = {
  "no_warn_overwrite" : False,
  "no_warn_switch"    : False,
  "autosave"          : False,
  "last_file"         : None,
}

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
  load_new_image(fullpath)
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

def move_hand_preview(x, y, p=None):
  global _attach_point_coords

  # Get the active attach point from the environment if not specified
  if p is None:
    p = _active_attach_point
  if dpg.get_item_label(f"{p.tag_base} enabled") == DISABLED_STRING:
    # print(f"{p.tag_base} is disabled")
    return # return if our element is disabled

  # Round x and y values as necessary to snap to the grid
  x = max(DRAWLIST_PAD, min(DRAWLIST_PAD + orig_width * PREVIEW_SCALE, round(x / PREVIEW_SCALE) * PREVIEW_SCALE))
  y = max(DRAWLIST_PAD, min(DRAWLIST_PAD + orig_height * PREVIEW_SCALE, round(y / PREVIEW_SCALE) * PREVIEW_SCALE))

  # Set the global coordinates (TODO: maybe don't use globals here)
  _attach_point_coords[p.name] = (x,y)
  # Get the real coordinates of the hand wrt what the JSON expects
  realx, realy = toJsonCoordinates(*_attach_point_coords[p.name])
  # ...and update the boxes
  dpg.set_value(f"{p.tag_base} x box", realx)
  dpg.set_value(f"{p.tag_base} y box", realy)

  # Delete and redraw the hand drawing layer
  layer = f"{p.tag_base} layer"
  if dpg.does_alias_exist(layer):
    dpg.delete_item(layer)
  dpg.push_container_stack("drawlist")
  dpg.add_draw_layer(tag=layer)
  dpg.pop_container_stack()

  # Redraw the hand at the designated position
  dpg.push_container_stack(layer)
  dpg.draw_circle(center=_attach_point_coords[p.name], radius=8, color=BLACK, fill=p.color, tag=f"{p.tag_base} circle")
  dpg.pop_container_stack()


def on_plot_clicked(sender, app_data):
  if dpg.is_key_down(dpg.mvKey_Shift):
    p=_attach_point_dict["      Clip"]
  else:
    p=_attach_point_dict[" Main Hand"]
  move_hand_preview(*dpg.get_drawing_mouse_pos(), p=p)
  # Mark our unsaved changes state
  mark_unsaved_changes()

def on_plot_right_clicked(sender, app_data):
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

def load_new_image(filename):
  global orig_width, orig_height, current_file, current_dir

  # Export our current image if we have unsaved changes and autosave is on
  if unsaved_changes and get_config("autosave"):
    export_callback()

  # Load and resize the image internally since pygui doesn't seem to support nearest neighbor scaling
  pil_image = Image.open(filename)
  orig_width, orig_height = pil_image.size
  scaled_width, scaled_height = PREVIEW_SCALE * orig_width, PREVIEW_SCALE * orig_height
  scaled_image = pil_image.resize((scaled_width, scaled_height), resample=Image.Resampling.NEAREST)
  dpg_image = np.frombuffer(scaled_image.tobytes(), dtype=np.uint8) / 255.0
  with dpg.texture_registry():
    image_tag = "image_id"
    if dpg.does_alias_exist(image_tag):
      dpg.remove_alias(image_tag)
      dpg.delete_item(image_tag)
    dpg.add_static_texture(width=scaled_width, height=scaled_height, default_value=dpg_image, tag=image_tag)

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
    dpg.draw_image("image_id", (DRAWLIST_PAD,DRAWLIST_PAD), (DRAWLIST_PAD+scaled_width, DRAWLIST_PAD+scaled_height))
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
    dpg.configure_item("file picker box", items=filelist, default_value=current_file.replace(".png",""))

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

  load_new_image(f"{stem}.png")
  if os.path.exists(f"{stem}.json"):
    load_json_from_file(f"{stem}.json")

def set_current_file_from_picker_box(sender, app_data):
  fullpath = os.path.join(current_dir, app_data)
  if os.path.exists(f"{fullpath}.png"):
    load_new_image(f"{fullpath}.png")
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
  if current_search in query:
    base_list = filtered_file_list # slight optimization for not looking through whole file list
  else:
    base_list = dir_file_list
  filtered_file_list = [f for f in base_list if query in f]
  update_file_list(filtered_file_list)
  current_search = query

def save_changes_from_shortcut():
  if jconf["no_warn_overwrite"]:
    export_callback()
  else:
    print("checking...")
    if dpg.does_item_exist("save modal"):
      # print("found modal")
      dpg.configure_item("save modal", show=True)

def main(filename):
  if (filename is not None) and (not os.path.exists(filename)):
    print(f"{filename} doesn't exist!")
    return

  global orig_width, orig_height
  dpg.create_context()
  dpg.create_viewport(title='Enter the Gungeon - Gun JSON editor', x_pos=100, y_pos=100, width=1720, height=880, resizable=False)
  dpg.setup_dearpygui()

  # Set up the main window
  with dpg.window(label="Files List", tag="mainwindow", width=1720, height=880, no_resize=True, autosize=False, no_close=True, no_collapse=True, no_title_bar=True, no_move=True):
    with dpg.group(horizontal=True, tag="topwidget"):
      # Set up our file picker box
      with dpg.group(horizontal=False, width=300, height=880, tag="filewidget", tracked=True):
        dpg.add_input_text(width=256, hint="Click here or Ctrl+F to filter files", callback=filter_files, tag="file search box")
        dpg.add_listbox([], tag="file picker box", num_items=49, tracked=True, callback=set_current_file_from_picker_box)
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

            dpg.add_separator()

            # Set up our config / import / export / copy buttons
            with dpg.group(horizontal=False, tag="file controls"):
              dpg.add_separator()
              dpg.add_checkbox(label="Autosave on switch / exit", callback=lambda s, a: set_config("autosave", a), tag="config autosave")
              # no easy way to get this to work with listpicker, so hidden by default
              dpg.add_checkbox(label="Don't warn about unsaved changes", callback=lambda s, a: set_config("no_warn_switch", a), tag="config no_warn_switch", show=False)
              dpg.add_checkbox(label="Don't warn about overwriting files", callback=lambda s, a: set_config("no_warn_overwrite", a), tag="config no_warn_overwrite")
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

        # Set up the main drawing list
        with dpg.drawlist(width=1, height=1, tag="drawlist"):
          pass # deferred until load_new_image()

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
    dpg.add_key_press_handler(key=dpg.mvKey_C, callback=lambda: dpg.is_key_down(dpg.mvKey_Control) and copy_state())
    # Ctrl + V = paste gun data
    dpg.add_key_press_handler(key=dpg.mvKey_V, callback=lambda: dpg.is_key_down(dpg.mvKey_Control) and paste_state())
    # Ctrl + O = open gun data
    dpg.add_key_press_handler(key=dpg.mvKey_O, callback=lambda: dpg.is_key_down(dpg.mvKey_Control) and open_import_dialog())
    # Ctrl + F = focus file filter box
    dpg.add_key_press_handler(key=dpg.mvKey_F, callback=lambda: dpg.is_key_down(dpg.mvKey_Control) and dpg.focus_item("file search box"))
    # Ctrl + S = save active gun changes
    dpg.add_key_press_handler(key=dpg.mvKey_S, callback=lambda: dpg.is_key_down(dpg.mvKey_Control) and save_changes_from_shortcut())
    # Ctrl + Z = revert active gun changes
    dpg.add_key_press_handler(key=dpg.mvKey_Z, callback=lambda: dpg.is_key_down(dpg.mvKey_Control) and revert_callback())

  # Load our initial file either from the command line, our config, or a file picker
  load_config()
  if filename is None:
    filename = get_config("last_file") or None
  if filename is not None:
    load_new_image(filename)
    if os.path.exists(jf := filename.replace(".png",".json")):
      load_json_from_file(jf)
  else:
    open_import_dialog()

  # Perform some final setup
  clear_unsaved_changes()

  # Show the app
  dpg.show_viewport()
  dpg.start_dearpygui()

  # Before we exit, export our current image if we have unsaved changes and autosave is on
  if dpg.does_item_exist("save modal") and get_config("autosave"):
    export_callback()

  # Finish up
  dpg.destroy_context()

def maindemo():
  dpg.create_context()
  dpg.create_viewport(title='Custom Title', width=1200, height=800)
  dpg.setup_dearpygui()

  demo.show_demo()

  dpg.show_viewport()
  dpg.start_dearpygui()
  dpg.destroy_context()

if __name__ == "__main__":
  # maindemo()
  main(None if len(sys.argv) == 1 else sys.argv[1])