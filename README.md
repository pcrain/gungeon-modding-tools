# A collection of various tools and scripts for modding Enter the Gungeon

## Files

| Filename                  | Description                                           |
|:--------------------------|:------------------------------------------------------|
| gen-gungeon-audio-bank.py | generate WWise audio banks from a folder of WAV files |
|                           |                                                       |

### gen-gungeon-audio-bank.py

```
Requirements:
  - python 3.9

Basic Usage:
  - from shell: gen-gungeon-audio-bank.py <path to folder containing wavs> <path to output .bnk>
    - can pass a spreadsheet of audio data with -s to set volume, loops, and channel (sound / music) information
    - if the spreadsheet does not exist, one will be created with default values and can be edited later
    - valid fields:
      - name: base name of audio file (without path or file extension)
      - volume: the volume of the audio file in game (default: 1.0)
      - loops: the number of times the audio file should loop (0 == infinite, default: 1)
      - channel: the channel the audio plays on; can be "sound" or "music" (default: "sound")
  - in C# project: AkSoundEngine.PostEvent(eventname, ETGModMainBehaviour.Instance.gameObject), where eventname="<name of original wav without extension>";
    - can use eventname+"_stop" to stop playing an audio file w.r.t. to the current game object
    - can use eventname+"_stop_all" to stop playing all instances of the audio file
    - can use eventname+"_pause" to pause the currently playing audio globally (only tested with music, not normal sounds)
    - can use eventname+"_resume" to resume the currently playing audio globally (only tested with music, not normal sounds)
  - run the script with the `-h` flag for more info
```
