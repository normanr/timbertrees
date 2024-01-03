# Timbertrees

## Instructions:

Use [AssetRipper](https://github.com/AssetRipper/AssetRipper) to export assets from Timberborn. You can follow the instructions in the [TimberAPI docs](https://timberapi.com/making_mods/exporting_game_files/) on how to do this, but note the following:
 - You do not need Unity Editor or Thunderkit installed, only AssetRipper
 - The `Script Export format` _must_ be set to `Decompiled`

Then run:

```sh
$ python3 timbertrees.py \
    -d $exported/ExportedProject/Assets/
```

If you'd like to parse assets from mods as well, then export the mod's assets and copy (or create symlinks to) some of the mod's directories under the exported directory as follows:

- `$mod/lang` --> `$mod_exported/ExportedProject/Assets/Resource/localizations`
- `$mod/specifications` --> `$mod_exported/ExportedProject/Assets/Resource/Specifications`

then include additional mod's exported locations in the command, eg:

```sh
$ python3 timbertrees.py \
    -d $exported/ExportedProject/Assets/ \
    -d $mod1_exported/ExportedProject/Assets/ \
    -d $mod2_exported/ExportedProject/Assets/
```
