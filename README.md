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
  - in C# project: AkSoundEngine.PostEvent("<name of original wav without extension>", ETGModMainBehaviour.Instance.gameObject);
  - run the script with the `-h` flag for more info
```
