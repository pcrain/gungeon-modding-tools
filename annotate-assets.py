#!/usr/bin/python
#Annotates decompiled assets, showing the corresponding class / asset names for guids

import sys, os, re

def processMetaFiles(decomp_path):
  guidmap = {}
  count = 0
  for root, subdirs, files in os.walk(decomp_path):
    for f in files:
      fpath = os.path.join(root, f)
      if not fpath.endswith(".meta"):
        continue

      count += 1
      with open(fpath, 'r') as fin:
        for line in fin.read().split("\n"):
          if not line.startswith("guid: "):
            continue
          guid = line.split(" ")[1]
          guidmap[guid] = f.removesuffix(".meta")

  print(f"Collected data from {count} .meta files")
  return guidmap

def processAssets(decomp_path, guidmap):
  guidfinder = re.compile(r"guid: ([0-9a-f]+)")
  compfinder = re.compile(r"fileID: ([0-9]+)")
  secfinder  = re.compile(r"--- !u![0-9]+ &([0-9]+)")
  scriptfinder = re.compile(r"m_Script: .* guid: ([0-9a-f]+)")

  count = 0
  for root, subdirs, files in os.walk(decomp_path):
    for f in files:
      fpath = os.path.join(root, f)
      if not fpath.endswith(".prefab"):
        continue

      count += 1
      componentMap = {}
      annotatedLines = []

      # first pass: collecting info
      nextLineIsSectionType = False
      secId = None
      sec = None
      isScript = False
      with open(fpath, 'r') as fin:
        for line in fin.read().split("\n"):
          if nextLineIsSectionType:
            sec = line.removesuffix(":")
            componentMap[secId] = sec
            nextLineIsSectionType = False
            isScript = sec == "MonoBehaviour"
            continue
          if isScript:
            m = scriptfinder.search(line)
            if m is not None:
              guid = m.groups()[0]
              if guid not in guidmap:
                componentMap[secId] = "UNKNOWNSCRIPT"
              else:
                componentMap[secId] = guidmap[guid].removesuffix(".cs")
              isScript = False
          m = secfinder.search(line)
          if m is not None:
            secId = m.groups()[0]
            nextLineIsSectionType = True
            continue

      # second pass: annotating
      with open(fpath, 'r') as fin:
        for line in fin.read().split("\n"):
          # replace guids with prefab names
          m = guidfinder.search(line)
          if m is not None:
            guid = m.groups()[0]
            if guid not in guidmap:
              annotatedLines.append(f"{line} # ??? {guid}")
            else:
              annotatedLines.append(f"{line} # {guidmap[guid]}")
            continue

          # replace fileids with script names
          m = compfinder.search(line)
          if m is not None:
            fileid = m.groups()[0]
            if fileid == "0":
              annotatedLines.append(line)
            elif fileid not in componentMap:
              annotatedLines.append(f"{line} # ??? {fileid}")
            else:
              annotatedLines.append(f"{line} # {componentMap[fileid]}")
            continue

          # just write the line verbatim
          annotatedLines.append(line)

      with open(f"{fpath}.annotated", 'w') as fout:
        fout.write("\n".join(annotatedLines))
  print(f"Annotated {count} .prefab files")

def main():
  if len(sys.argv) < 2:
    print("Please provide a path to the Gungeon decomp")
    return

  decomp_path = sys.argv[1]
  guidmap = processMetaFiles(decomp_path)
  processAssets(decomp_path, guidmap)

if __name__ == "__main__":
  main()
