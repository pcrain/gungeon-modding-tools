# A collection of various tools and scripts for modding Enter the Gungeon

## Files

| Filename                           | Description                                                   |
| :--------------------------        | :------------------------------------------------------       |
| gen-gungeon-audio-bank.py          | generate WWise audio banks from a folder of WAV files         |
| gungeon-gun-sprite-json-creator.py | visual editor for hand attach points on gun sprites           |
| annotate-assets.py                 | adds script and asset name annotations to extracted assets    |
|                                    |                                                               |

### gen-gungeon-audio-bank.py

```
Requirements:
  - python 3.9+

Basic Usage:
  - from shell: gen-gungeon-audio-bank.py <path to folder containing wavs> <path to output .bnk>
    - can pass a spreadsheet of audio data with -s to set volume, loops, and channel (sound / music) information
    - if the spreadsheet does not exist, one will be created with default values and can be edited later
    - valid fields:
      - name: base name of audio file (without path or file extension)
      - volume: the decibel volume adjustent of the audio file in game; can be negative (default: 1.0)
      - loops: the number of times the audio file should loop (0 == infinite, default: 1)
      - channel: the channel the audio plays on; can be "sound" or "music" (default: "sound")
  - in C# project: AkSoundEngine.PostEvent(eventname, ETGModMainBehaviour.Instance.gameObject), where eventname="<name of original wav without extension>";
    - can use eventname+"_stop" to stop playing an audio file w.r.t. to the current game object
    - can use eventname+"_stop_all" to stop playing all instances of the audio file
    - can use eventname+"_pause" to pause the currently playing audio globally (only tested with music, not normal sounds)
    - can use eventname+"_resume" to resume the currently playing audio globally (only tested with music, not normal sounds)
  - run the script with the `-h` flag for more info

Automatic Usage:
  - change the `ALLOW_AUTORUN` variable near the top of the script from `False` to `True` and copy the script to the folder containing your .wav files to enable autorun mode
  - in autorun mode, whenever the script is run without arguments, the following will happen automatically:
    - the script will scan its current directory for any `.csv` files, and load audio metadata from the first `.csv` file it finds
    - if no `.csv` file is found, the script will create a default `Sounds.csv` file in its directory
    - the script will scan its current directory for wave files and assemble them all in a soundbank with the same base name as the metadata `.csv` (e.g., `Sounds.bnk`)
    - consequently, renaming the audio `.csv` file will change the filename of the automatically-generated sound bank

Known Bugs:
  - 8-bit PCM files seem to crash, so convert to 16-bit LE PCM wav before using
  - ~~stereo files tend to crash, so please convert .WAV files to mono format before using~~ should be fixed
```

### gungeon-gun-sprite-json-creator.py

```
Requirements:
  - python 3.11+ (might work with 3.9, untested)
  - dearpygui, pillow, numpy, screeninfo
    - you can install all of the above with `pip install --user --break-system-packages dearpygui pillow numpy screeninfo`

Basic Usage:
  - running `gungeon-gun-sprite-json-creator.py` will open an editor interface and initiate a file picker dialog
    - opening a PNG of a gun sprite will automatically load its corresponding JSON file, if it exists
    - you can optionally pass the path to the sprite on the command line to open it directly
    - the editor will remember the last opened file upon closing
  - clicking anywhere on the image of the open gun will modify its attach points
    - attach points can be enabled / disabled by clicking on the corresponding enable / disable buttons
    - left click = change main hand attach point
    - right click = change off hand attach point
    - shift + left click = change clip attach point
    - shift + right click = change casing attach point
  - click "Save Changes" to save the data to a JSON with the same name as the sprite
  - click "Revert Changes" to discard all changes without saving
  - click "Import / Edit Gun Data" to open a new image for attach point editing

Advanced Usage:
  - every button has a corresponding keyboard shortcut (shown beside it) for faster navigation
  - the left pane lets you scroll through and quickly open all images in the same directory as the currently open image
    - the search field above the pane lets you filter the list by name
  - checking "Autosave on switch / exit" will automatically save changes when opening a new gun or closing the program
  - checking "Don't warn about overwriting file" will suppress the popup when attempting to save over existing gun data
  - clicking "Copy Gun Data" will copy the current attach points and enable / disable status to an internal clipboard
  - clicking "Paste Gun Data" will paste attach point data from the last copied gun over the current one
    - useful for editing multiple frames with similar attach points
```

### annotate-assets.py
```
Requirements:
  - python 3.11+ (might work with older versions, untested)

Basic Usage:
  - running `annotate-assets.py <path to gungeon decomp>` will scan and annotate to all `.asset` and `.prefab` files with information about scripts and resource names
  - these new files will be created with the extensions `.asset.annotated` and `.prefab.annotated`
```
