#!/usr/bin/python
#Maps Annotations

import sys, os, re

USED_NEVER  = 0
USED_SPRITE = 1
USED_ANIM   = 2

def findSprites(decomp_path):
  colSprites = {}
  for root, subdirs, files in os.walk(decomp_path):
    for f in files:
      fpath = os.path.join(root, f)
      if not fpath.endswith(".annotated"):
        continue
      with open(fpath, 'r') as fin:
        lines = fin.read().split("\n")
      colname = None
      sprites = []
      for line in lines:
        if colname is not None:
          if line.startswith("  - name:"): # exactly two spaces is important
            spritename = line[9:]
            sprites.append([spritename, USED_NEVER]) # last element == ever used
        elif "tk2dSpriteCollectionData.cs" in line:
          colname = f.split(".")[0]
          continue
      if colname is not None:
        # print(f"{len(sprites):5} sprites in {colname}")
        colSprites[colname] = sprites
  return colSprites

def findAnims(decomp_path, colSprites):
  libAnims = {}
  for root, subdirs, files in os.walk(decomp_path):
    for f in files:
      fpath = os.path.join(root, f)
      if not fpath.endswith(".annotated"):
        continue
      with open(fpath, 'r') as fin:
        lines = fin.read().split("\n")
      libname = None
      anims = []
      lastcol = None
      for line in lines:
        if libname is not None:
          if line.startswith("    - spriteCollection:"): # exactly two spaces is important
            lastcol = line.split("#")[-1].replace(".prefab","").strip()
          elif line.startswith("      spriteId:"): # exactly two spaces is important
            sid = int(line.split(":")[1].strip())
            colSprites[lastcol][sid][1] = USED_SPRITE
            tup = [lastcol, sid, colSprites[lastcol][sid]]
            # print(f"    {tup}")
            anims[-1][1].append(tup)
          elif line.startswith("  - name:"): # exactly two spaces is important
            anim = line[9:].strip()
            anims.append([anim, [], USED_NEVER])
            # print(f"  {anim}")
        elif "tk2dSpriteAnimation.cs" in line:
          libname = f.split(".")[0]
          # print(libname)
          continue
      if libname is not None:
        # print(f"{len(anims):5} anims in {libname}")
        libAnims[libname] = anims
  return libAnims

def findAnimators(decomp_path, libAnims):
  animators = {}
  errors = 0
  for root, subdirs, files in os.walk(decomp_path):
    for f in files:
      fpath = os.path.join(root, f)
      if not fpath.endswith(".annotated"):
        continue
      with open(fpath, 'r') as fin:
        lines = fin.read().split("\n")
      lastline = None
      script = f.split(".")[0]
      for line in lines:
        if "defaultClipId: " in line:
          lib = lastline.split("#")[-1].replace(".prefab","").strip()
          clip = int(line.split(":")[-1].strip())
          try:
            anim = libAnims[lib][clip]
            anim[2] = USED_ANIM
          except:
            errors += 1
            # print(f"file: {f}")
            # print(f"lib: {lib}")
            # print(f"clip: {clip}")
            # print(f"len: {len(libAnims[lib])}")
            continue
            # raise
          print(f"{script} uses animation {anim[0]} (#{clip} from {lib}), which uses the following sprites:")
          for i in range(len(anim[1])):
            anim[1][i][2][1] = USED_ANIM
            print(f"  {anim[1][i][2]} (#{anim[1][i][1]} in {anim[1][i][0]})")
        lastline = line
  print(f"finished with {errors} errors")

def main():
  if len(sys.argv) < 2:
    print("Please provide a path to the Gungeon decomp")
    return

  decomp_path = sys.argv[1]
  colSprites = findSprites(decomp_path)
  # print("\n\n\n")
  libAnims = findAnims(decomp_path, colSprites)
  # print("\n\n\n")
  findAnimators(decomp_path, libAnims)

  for col, sprites in colSprites.items():
    print(f"unused sprites in {col}:")
    for sprite in sprites:
      if len(sprite[0]) == 0:
        continue
      if "/" in sprite[0]:
        continue
      if sprite[1] > 0:
        continue
      print(f"  {sprite[0].strip()}")

  # for coll,collitems in libAnims.items():
  #   print(f"in collection {coll}:")
  #   for item in collitems:
  #     print(f"{item}")
  #   break

if __name__ == "__main__":
  main()
