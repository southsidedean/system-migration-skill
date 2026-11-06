# Archive manifest

Created: <YYYY-MM-DD> from <source machine>

| Archive | Size | Entries | SHA-256 | Encrypted | Holds secrets or client data |
|---|---|---|---|---|---|
| <name>.tar.gz | | | | no | no |

## Contents

- <Top-level paths in each archive>

## Deliberately left out

- <Item and reason>

## Known gaps

- <Symlinks that point outside the archive, unreadable items>

## To verify

```sh
shasum -a 256 -c <name>.tar.gz.sha256
tar -tzf <name>.tar.gz | wc -l
```

On Linux, use `sha256sum -c` in place of `shasum -a 256 -c`.
