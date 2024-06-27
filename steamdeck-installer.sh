#!/usr/bin/bash
#Helper script for installing modded gungeon on Linux / Steamdeck

#Constants
ts_api_link="https://thunderstore.io/api/experimental/package/MtG_API/Mod_the_Gungeon_API/"
ts_api_json="./temp_api.json"
ts_api_base="https://thunderstore.io/c/enter-the-gungeon/p/MtG_API/Mod_the_Gungeon_API/"

ts_bep_link="https://thunderstore.io/api/experimental/package/BepInEx/BepInExPack_EtG/"
ts_bep_json="./temp_bep.json"
ts_bep_base="https://thunderstore.io/c/enter-the-gungeon/p/BepInEx/BepInExPack_EtG/"

etg_install_path="/home/$USER/.local/share/Steam/steamapps/common/Enter the Gungeon"
etg_install_backup="$etg_install_path/_install_backup"

#Easy colors (condensed)
BLN="\e[0m"   ; UND="\e[1;4m" ; INV="\e[1;7m" ; CRT="\e[1;41m";
BLK="\e[1;30m"; RED="\e[1;31m"; GRN="\e[1;32m"; YLW="\e[1;33m";
BLU="\e[1;34m"; MGN="\e[1;35m"; CYN="\e[1;36m"; WHT="\e[1;37m";
CLR="\033[2K";

#Useful printing codes (short)
infop() {       echo -e  "$WHT[$GRN"">""$WHT]$BLN $@"; }
warnp() {       echo -e  "$WHT[$YLW""#""$WHT]$BLN $@"; }
erorp() {   >&2 echo -e  "$WHT[$RED""@""$WHT]$BLN $@"; }
prpty() {   >&2 echo -en "$WHT[$BLU""?""$WHT] $@ [Y/n] $BLN"; read -sn1 v; if [[ $v =~ ^[^nN]?$ ]]; then 2>&1 echo -e "$GRN""yes""$BLN"; else 2>&1 echo -e "$RED""no""$BLN"; fi; [[ $v =~ ^[^nN]?$ ]]; }
prptn() {   >&2 echo -en "$WHT[$BLU""?""$WHT] $@ [y/N] $BLN"; read -sn1 v; if [[ $v =~ ^[yY]$   ]]; then 2>&1 echo -e "$GRN""yes""$BLN"; else 2>&1 echo -e "$RED""no""$BLN"; fi; [[ $v =~ ^[yY]$   ]]; }

#Other helper functions
get_dl_link() {
  echo "$(cat "$1" | grep -Eo "icon.*\.png" | cut -f 3 -d '"' | sed -re 's/icons/packages/'  | sed -re 's/\.png/\.zip/')"
}

dl_error() {
  erorp "  Double check your internet connection. If the problem persists, click ${CYN}Manual Download${BLN} at ${CYN}${1}${BLN} and move the .zip file to the same directory as this script, then rerun."
}

extract() {
  which unzip >/dev/null 2>&1 && unzip -o "$1" -d"$2" >/dev/null && return
  which 7z >/dev/null 2>&1 && 7z x "$1" -o"$2" -y >/dev/null && return
  which ark >/dev/null 2>&1 && ark --batch -o "$2" "$1" >/dev/null 2>&1 && return
  erorp "No suitable .zip extraction utility found (unzip, 7z, and ark supported), aborting setup"
  exit
}

###############
##MAIN SCRIPT##
###############

infop "Checking for necessary core utilities"
! which grep >/dev/null 2>&1 && erorp "grep not found" && exit
! which sed >/dev/null 2>&1 && erorp "sed not found" && exit
! which wget >/dev/null 2>&1 && erorp "wget not found" && exit
! which curl >/dev/null 2>&1 && erorp "curl not found" && exit
! which cut >/dev/null 2>&1 && erorp "cut not found" && exit
! which tr >/dev/null 2>&1 && erorp "tr not found" && exit
! which mv >/dev/null 2>&1 && erorp "mv not found" && exit
! which cp >/dev/null 2>&1 && erorp "cp not found" && exit
! which chmod >/dev/null 2>&1 && erorp "chmod not found" && exit
! which cat >/dev/null 2>&1 && erorp "cat not found" && exit

infop "Checking Gungeon install path"
if [ ! -d "$etg_install_path" ]; then
  erorp "  Gungeon install path $CYN${etg_install_path}$BLN does not exist"
  erorp "  If you installed Gungeon to a different directory, please adjust ${CYN}etg_install_path${BLN} and rerun the script"
  exit
fi
infop "  Found $CYN${etg_install_path}$BLN"

infop "Checking for native Gungeon executable"
if [ ! -e "${etg_install_path}/EtG.x86_64" ]; then
  if [ ! -e "${etg_install_path}/EtG.exe" ]; then
    erorp "  Could not find Gungeon at expected location $CYN${etg_install_path}/EtG.x86_64$BLN"
    erorp "  If you installed Gungeon to a different directory, please adjust ${CYN}etg_install_path${BLN} and rerun the script"
  else
    erorp "  Found Windows executable $CYN${etg_install_path}/EtG.exe$BLN, but no native executable"
    erorp "  Please disable Proton compatibility by right clicking ${CYN}Enter the Gungeon${BLN} in Steam, clicking ${CYN}Properties${BLN}, clicking the ${CYN}Compatibility${BLN} tab, and unchecking ${CYN}Force the use of a specific Steam Play compatibility tool${BLN}. You can also access ${CYN}Properties${BLN} by pressing the gear icon and selecting it from the menu."
  fi
  exit
fi
infop "  Found $CYN${etg_install_path}/EtG.x86_64$BLN"

infop "Getting download link for latest EtG BepInEx Pack"
if [ ! -e "$ts_bep_json" ]; then
  curl -s -X GET "$ts_bep_link" -H  "accept: application/json" > "$ts_bep_json"
fi
ts_bep_dl="$(get_dl_link "${ts_bep_json}")"
if [ -z "$ts_bep_dl" ]; then
  erorp "  Failed to retrieve download link for EtG BepInEx Pack."
  dl_error "$ts_bep_base"
  exit
fi
infop "  Found $CYN${ts_bep_dl}$BLN"

infop "Getting download link for latest MtG API"
if [ ! -e "$ts_api_json" ]; then
  curl -s -X GET "$ts_api_link" -H  "accept: application/json" > "$ts_api_json"
fi
ts_api_dl="$(get_dl_link "${ts_api_json}")"
if [ -z "$ts_api_dl" ]; then
  erorp "  Failed to retrieve download link for MtG API."
  dl_error "$ts_api_base"
  exit
fi
infop "  Found $CYN${ts_api_dl}$BLN"

ts_bep_file="$(echo "${ts_bep_dl}" | rev | cut -f 1 -d '/' | rev)"
if [ ! -e "$ts_bep_file" ]; then
  infop "Downloading $ts_bep_file"
  wget -q "$ts_bep_dl"
fi
if [ ! -e "$ts_bep_file" ]; then
  erorp "  Error downloading EtG BepInEx Pack."
  dl_error "$ts_bep_base"
  exit
fi

ts_api_file="$(echo "${ts_api_dl}" | rev | cut -f 1 -d '/' | rev)"
if [ ! -e "$ts_api_file" ]; then
  infop "Downloading $ts_api_file"
  wget -q "$ts_api_dl"
fi
if [ ! -e "$ts_api_file" ]; then
  erorp "  Error downloading MtG API."
  dl_error "$ts_api_base"
  exit
fi

if [ -d "./tempmods" ]; then
  infop "Removing temporary install directory "
  /usr/bin/rm -rf "./tempmods"
fi

mkdir -p "./tempmods"
infop "Extracting BepInEx Pack"
extract "$ts_bep_file" "./tempmods"
if [ ! -e "./tempmods/BepInExPack_EtG/BepInEx" ]; then
  erorp "BepInEx Pack did not contain expected ${CYN}BepInExPack_EtG/BepInEx${BLN} directory, aborting"
  exit
fi

mkdir -p "./tempmods"
infop "Extracting MtG API"
extract "$ts_api_file" "./tempmods/BepInExPack_EtG/BepInEx"
if [ ! -e "./tempmods/BepInExPack_EtG/BepInEx/plugins/MtGAPI/ModTheGungeonAPI.dll" ]; then
  erorp "MtG API did not contain expected ${CYN}ModTheGungeonAPI.dll${BLN}, aborting"
  exit
fi

infop "Cleaning up extra Thunderstore files"
/usr/bin/rm -f "./tempmods/BepInExPack_EtG/BepInEx/CHANGELOG.md"
/usr/bin/rm -f "./tempmods/BepInExPack_EtG/BepInEx/icon.png"
/usr/bin/rm -f "./tempmods/BepInExPack_EtG/BepInEx/manifest.json"
/usr/bin/rm -f "./tempmods/BepInExPack_EtG/BepInEx/README.md"

if [ -d "$etg_install_path/BepInEx" ]; then
  if ! prptn "Old / partial BepInEx install detected. Overwrite? ${RED}Warning: this will delete any installed mods$BLN"; then
    warnp "BepInEx setup cancelled"
    exit
  fi
  /usr/bin/rm -rf "$etg_install_path/BepInEx"
  /usr/bin/rm -rf "$etg_install_path/doorstop_libs"
  /usr/bin/rm -f  "$etg_install_path/doorstop_config.ini"
  /usr/bin/rm -f  "$etg_install_path/start_game_bepinex.sh"
  /usr/bin/rm -f  "$etg_install_path/version.dll"
  /usr/bin/rm -f  "$etg_install_path/winhttp.dll"
fi

infop "Copying BepInEx and MtG API files into Gungeon install directory"
/usr/bin/cp -rf "./tempmods/BepInExPack_EtG/"* "$etg_install_path/"
if [ ! -e "$etg_install_path/start_game_bepinex.sh" ]; then
  erorp "  Could not copy startup script, check that you have write permissions to the install directory."
  exit
fi

infop "Relocating problematic steam integration DLLs"
mkdir -p "$etg_install_backup"
[ -e "$etg_install_path/EtG_Data/Plugins/x86/libCSteamworks.so" ] && \
  /usr/bin/mv "$etg_install_path/EtG_Data/Plugins/x86/libCSteamworks.so" "$etg_install_backup/libCSteamworks_32.so"
[ -e "$etg_install_path/EtG_Data/Plugins/x86_64/libCSteamworks.so" ] && \
  /usr/bin/mv "$etg_install_path/EtG_Data/Plugins/x86_64/libCSteamworks.so" "$etg_install_backup/libCSteamworks.so"
[ -e "$etg_install_path/EtG_Data/Plugins/x86/libsteam_api.so" ] && \
  /usr/bin/mv "$etg_install_path/EtG_Data/Plugins/x86/libsteam_api.so" "$etg_install_backup/libsteam_api_32.so"
[ -e "$etg_install_path/EtG_Data/Plugins/x86_64/libsteam_api.so" ] && \
  /usr/bin/mv "$etg_install_path/EtG_Data/Plugins/x86_64/libsteam_api.so" "$etg_install_backup/libsteam_api.so"

infop "Making launch script executable"
chmod +x "$etg_install_path/start_game_bepinex.sh"

echo "----------"
infop "Installation complete! You can run modded Gungeon by running the script ${GRN}\"$etg_install_path/start_game_bepinex.sh\"${BLN} (including the quotes) in a terminal, or by adding the path to the above script to your Steam Library as a non-Steam game."
echo "----------"

if prptn "Test now?"; then
  "$etg_install_path/start_game_bepinex.sh"
fi
