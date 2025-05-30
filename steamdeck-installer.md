## Modded Enter the Gungeon Setup for Steam Deck / Linux


### Prerequisites

- Make sure the appropriate `mono` / `libmono` package for your distro is installed:
    + Arch: `sudo pacman -S mono`
- If you get a "could not lock database: Read-only file system" error on Steam Deck, you will need to run the following additional commands:
  ```
    sudo steamos-readonly disable
    echo "keyserver hkps://keyserver.ubuntu.com" | sudo tee -a /etc/pacman.d/gnupg/gpg.conf
    sudo pacman-key --init
    sudo pacman-key --populate
    sudo pacman-key --refresh-keys
  ```

### Installing

- Open a terminal and run the following command:
  ```
    bash <(wget -qO- https://raw.githubusercontent.com/pcrain/gungeon-modding-tools/master/steamdeck-installer.sh)
  ```
- Follow the remaining instructions and prompts on screen.

### Playing

On a standard Steam Deck installation, you will be able to launch the game by running the following script (including quotes) in a terminal:

```
"/home/deck/.local/share/Steam/steamapps/common/Enter the Gungeon/start_game_bepinex.sh"
```

You can also add the path to the above script to your Steam library as a non-Steam game.

Please report any issues with the install script to `@Captain Pretzel` in the [Mod the Gungeon Discord](https://discord.gg/uT7AwbcpyC):
