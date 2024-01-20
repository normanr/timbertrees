# Timbertrees

## Instructions:

Use [AssetRipper](https://github.com/AssetRipper/AssetRipper) to export assets from Timberborn. You can follow the instructions in the [TimberAPI docs](https://timberapi.com/making_mods/exporting_game_files/) on how to do this, but note the following:
 - You do not need Unity Editor or Thunderkit installed, only AssetRipper
 - The `Script Export format` _must_ be set to `Decompiled` under `Settings` _before_ loading game data

Then run:

```sh
$ python3 timbertrees.py \
    -d $exported/ExportedProject/Assets/
```

If you'd like to parse assets from mods as well, then export the mod's assets to a _subdirectory of the directory containing mod.json_, and include the additional mod's exported locations in the command, eg:

```sh
$ python3 timbertrees.py \
    -d $exported/ExportedProject/Assets/ \
    -d /path/to/Timberborn/BepInEx/plugins/$mod1-abc/exported/ExportedProject/Assets/ \
    -d /path/to/Timberborn/BepInEx/plugins/$mod2_1.2.3-xyz/Mod2/exported/ExportedProject/Assets/
```
