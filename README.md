# CipherLab Pro

A fully **offline** desktop application (Python 3.12 + PySide6) for encoding, decoding, encryption, hashing,
hexadecimal analysis and local cryptographic experiments. Dark theme, Persian/Arabic/English/emoji support.

* **No APIs, no AI services, no accounts, no telemetry, no update checks, no network connections.**
* All analysis uses deterministic local algorithms with explainable scoring.
* Passwords and keys are never written to history, settings or logs.

---------------------------------------------------------------------------------------------------

## 1. Installation

Requirements: Python 3.12 (3.10+ should work), 64-bit. Dependencies: `PySide6` (GUI) and `cryptography`
(AES-GCM / PBKDF2). `pytest` and `pyinstaller` are only for development/packaging.

### Windows 10/11 (PowerShell)
```powershell
cd CipherLab-Pro
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt       # needs internet ONCE (install time only)
python main.py
```

### Linux (Debian/Ubuntu example)
```bash
sudo apt install python3-venv libxcb-cursor0 libegl1 libxkbcommon-x11-0   # Qt runtime libraries
cd CipherLab-Pro
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt       # needs internet ONCE (install time only)
python main.py
```

### Run the tests
```bash
pip install -r requirements-test.txt  # pytest + coverage (adds nothing to the application itself)
python -m pytest                      # core + offline + headless GUI tests (Qt "offscreen" platform)
python scripts/check_dependencies.py  # compares the code's imports with the requirements files
```

## 2. Installing without internet (local wheel files)

On a computer **with** internet and the **same OS / CPU architecture / Python version** as the target:
```bash
sh scripts/download_wheels.sh         # Windows: .\scripts\download_wheels.ps1
# = python -m pip download -r requirements-dev.txt -c constraints.txt -d wheelhouse
```
Copy the whole `CipherLab-Pro/` folder (including `wheelhouse/`) to the offline computer, then:
```bash
sh scripts/install_offline.sh         # Windows: .\scripts\install_offline.ps1
# = pip install --no-index --find-links wheelhouse -r requirements-dev.txt -c constraints.txt
python main.py
```
`--no-index` forbids pip from contacting any package server.

Dependencies, versions, audit and offline details are documented in **[DEPENDENCIES.md](DEPENDENCIES.md)**.

## 3. Offline architecture

| Phase | Network? | What happens |
|---|---|---|
| **Installation** | Yes, optional | `pip` may download PySide6 and cryptography. Skip it entirely by using the wheelhouse above. |
| **Runtime** | **Never** | The app reads/writes only local files in its data folder and never opens a socket. |

Enforced by design and by tests:
1. **No network libraries** are imported by any application module (`socket`, `ssl`, `http`, `urllib.request`,
   `requests`, `httpx`, `aiohttp`, `QtNetwork`, `QtWebEngine`, ...). `tests/test_offline_behavior.py` parses every
   source file's AST and fails if one appears.
2. **Runtime guard** (`src/utils/offline_guard.py`): `main.py` replaces Python's socket entry points with functions that raise
   and count. Tests install the same guard and prove core operations trigger zero attempts. (A guard cannot stop native
   C/C++ code; the import ban and the absence of network code cover that.)
3. No remote fonts/images/scripts/stylesheets: the theme is an in-code stylesheet; no browser component is used.
4. No license server, remote database, cloud sync, telemetry or auto-update. `requirements.txt` has no HTTP client.

### Testing with the network disconnected
1. Disconnect Wi-Fi / unplug Ethernet (or enable airplane mode).
2. `python scripts/offline_selfcheck.py` → expect `network attempts blocked: 0`.
3. `python main.py` and use every tab. Everything works the same.
4. Optional, Linux: run inside an empty network namespace: `unshare -rn python -m pytest`.
5. Optional, any OS: watch the process with your firewall / `netstat` / Resource Monitor: it never opens connections.

## 4. Using each tab

Common to all editors: **Paste / Copy / Clear / Import / Export**, drag-and-drop a file onto an input editor, text direction
adapts automatically (Persian/Arabic are right-to-left). The status bar shows chars/bytes of the active input, progress and
a Cancel button for background work. Shortcuts: **Ctrl+Enter** run · **Ctrl+L** clear · **Ctrl+O** import · **Ctrl+S** export ·
**Ctrl+1…9 / Ctrl+0** switch to tabs 1-10 and **Ctrl+Shift+1 / 2** to tabs 11-12.

| Tab | Purpose and example |
|---|---|
| **Encode** | Text → bytes (UTF-8, UTF-16, ASCII, Latin-1) → Hex, Base64, URL, `\uXXXX`, JSON escape, binary, decimal. `Hello` → hex `48 65 6c 6c 6f`. Characters a charset cannot represent are reported, never dropped. |
| **Decode** | Any of those representations → exact bytes → text. **Strict** by default; "replace" is an explicit lossy option. If bytes are not valid text you get an error and the raw hex. *Suggest format* lists possible formats and states ambiguity (`48656c6c6f` is valid hex **and** Base64). |
| **Encrypt** | AES-256-GCM with password (PBKDF2-HMAC-SHA256, random salt + nonce), AES-GCM with a raw hex key, educational repeating-key XOR, SHA-256/512 and HMAC-SHA256/512. Output of AES is a versioned JSON container. |
| **Decrypt** | Opens CipherLab Pro containers (validates all metadata, verifies the tag before returning plaintext) and XOR hex. A wrong password or tampered data gives one safe error. |
| **Hex Analyzer** | Paste hex such as `dcdcdcd324ad81ad8254dcdbddfcdcc7dcde24ad81af88acb0af88`. Validates, normalises (spaces, `:`, `-`, `,`, `0x`, `\x`), rejects odd length, shows entropy/byte frequencies, tests encodings, signatures, compression, nested encodings, single-byte XOR and optional bounded repeating-key XOR, then ranks candidates and states what is reliable and what is not. For that sample (27 bytes) the honest result is **inconclusive**. |
| **XOR Analyzer** | Key-length ranking (Hamming distance), single-byte and bounded repeating-key analysis, or XOR with a known key (text or hex). |
| **Compare Results** | Candidates sent from the analyzers, side by side (method, score, confidence, printable ratio, errors, entropy, key, preview, reasoning). Export as JSON. |
| **History** | Optional local log; search, delete a record, clear all, disable recording. |
| **Settings** | History, file-size limit, PBKDF2 iterations, default charset, Persian scoring and an optional custom Persian frequency table (JSON `{"ا": 13.0, ...}`), data-folder location. |

Examples
* Round trip: Encode `سلام دنیا` (UTF-8 → Base64) = `2LPZhNin2YUg2K/ZhtuM2Kc=`; paste into Decode (Base64 → UTF-8).
* Encrypt `meet at noon` with password `correct horse`, copy the JSON, paste into Decrypt, enter the password.
* XOR: Encrypt tab → XOR, key text `K3`, then paste the hex into XOR Analyzer → *Single-byte* (try a 1-byte key on a long sentence).

## 4b. Interface language

Settings → **Language** switches the interface immediately (no restart) between **English, فارسی (Persian), العربية (Arabic),
中文 (Chinese) and Русский (Russian)**. Persian and Arabic use a right-to-left layout. The choice is stored in `settings.json`.
Translated: tabs, menus, buttons, labels, placeholders, tooltips, table headers, counters and the status bar.
Intentionally **not** translated: error messages produced by the core, the analysis report text, dialog boxes, the
Settings/History info notes and the About page (English only), and technical names such as UTF-8 or Base64.
Translations live in `src/gui/i18n.py` (one table; add a row to translate another string).

## 4c. Theme

Settings → **Theme** switches instantly between **Blue (dark)** (default) and **Green (hacker)** (green text on black).
The choice is stored in `settings.json`. Both themes live in `src/gui/theme.py`.

## 4d. XOR Encoder / XOR Decoder (custom HEX password)

Two tabs encrypt UTF-8 text with **repeating-key XOR using your own hexadecimal password** and restore it again.
* The password is treated as **hex data**, not text. Any length is accepted (no limit in the application), `0x` prefix optional,
  separators (space `:` `-` `,` `_`) allowed, **leading zeros preserved** (`0001` = bytes `00 01`).
* An odd digit count is read as a number with an implied leading zero (`0x474` = `0x0474` = `04 74`); tick *Strict* to reject it.
* The whole password is used: data byte *i* is XORed with password byte *i mod length*. Nothing is hardcoded or modified.
* Output is HEX (spaced or continuous, lower or upper case). Decoding converts back with UTF-8; wrong passwords give other bytes
  (XOR has no integrity check) and, if they are not valid UTF-8, the raw bytes are shown as hex.
* XOR is **not secure encryption**. History never stores the password or any content for these operations.
* Code: `src/core/xor_cipher.py` (logic), `src/gui/xor_encoder_tab.py`, `src/gui/xor_decoder_tab.py`, `src/gui/xor_password.py`.

## 5. Scoring model (all rules are explainable)

`score = quality × prior`, shown for every candidate.
* **quality** (0–1): for English `0.4·printable + 0.3·letters/spaces + 0.3·letter-frequency fit`, damped for samples < 8 bytes;
  for Persian `0.3·printable + 0.3·script share + 0.4·letter fit` (table is approximate and configurable); structural evidence
  (valid compressed stream, file signature) gives 0.9.
* **prior**: raw reading 1.0, container 0.95, nested encoding 0.9, single-byte XOR 0.8, UTF-16 0.7, repeating-key XOR 0.7,
  reversal 0.5, Latin-1 0.4. Methods that can "succeed" on any input get low priors.
* **confidence**: `<0.35 none · <0.6 low · <0.8 medium · else high`, then **capped**: XOR on < 16 bytes ≤ low; repeating-key
  XOR ≤ medium; Latin-1 ≤ low. If nothing reaches medium the report says **INCONCLUSIVE**.

## 6. Cryptography and file format

* AES-GCM and PBKDF2 come from the maintained `cryptography` package; hashes/HMAC from the standard library. No primitives are hand-written.
* Password mode: 600,000 PBKDF2-HMAC-SHA256 iterations by default (configurable 100k–5M), fresh 16-byte salt **and** fresh 96-bit
  random nonce per message, so a (key, nonce) pair is never reused; an in-process uniqueness guard backs this up in raw-key mode.
* Container (`"format": "CipherLabPro", "version": 1`): `cipher, kdf, iterations, salt, nonce, ciphertext` (Base64). The header
  is authenticated as AES-GCM associated data, so editing any field makes decryption fail. Unknown fields, bad Base64, wrong
  lengths, out-of-range iterations and unsupported versions are rejected before any key derivation.
* Limits: plaintext ≤ 16 MiB, XOR analysis ≤ 64 KiB, decompression output ≤ 16 MiB (bomb guard), imports ≤ 10 MB (setting).

## 7. Security limitations (please read)

* **Encoding (Base64/hex/URL), hashing (SHA/HMAC) and encryption (AES-GCM) are different things.** Only AES-GCM hides data.
* XOR is **not** secure. XOR analysis is statistical; readable output is evidence, not proof. Short inputs prove nothing.
* The app **cannot** decrypt unknown ciphertext without the algorithm and key and says so. No cracking, no unbounded brute force.
* Python cannot reliably wipe secrets from memory; passwords exist as Python strings while the app runs. Use a trusted computer.
* Plaintext shown on screen, copied to the clipboard or exported is not protected by the app. `history.db` is **not encrypted**
  (it never contains passwords/keys, and keeps no content for encrypt/decrypt/HMAC) – you can disable or clear it.
* Raw-key AES mode relies on you generating a strong random key; random 96-bit nonces are safe up to ~2^32 messages per key.
* A forgotten password cannot be recovered.
* The built-in Persian letter-frequency table is approximate; supply your own for serious use.

Data folder: Windows `%APPDATA%\CipherLabPro`, Linux `~/.local/share/CipherLabPro` (override with `CIPHERLAB_DATA_DIR`):
`settings.json`, `history.db`, `cipherlab.log` (redacted, no content).

## 8. Packaging with PyInstaller (optional)

```powershell
pip install -r requirements-dev.txt
.\scripts\build_exe.ps1               # Linux: sh scripts/build_exe.sh
# -> dist\CipherLabPro\CipherLabPro.exe   (build on the target OS; no cross-compiling)
```

## 9. Project layout

```
main.py                    entry point (installs the offline guard)
src/core/                  encodings, xor_tools, crypto_engine, hex_analyzer, statistics, candidate_ranking,
                           file_handler, history_manager, settings        (no GUI imports)
src/models/                analysis_result, crypto_envelope
src/utils/                 validation, logging_config (redacting), offline_guard, progress
src/gui/                   main_window + one module per tab, widgets, context (workers), theme
tests/                     pytest suite (incl. offline and headless GUI tests)
scripts/                   wheelhouse download/install, offline self-check, PyInstaller builds
```
Cryptographic logic never lives in GUI code: tabs only collect input, call `src.core`, and show results/errors.
