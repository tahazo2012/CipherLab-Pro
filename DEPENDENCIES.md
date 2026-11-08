# CipherLab Pro - Dependency Architecture and Audit Report

Everything in this report was **measured on the real project** (Linux, Python 3.12.3, PySide6-Essentials 6.12.0,
cryptography 50.0.2) unless it says "not verified". Commands were run; numbers are copied from the output.

---------------------------------------------------------------------------------------------------

## 0. Summary of findings

| # | Finding | Evidence |
|---|---|---|
| 1 | The application needs only **2 external packages** at runtime: `PySide6-Essentials` and `cryptography` (plus 3 automatic helpers: `shiboken6`, `cffi`, `pycparser`). | AST scan of all 40 runtime source files |
| 2 | `PySide6` (the meta-package) was **unnecessary**: it also installs `PySide6-Addons`, `PySide6-WebEngine` (a complete Chromium browser) and `PySide6-Pdf`. The code imports only `QtCore`, `QtGui`, `QtWidgets`. | Your own pip log; scan; full test suite passes with Essentials only |
| 3 | Switching to `PySide6-Essentials` cuts the download from about **263 MB to about 88 MB** and the installed size from **742 MB to 294 MB**. | Wheel sizes from your pip log; `du -sh site-packages` of both environments |
| 4 | **No known vulnerabilities** in any of the 10 dependency packages at the tested versions. `pip` itself (24.0 here, 23.2.1 in your log) is flagged and should be upgraded. | `pip-audit`: 11 packages audited |
| 5 | **Python:** the code needs 3.10+ (`int.bit_count`); the pinned, tested stack needs **3.11+**; recommended **3.12** (the only version tested). Python 3.10 reached end of life in October 2026. | `Requires-Python` metadata; manual source check |
| 6 | A **fresh offline installation** (no network at all, `--no-index`) works and the full suite passes. | Run inside `unshare -rn` (empty network namespace) |
| 7 | Logging is safe by construction: the application makes **one** log call and it records only an exception type name. The redaction filter was hardened (quoted values, tracebacks). | grep of all logging calls; new tests |
| 8 | **Not built yet** (listed in your spec): File Encryption, File Decryption, Password Generator. This task was dependency analysis, so I did not add features. | Source inspection |

---------------------------------------------------------------------------------------------------

## 1. Module status (your 13 modules vs the existing application)

| Module in your list | Status | Where / libraries |
|---|---|---|
| XOR Encoder, XOR Decoder | **exists** | tabs `XOR Encoder/Decoder`; `core/xor_cipher.py` (stdlib only) |
| XOR Analyzer | **exists** | `core/xor_tools.py`, `statistics.py` (stdlib only) |
| HEX Analyzer | **exists** | `core/hex_analyzer.py` (+ `zlib`, `bz2`, `lzma`) |
| AES Encryptor / Decryptor | **exists** (Encrypt / Decrypt tabs) | `core/crypto_engine.py` -> `cryptography` |
| Compare Results | **exists** (side-by-side candidates; no byte-by-byte diff view) | Qt only |
| History Manager | **exists** | `core/history_manager.py` -> `sqlite3` |
| Settings Manager | **exists** | `core/settings.py` -> `json` + dataclass (not `QSettings`) |
| Data Format Converter | **exists** (Encode / Decode tabs: Hex, Base64, URL, escapes, binary, decimal) | `core/encodings.py` (stdlib only) |
| File Encryption / File Decryption | **not built** | would need: `cryptography`, `pathlib`, `tempfile`, `os`, `io`, `struct` (section 3.5) |
| Password Generator | **not built** | would need only `secrets` (already imported elsewhere) |

---------------------------------------------------------------------------------------------------

## 2. Complete list of libraries

### 2.1 External packages (the only things in the requirements files)

| Package | Role | Tested version | Requires-Python | File | Category |
|---|---|---|---|---|---|
| **PySide6-Essentials** | GUI (QtCore, QtGui, QtWidgets) | 6.12.0 | >=3.10, <3.16 | requirements.txt | Required |
| shiboken6 | PySide6 binding runtime (automatic) | 6.12.0 | >=3.10, <3.16 | (automatic) | Required |
| **cryptography** | AES-GCM, PBKDF2, scrypt-capable | 50.0.2 | >=3.9 | requirements.txt | Required |
| cffi, pycparser | native glue of cryptography (automatic) | 2.1.1 / 3.12 | >=3.10 / >=3.11 | (automatic) | Required |
| **pytest** (+ pluggy, iniconfig, packaging, Pygments) | test runner | 9.2.0 | >=3.10 | requirements-test.txt | Testing |
| **coverage** | coverage measurement | 7.17.0 | >=3.11 | requirements-test.txt | Testing |
| **pyinstaller** (+ altgraph, pyinstaller-hooks-contrib) | optional .exe packaging | 6.22.3 | >=3.8, <3.16 | requirements-dev.txt | Development |
| **pip-audit** | vulnerability scanner | 2.10.1 | >=3.10 | requirements-audit.txt | Audit (separate venv) |

There are **no optional runtime dependencies**. Packages I considered and rejected: `numpy`/`pandas`/`scipy` (the analyzers
use integer-XOR and histograms: 64 KiB single-byte analysis takes 13 ms and repeating-key analysis with keys up to 40 takes
180 ms, so no numeric library is justified), `requests`/`httpx` (forbidden: offline), `PyQt6`/`Tkinter`/`CustomTkinter` (would
replace the existing GUI), `pytest-cov` (plain `coverage` is enough), `pytest-qt` (the headless tests already work without it),
`colorama` (not used).

### 2.2 Standard-library modules the application really uses (never list these in requirements)

| Module | Used in | Purpose |
|---|---|---|
| `hashlib`, `hmac` | crypto_engine | SHA-256/512, HMAC, constant-time compare (`compare_digest`) |
| `secrets` | crypto_engine | random salt and nonce (CSPRNG) |
| `unicodedata` | crypto_engine | NFC-normalise passwords (Persian/Arabic text) |
| `binascii`, `base64` | encodings, crypto_envelope | Base64 and error types for hex/Base64 |
| `json` | crypto_envelope, encodings, settings, history_manager, compare_tab | encrypted container, settings, JSON escapes, export |
| `re` | encodings, hex_analyzer, validation, logging_config | input validation, log redaction |
| `pathlib`, `os`, `stat`, `tempfile` | file_handler, settings, history_manager, main | safe import/export (atomic write via temp file + `os.replace`), data folder |
| `logging` | logging_config, context | safe, redacting logging |
| `sqlite3`, `contextlib`, `datetime` | history_manager | local history database |
| `zlib`, `bz2`, `lzma` | hex_analyzer | bounded decompression checks |
| `dataclasses`, `enum`, `typing`, `collections`, `math`, `string` | many | data models, statistics |
| `threading` | gui/context | cancel flag for background tasks |
| `urllib.parse` | encodings | percent-encoding only (never `urllib.request`) |
| `ctypes` | main | Windows taskbar icon id |
| `socket` | utils/offline_guard | **blocks** network access (the only file allowed to import it) |
| `sys` | main, settings | platform detection |

### 2.3 Modules from your list that the code does **not** use (and what to do)

| Module | Verdict |
|---|---|
| `codecs` | **Not needed.** `str.encode()` / `bytes.decode()` with explicit `errors=` already do everything, including Persian text. Add it only for incremental decoding of very large text files. |
| `struct` | **Not needed yet.** The container is JSON. Use it when File Encryption gets a binary header (magic, version, KDF parameters, chunk size). |
| `textwrap` | **Not needed.** `bytes.hex(" ")` and Qt text wrapping cover display. Optional for fixed-width hex dumps in exports. |
| `shutil` | **Not needed yet.** Needed for copying across drives when exporting results or File Encryption output. |
| `io` | **Not needed yet.** Needed for streaming (`BufferedReader` / `BytesIO`) in File Encryption. |
| `unittest` | **Not needed.** pytest also runs unittest-style tests. `scripts/offline_selfcheck.py` and `scripts/check_dependencies.py` already run with no test framework at all. |

---------------------------------------------------------------------------------------------------

## 3. Why each library is used and how

### 3.1 cryptography (the only cryptographic dependency)
Used in `core/crypto_engine.py`: `AESGCM`, `PBKDF2HMAC`, `InvalidTag`. Nothing is implemented by hand.

**AES modes - why GCM is the default**

| Mode | Authentication? | Needs | Problem |
|---|---|---|---|
| ECB | no | nothing | identical blocks give identical ciphertext: leaks patterns. **Never use.** |
| CBC | no | unpredictable IV + padding | modification is not detected; padding-oracle attacks; needs a separate HMAC (encrypt-then-MAC). |
| CTR | no | unique nonce | an attacker can flip bits in the plaintext undetected; nonce reuse is catastrophic. |
| **GCM** | **yes (16-byte tag)** | unique 96-bit nonce | nonce reuse with the same key is catastrophic -> CipherLab uses a fresh random nonce, and a fresh random salt (so a fresh key) per message. |

AES-128, AES-192 and AES-256 differ only in key size (16, 24, 32 bytes). CipherLab supports all three in raw-key mode and
AES-256 in password mode. `AESGCM.decrypt` verifies the tag **before** returning plaintext; a wrong key or modified data raises
`InvalidTag`, which the application turns into one safe error. The container header (cipher, KDF, iterations, salt, nonce) is
bound to the ciphertext as authenticated associated data.

**Key derivation.** PBKDF2-HMAC-SHA256 with 600,000 iterations (configurable 100k-5M) is implemented. **scrypt is not
implemented**; `cryptography.hazmat.primitives.kdf.scrypt.Scrypt` is already in the installed package, so adding it needs no new
dependency. scrypt is memory-hard (costly for GPU/ASIC attackers); PBKDF2 is the more widely certified choice. Pick one
per container format and store the parameters in the authenticated header.

**Limits worth knowing:** random 96-bit nonces are safe up to about 2^32 messages per key; one GCM message is limited to
about 64 GiB. For big files use chunked encryption (section 3.5).

### 3.2 secrets, hashlib, hmac
* **`secrets`** reads the operating system's cryptographically secure generator. `random` is a Mersenne Twister: after
  observing 624 outputs an attacker can predict all later ones, so it must never produce passwords, salts, nonces or tokens.
  A future Password Generator needs only `secrets.choice` over an alphabet (entropy = length x log2(alphabet size)).
* **`hashlib`** gives SHA-256/512 (hash tool). A plain hash is **not** a password-based key derivation function: it is extremely
  fast (billions of guesses per second on a GPU), has no salt and no cost parameter. PBKDF2/scrypt exist to be slow and salted.
* **`hmac`** computes message authentication codes and `compare_digest` compares them in constant time (never use `==` on tags).
  **Where HMAC helps:** authenticating data that is *not* encrypted (exports, file checksums with a secret), key derivation
  constructions, legacy CBC/CTR designs. **Where AES-GCM already authenticates:** everything it encrypts, so adding HMAC on top
  of GCM adds nothing. CipherLab exposes HMAC as a user tool in the Encrypt tab.

### 3.3 Encoding and processing modules
* `binascii` / `base64`: `core/encodings.py` (strict Base64 with clear errors) and `models/crypto_envelope.py` (Base64 fields of the container).
* `json`: the encrypted container, metadata, settings, history parameters, JSON string escapes, comparison export.
* `re`: input validation and log redaction. Hex validation itself is a hand-written scanner (`core/xor_cipher.py`, `utils/validation.py`) so that error messages can name the exact character and position.
* `codecs`, `struct`, `textwrap`: see 2.3.

### 3.4 GUI (PySide6, unchanged)
The framework is kept: **PySide6**, installed as `PySide6-Essentials`. Needs from your list, and the Qt classes that cover them (the number is how often the class name appears in the source):

| Need | Qt class (uses) |
|---|---|
| Tabs | `QTabWidget` (6) |
| Text input / password fields | `QPlainTextEdit` (10), `QLineEdit` with `EchoMode.Password` (30) |
| Buttons, options | `QPushButton` (52), `QCheckBox` (24), `QComboBox` (33), `QSpinBox` (15) |
| Progress bars | `QProgressBar` (6) + `QThreadPool` / `QRunnable` (background work) |
| Dialogs, error messages | `QMessageBox` (15) |
| File selection | `QFileDialog` (9) |
| Clipboard | `QApplication.clipboard()` |
| Tables, panes | `QTableWidget` (14), `QSplitter` (21), `QTextBrowser` (2) |
| Settings | **not** `QSettings`: a JSON file in the app data folder (no registry, fully inspectable) |

No Qt module outside Essentials is imported; `tests/test_dependencies.py` fails if one is added.

### 3.5 File libraries and how they cooperate (design for File Encryption; not implemented)
`pathlib` (paths, suffix, `is_file`) -> `tempfile.mkstemp` in the **same folder** as the target (created `0600`, so no other user can read
partial output) -> `io` buffered streams, reading fixed-size chunks (e.g. 1 MiB) -> `cryptography` encrypts each chunk -> write the chunk ->
`os.replace` swaps the finished temp file into place atomically (the existing `core/file_handler.py` already uses this pattern for exports)
-> on failure delete the temp file -> `shutil` only for cross-drive copy/move. A binary header written with `struct` (magic, version, KDF id,
parameters, salt, chunk size) is authenticated as associated data; each chunk uses a nonce built from a random prefix plus a counter, and the
last chunk is flagged so truncation is detected. Never keep the plaintext in an intermediate file on disk.

### 3.6 Analysis and comparison
No extra library gives a genuine benefit. Byte analysis, XOR, frequency analysis, Hamming distance and entropy are implemented with
`collections.Counter`, `math` and Python's big-integer XOR. For a future byte-by-byte diff in Compare Results use the standard
`difflib.SequenceMatcher` or a simple zip-compare.

---------------------------------------------------------------------------------------------------

## 4. Testing strategy (pytest, unittest, coverage)

* **pytest** is the runner (parametrisation and fixtures). **unittest** is not needed. **coverage** measures what the tests execute.
* Run: `python -m pytest` (508 tests). Coverage: `python -m coverage run -m pytest && python -m coverage report`.
* Measured coverage (branch coverage on): **87 % overall** (2957 statements). By area: core **94 %**, models 95 %, utils **100 %**, GUI 84 %. (The logging module was 39 % before the new tests.)

| Your test topic | Covered by | Status |
|---|---|---|
| AES-128 / 192 / 256 | `test_crypto_engine` (16/24/32-byte keys, password mode AES-256) | covered |
| AES-GCM authentication, modified ciphertext, modified header | `test_tampered_ciphertext_and_header_fail` | covered |
| Incorrect passwords | `test_wrong_password_fails_safely` | covered |
| Invalid HEX / Base64 | `test_encodings`, `test_hex_analyzer`, `test_xor_cipher` | covered |
| Unicode, Persian, emoji | `test_encodings`, `test_crypto_engine`, `test_xor_cipher`, GUI tests | covered |
| Empty input | all core test files | covered |
| Invalid file formats / invalid container | `test_file_handler`, `test_invalid_metadata_rejected` | covered |
| Resource limits, decompression bomb | `test_resource_limits`, `test_decompression_bomb_is_bounded` | covered |
| Offline behaviour, no network imports | `test_offline_behavior` | covered |
| Logging never leaks secrets | `test_logging` (13 tests) | covered |
| Requirements match imports | `test_dependencies` | covered |
| **Large files** | only size limits and a ~400 KB XOR round trip | **gap**: no multi-hundred-MB test, because File Encryption does not exist yet |

---------------------------------------------------------------------------------------------------

## 5. Safe logging

* Only the standard `logging` module is used. `setup_logging()` writes a rotating file `cipherlab.log` (256 KB, 2 backups) in the app data folder; if the folder is not writable it silently logs nowhere.
* **The application contains exactly one log call** (`gui/context.py`): `log.debug("task failed: %s", type(exc).__name__)`. It records the exception *type*, never its message. The core modules contain no logging at all (a test proves nothing is logged during encrypt/decrypt/analysis).
* `RedactingFilter` is the second line of defence: it masks values after `password`, `passphrase`, `secret`, `token`, `key`, `hmac_key` (including quoted values with spaces) and **replaces tracebacks with the exception type** (an exception message can contain anything the user typed).
* Rules for future code: never log arguments, plaintext, passwords, keys or decrypted text; log lengths and types instead; do not use `logger.exception` with user data nearby; keep the default level at INFO.
* Limit: regex redaction is best-effort. The real protection is not logging content in the first place.

---------------------------------------------------------------------------------------------------

## 6. Dependency inspection results

| Question | Answer |
|---|---|
| Already installed (your Windows venv, from your pip log) | PySide6 6.12.0, PySide6_Essentials, PySide6_Addons, PySide6_WebEngine 6.12.0.140, PySide6_Pdf, shiboken6, cryptography 50.0.2, cffi 2.1.1, pycparser 3.12 |
| Missing | none for running the app. For tests: `pytest`, `coverage` (`pip install -r requirements-test.txt`) |
| **Unnecessary** | `PySide6` (meta), `PySide6_Addons`, `PySide6_WebEngine`, `PySide6_Pdf` (about 175 MB download, 448 MB on disk) |
| Duplicated | none; `scripts/check_dependencies.py` checks this automatically |
| Compatibility | no conflicts: `pip check` -> "No broken requirements found" |
| Outdated | `pip` (your log: 23.2.1 -> 26.2.2 available) |

---------------------------------------------------------------------------------------------------

## 7. Python version and compatibility

| Python | Verdict |
|---|---|
| 3.9 and older | **Not supported.** The code uses `int.bit_count()` (3.10+); PySide6 6.12 requires 3.10+. |
| 3.10 | Code runs in principle, but the pinned test set (`pycparser 3.12`, `coverage 7.17`) needs 3.11, and 3.10 reached end of life in October 2026. Not recommended. |
| 3.11 | Supported by every pinned package. **Not tested here.** |
| **3.12** | **Recommended. The only version the 508 tests were run on.** |
| 3.13, 3.14 | Allowed by all package metadata (PySide6 6.12 allows `<3.16`). **Not tested here.** |

Note: the `vermin` tool reported "3.9" for the source; it cannot see method calls on plain integers, so I checked by hand and found `int.bit_count()`
in `core/xor_tools.py` and `core/statistics.py`. Windows 7 cannot run Python 3.9 or newer; use Windows 10/11.

---------------------------------------------------------------------------------------------------

## 8. The requirements files

```
requirements.txt        RUNTIME   PySide6-Essentials>=6.6,<7 ; cryptography>=42
requirements-test.txt   TESTING   -r requirements.txt ; pytest>=8 ; coverage>=7
requirements-dev.txt    DEV       -r requirements-test.txt ; pyinstaller>=6
requirements-audit.txt  AUDIT     pip-audit>=2.7   (install in a SEPARATE venv: it brings an HTTP client)
constraints.txt         exact versions the suite was tested with (Python 3.11+); not a requirements file
```
* Ranges, not pins, in the requirements files, so security fixes can be installed; `constraints.txt` records the tested set for reproducible installs.
* The version floors are conservative choices, not measured limits: the primitives used (`AESGCM`, `PBKDF2HMAC`) are old and stable, and the Qt classes are basic. **Only the pinned versions in `constraints.txt` were tested, not the minimum versions.**
* No standard-library module is listed anywhere (enforced by `tests/test_dependencies.py`).

---------------------------------------------------------------------------------------------------

## 9. Installation commands

**Windows 10/11 (PowerShell or CMD), new environment**
```
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt -c constraints.txt
python main.py
```
If `files.pythonhosted.org` is unreachable (as on your network), add a mirror: `-i https://mirrors.aliyun.com/pypi/simple/`.
See section 11 for why a mirror deserves care.

**Linux**
```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -c constraints.txt
```

**Tests / development**
```
pip install -r requirements-test.txt -c constraints.txt        # pytest + coverage
python -m pytest
pip install -r requirements-dev.txt -c constraints.txt         # + pyinstaller
```

**Migrating an existing environment from `PySide6` to `PySide6-Essentials`** (no new venv needed)
```
pip uninstall -y PySide6 PySide6_Addons PySide6_WebEngine PySide6_Pdf
pip install --force-reinstall --no-deps PySide6-Essentials
pip check
python -c "import PySide6; print(PySide6.__version__)"
```
**Do not skip the second line.** The four packages share files: Addons, WebEngine and Pdf each also list `PySide6/__init__.py` and
`_config.py`, so uninstalling them removes files `PySide6` needs (on Windows `__init__.py` also registers Qt's DLL folder). The reinstall
restores them. pip may reuse its cached wheel instead of downloading 82 MB again ("Using cached ..."). Tested on Linux: after these
steps `pip check` is clean and `import PySide6` works.

---------------------------------------------------------------------------------------------------

## 10. Offline installation guide

CipherLab never uses the network at runtime. The only online step is downloading the packages once.

1. **Download in advance** (on a computer with internet; same OS / CPU / Python as the target):
   ```
   python -m pip download -r requirements-dev.txt -c constraints.txt -d wheelhouse
   ```
   Runtime only: use `requirements.txt`. For **another operating system** (verified: Windows wheels from Linux):
   ```
   python -m pip download --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 \
       --only-binary=:all: -r requirements.txt -c constraints.txt -d wheelhouse
   ```
   Result: 5 wheels, 84 MB (PySide6_Essentials 78 MiB, shiboken6, cryptography, cffi, pycparser).
2. **Store locally:** keep the `wheelhouse/` folder with the project (USB drive, internal share).
3. **Install without internet:**
   ```
   python -m venv .venv
   .venv/bin/pip install --no-index --find-links wheelhouse -r requirements.txt -c constraints.txt     (Windows: .venv\Scripts\pip.exe)
   ```
   `--no-index` makes pip refuse to contact any server.
4. **Verify it works offline:** disconnect the network, then `python scripts/offline_selfcheck.py` (expect `network attempts blocked: 0`),
   `python scripts/check_dependencies.py --strict`, `python -m pytest`. Stronger, Linux only: `unshare -rn <command>` runs it in a namespace with no network.
5. **Reinstall from the local folder** any time: repeat step 3 with `--force-reinstall` if needed.

**Verified:** in a sandbox where `socket.create_connection("pypi.org", 443)` fails, I created a fresh venv, installed from the local
wheelhouse with `--no-index`, `pip check` passed, the dependency checker and offline self-check passed, and the whole suite passed.
Not verified: the same procedure on Windows.

---------------------------------------------------------------------------------------------------

## 11. Security and dependency auditing

| Task | Command |
|---|---|
| Installed versions | `pip list` ; `pip show cryptography` |
| Conflicts | `pip check` |
| Outdated packages | `pip list --outdated` |
| Known vulnerabilities | in a **separate** venv: `pip install -r requirements-audit.txt`, then `pip-audit --path .venv/Lib/site-packages` (Linux: `.venv/lib/python3.12/site-packages`). Needs internet (it asks the PyPI advisory service); do it on a connected machine. |
| Code vs requirements | `python scripts/check_dependencies.py --strict` (offline) |
| Verify a downloaded file | `pip hash wheelhouse/<file>.whl` and compare with the hash on the package's PyPI "Download files" page |
| Reject tampering | hash-pinned install: `pip install --require-hashes -r requirements-hashes.txt`. Generate that file on the target OS with `pip-compile --generate-hashes` (package `pip-tools`; not included, because hashes are platform-specific). |

Practices:
* **Official source:** install from `pypi.org`. Check the project page and maintainers (cryptography: the PyCA project; PySide6: the "Qt for Python" project of the Qt Group). Beware look-alike names (typosquatting): the correct names are exactly `cryptography` and `PySide6-Essentials`.
* **Mirrors:** you installed through `mirrors.aliyun.com`. A mirror is a third party that could in principle serve different files than PyPI. For cryptographic software, prefer `pypi.org`, or compare the file hashes with PyPI, or reinstall from PyPI once your connection allows.
* **Keep `pip` current:** `python -m pip install --upgrade pip`. The audit flagged 12 advisories in pip 24.0 (fixed in 26.2); your 23.2.1 is older, so it is at least as exposed (I audited 24.0, not 23.2.1).
* **Update cryptography regularly:** it receives security fixes often. Monthly: `pip list --outdated`, upgrade, run `python -m pytest`, then update `constraints.txt`.
* Never install anything from a random URL or an unsigned archive; keep the application environment free of network libraries (`tests/test_offline_behavior.py` enforces it).

---------------------------------------------------------------------------------------------------

## 12. Dependency structure

```
CipherLab Pro (main.py, src/)
|-- RUNTIME  (requirements.txt)
|   |-- PySide6-Essentials 6.12.0        QtCore, QtGui, QtWidgets only
|   |   `-- shiboken6 6.12.0
|   `-- cryptography 50.0.2              AESGCM, PBKDF2HMAC
|       `-- cffi 2.1.1 -> pycparser 3.12
|-- TESTING  (requirements-test.txt)  = runtime +
|   |-- pytest 9.2.0 -> pluggy, iniconfig, packaging, Pygments
|   `-- coverage 7.17.0
|-- DEV      (requirements-dev.txt)   = testing +
|   `-- pyinstaller 6.22.3 -> altgraph, pyinstaller-hooks-contrib, setuptools
|-- AUDIT    (requirements-audit.txt)   separate venv
|   `-- pip-audit 2.10.1 (+ its own HTTP client)
`-- STANDARD LIBRARY (nothing to install): hashlib hmac secrets json re base64 binascii pathlib os tempfile
    sqlite3 logging zlib bz2 lzma dataclasses ... (full table in 2.2)
```

---------------------------------------------------------------------------------------------------

## 13. What was not verified

* Everything was run on **Linux with Python 3.12 only**. Windows, Python 3.11/3.13/3.14 are expected to work from package metadata but were not run.
* The **PyInstaller** build was not run (the scripts exist; `scripts/build_exe.*`).
* The Aliyun mirror's file integrity was not checked.
* File Encryption, File Decryption and the Password Generator are not implemented; section 3.5 is a design note.
* `pip-audit` reflects the advisory database at the time it ran.
