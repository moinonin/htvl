# HTVL for VS Code

Syntax highlighting and editor support for `.htvl` and `.cal` files: tag calls
(`$(h 1 '' '' 'Title' '')`), variables (`$head`, `$_a`, `$meta`, `${nav0[@]}`),
quoted and bare arguments, nested calls, and HTML comments.

## Structure

| File | Purpose |
| --- | --- |
| `package.json` | Extension manifest: registers `.htvl`/`.cal` and the grammar |
| `syntaxes/htvl.tmLanguage.json` | TextMate grammar (`source.htvl`) |
| `language-configuration.json` | Comment/bracket/folding behaviour |

## Try it without publishing

```bash
# From this directory:
npx @vscode/vsce package          # produces htvl-0.2.0.vsix
code --install-extension htvl-0.2.0.vsix
```

Or symlink the whole directory into your extensions folder for development:

```bash
ln -s "$PWD" ~/.vscode/extensions/htvl
```

## Publishing

```bash
npx @vscode/vsce login moinonin
npx @vscode/vsce publish
```

The publisher id (`moinonin`) and repository URL live in `package.json`; bump
`version` with each release.
