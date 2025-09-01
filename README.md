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
    -d $exported/ExportedProject/
```

If you'd like to parse assets from mods as well, then follow these additional steps:
 - Make a copy of the mod _outside_ of the Timberborn Mods folder
 - Export the mod's assets to a _subdirectory of the directory containing manifest.json_
 - Include the additional mod's exported locations in the command, eg:

```sh
$ python3 timbertrees.py \
    -d $exported/ExportedProject/ \
    -d $mod1-abc/exported/ExportedProject/ \
    -d $mod2_1.2.3-xyz/Mod2/exported/ExportedProject/
```

## Troubleshooting:

On Windows you may need to set `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled` to `1` to allow Python to find and read files with very long path names (typically shows up as `FileNotFoundError` when loading unity metadata).
