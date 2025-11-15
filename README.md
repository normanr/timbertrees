# Timbertrees

## Instructions:

If Timberborn is installed in a default location then you may be able to just run:

```sh
$ python3 timbertrees.py
```

Otherwise, if it's in non-standard location then run:

```sh
$ python3 timbertrees.py \
    -d .../path/to/Timberborn/Timberborn_Data (or .../Timberborn.app/Contents/Resources/Data for Mac)
```

If you'd like to parse assets from mods as well, then include the additional
mod locations in the command, eg:

```sh
$ python3 timbertrees.py \
    -d .../path/to/Timberborn/Timberborn_Data \
    -m .../path/to/mod1-abc \
    -m .../path/to/mod2_1.2.3-xyz
```

## Troubleshooting:

On Windows you may need to set `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled` to `1` to allow Python to find and read files with very long path names (typically shows up as `FileNotFoundError`).
