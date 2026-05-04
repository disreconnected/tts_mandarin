# Installing ffmpeg (required for pydub tempo / export)

The app uses **ffmpeg** (via pydub and direct CLI calls) for pitch-preserving speed changes and some conversions. Install ffmpeg so the `ffmpeg` command is available in a terminal.

## Verify

```bash
ffmpeg -version
```

You should see version information, not “command not found”.

## Windows

1. **Chocolatey** (admin shell):

   ```powershell
   choco install ffmpeg
   ```

2. **Scoop**:

   ```powershell
   scoop install ffmpeg
   ```

3. **Manual:** Download a build from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) (or a trusted mirror such as [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)), extract it, and add the `bin` folder to your **PATH** environment variable.

## macOS

**Homebrew:**

```bash
brew install ffmpeg
```

## Linux

**Debian / Ubuntu:**

```bash
sudo apt update
sudo apt install ffmpeg
```

**Fedora:**

```bash
sudo dnf install ffmpeg
```

**Arch:**

```bash
sudo pacman -S ffmpeg
```

After installation, open a **new** terminal and run `ffmpeg -version` again.
