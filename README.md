# Timbertrees

## Instructions:

Use [AssetRipper](https://github.com/AssetRipper/AssetRipper) to export assets from Timberborn. You can follow the instructions in the [TimberAPI docs](https://timberapi.com/making_mods/exporting_game_files/) on how to do this, but note the following:
 - You do not need Unity Editor or Thunderkit installed, only AssetRipper
 - _Before_ loading game data, under `View` > `Settings` change:
   - `Bundled Assets Export Mode` to `Direct Export`
   - `Script Export format` to `Decompiled`

Then run:

```sh
$ python3 timbertrees.py \
    -d $exported/ExportedProject/Assets/
```

If you'd like to parse assets from mods as well, then follow these additional steps:
 - Make a copy of the mod _outside_ of the BepInEx folder
 - Export the mod's assets to a _subdirectory of the directory containing mod.json_
 - Include the additional mod's exported locations in the command, eg:

```sh
$ python3 timbertrees.py \
    -d $exported/ExportedProject/Assets/ \
    -d $mod1-abc/exported/ExportedProject/Assets/ \
    -d $mod2_1.2.3-xyz/Mod2/exported/ExportedProject/Assets/
```
