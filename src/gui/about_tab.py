"""About tab: developer credit, full description of CipherLab Pro and a user guide (English only)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QTextBrowser, QVBoxLayout

from src.core.settings import get_data_dir
from src.gui.theme import palette
from src.gui.widgets import BaseTab

APP_VERSION = "1.0"


def build_html() -> str:
    """Return the About / user-guide document as rich text."""
    p = palette()
    ACCENT, TEXT = p["ACCENT"], p["TEXT"]
    h = f'style="color:{ACCENT}; margin-top:18px;"'
    th = f'bgcolor="{p["PANEL"]}" style="color:{ACCENT};"'
    data_dir = str(get_data_dir())
    return f"""
<h2 {h}>1. Overview</h2>
<p><b>CipherLab Pro</b> is a desktop application for encoding, decoding, encryption, hashing, hexadecimal
analysis and local cryptographic experiments. It is written in Python with PySide6 (Qt) and the maintained
<code>cryptography</code> library, and it runs entirely on your own computer.</p>
<p>Typical uses: converting text between encodings; protecting a message with AES-256-GCM and a password;
inspecting unknown hexadecimal data; learning how XOR obfuscation works and how statistical analysis can
recover it; computing SHA-256 / SHA-512 hashes and HMAC tags.</p>

<h2 {h}>2. Key Features</h2>
<ul>
<li><b>Encoding and decoding:</b> UTF-8, UTF-16, ASCII, Latin-1, Hexadecimal, Base64, URL (percent) encoding,
Unicode escape sequences, JSON string escaping, binary and decimal byte representations.</li>
<li><b>Encryption:</b> AES-256-GCM with a password (PBKDF2-HMAC-SHA256), AES-GCM with a raw hexadecimal key,
SHA-256 / SHA-512 hashing, HMAC, and repeating-key XOR for educational purposes.</li>
<li><b>Hex Analyzer:</b> input validation, entropy and byte statistics, encoding checks, file-signature and
compression detection, nested-encoding detection, XOR analysis and a ranked, explained list of candidates.</li>
<li><b>XOR Encoder and Decoder:</b> repeating-key XOR with a custom hexadecimal password of any length.</li>
<li><b>XOR Analyzer:</b> key-length ranking, single-byte and bounded repeating-key analysis, XOR with a known key.</li>
<li><b>Compare Results:</b> candidates side by side, with JSON export.</li>
<li><b>History and Settings:</b> optional local history and configurable limits.</li>
<li><b>Unicode support:</b> English, Persian, Arabic, emoji and any other Unicode text.</li>
<li><b>File handling:</b> import and export of TXT, HEX, JSON and binary files, with drag and drop.</li>
<li><b>Responsive interface:</b> long operations run in the background with a progress bar and a Cancel button.</li>
</ul>

<h2 {h}>3. Privacy and Offline Guarantee</h2>
<ul>
<li>No network connections, no accounts, no telemetry, no update checks and no cloud synchronization.</li>
<li>No AI services or external APIs. Analysis uses deterministic local algorithms with explainable scoring.</li>
<li>Passwords and keys are never written to history, settings or log files.</li>
<li>Internet access is only needed once, at installation time, to download the required Python packages.</li>
</ul>

<h2 {h}>4. Quick Start</h2>
<ol>
<li>Choose a tab at the top of the window.</li>
<li>Type or paste your input into the left editor, or drag a file onto it.</li>
<li>Select the options (format, algorithm, key) above the editors.</li>
<li>Press the main button (Encode, Decode, Run, Analyze) or press <b>Ctrl+Enter</b>.</li>
<li>Read the result on the right. Use <b>Copy</b> or <b>Export</b> to keep it.</li>
</ol>

<h2 {h}>5. User Guide: The Tabs</h2>
<table border="1" cellspacing="0" cellpadding="6" width="100%">
<tr><th {th}>Tab</th><th {th}>Purpose</th><th {th}>How to use it</th></tr>
<tr><td><b>Encode</b></td><td>Convert text into another representation.</td>
<td>Enter text, choose the text encoding and the output format, then press Encode. Characters that the chosen
encoding cannot represent are reported, never silently dropped.</td></tr>
<tr><td><b>Decode</b></td><td>Convert an encoded string back to bytes and text.</td>
<td>Paste the encoded text, choose its format and how the bytes should be interpreted, then press Decode.
Strict mode reports invalid bytes. If the bytes are not valid text, the raw bytes are shown as hexadecimal.
Suggest format lists the formats the input could be written in.</td></tr>
<tr><td><b>Encrypt</b></td><td>Encrypt a message or compute a hash or HMAC.</td>
<td>Choose an algorithm, enter the password or key, and press Run. AES output is a JSON container that includes
everything needed for decryption except the password or key.</td></tr>
<tr><td><b>Decrypt</b></td><td>Decrypt AES-GCM containers and XOR data.</td>
<td>Paste the container, enter the password or key and press Decrypt. A wrong password or modified data
produces a safe error message and no output.</td></tr>
<tr><td><b>XOR Encoder</b></td><td>Encrypt text with a custom HEX password (repeating-key XOR).</td>
<td>Type the plaintext, enter any hexadecimal password (with or without 0x), choose the output style and press Encrypt. The result is HEX. The status line shows the exact key bytes that will be used.</td></tr>
<tr><td><b>XOR Decoder</b></td><td>Restore the text from XOR-encrypted HEX.</td>
<td>Paste the HEX output, enter the same password and press Decrypt. The bytes are decoded as UTF-8. A wrong password gives different bytes; if they are not valid UTF-8 they are shown as hexadecimal.</td></tr>
<tr><td><b>Hex Analyzer</b></td><td>Analyze unknown hexadecimal data.</td>
<td>Paste hexadecimal text and press Analyze. Spaces, colons, dashes, commas, 0x and \\x prefixes are accepted.
Odd length and invalid characters are reported. Optionally include repeating-key XOR analysis.</td></tr>
<tr><td><b>XOR Analyzer</b></td><td>Study XOR-obfuscated data.</td>
<td>Choose single-byte or repeating-key analysis, or enter a known key and press Apply key.</td></tr>
<tr><td><b>Compare Results</b></td><td>Compare candidate interpretations.</td>
<td>Use Send selected to Compare in an analyzer tab. Each candidate becomes a column. Export the comparison as JSON.</td></tr>
<tr><td><b>History</b></td><td>Review recent operations.</td>
<td>Search, delete selected records, clear everything, or switch recording off.</td></tr>
<tr><td><b>About</b></td><td>Information and this guide.</td><td>Read only.</td></tr>
<tr><td><b>Settings</b></td><td>Configure the application.</td>
<td>Set history options, file-size limit, PBKDF2 iterations, default text encoding and Persian scoring.
Press Save settings to apply.</td></tr>
</table>
<p>Every editor has <b>Paste</b>, <b>Copy</b>, <b>Clear</b>, <b>Import</b> and <b>Export</b> buttons.
Right-to-left languages such as Persian and Arabic are displayed correctly.</p>

<h2 {h}>6. Step-by-Step Tutorials</h2>
<h3 style="color:{TEXT};">6.1 Encode and decode text</h3>
<ol>
<li>Open <b>Encode</b>, type <code>Hello, world!</code>, select UTF-8 and Hexadecimal, and press Encode.
The result is <code>48 65 6c 6c 6f 2c 20 77 6f 72 6c 64 21</code>.</li>
<li>Copy the result and open <b>Decode</b>.</li>
<li>Paste it, select Hexadecimal as input format and UTF-8 as the interpretation, and press Decode.</li>
</ol>
<h3 style="color:{TEXT};">6.2 Encrypt and decrypt a message with a password</h3>
<ol>
<li>Open <b>Encrypt</b>, select <i>AES-256-GCM (password)</i>, type the message and a password, and press Run.</li>
<li>Copy the JSON container that appears and store it anywhere you like.</li>
<li>Open <b>Decrypt</b>, paste the container, enter the same password and press Decrypt.</li>
</ol>
<p>There is no password recovery. If the password is lost, the data cannot be decrypted.</p>
<h3 style="color:{TEXT};">6.3 Analyze unknown hexadecimal data</h3>
<ol>
<li>Open <b>Hex Analyzer</b> and paste the hexadecimal text.</li>
<li>Press Analyze and read the report on the left: byte count, entropy, encoding checks, signatures, warnings.</li>
<li>Select a candidate in the table to see its score, confidence and the reasons for its rank.</li>
<li>Check the verdict. If it says <b>INCONCLUSIVE</b>, no interpretation could be established with confidence.</li>
</ol>
<h3 style="color:{TEXT};">6.4 Experiment with XOR</h3>
<ol>
<li>In <b>Encrypt</b>, select the XOR algorithm, enter a long English sentence and a short key, and press Run.</li>
<li>Copy the hexadecimal result into <b>XOR Analyzer</b>, keep Hexadecimal input, and press Analyze.</li>
<li>Compare the best candidate with your original text. Longer texts give more reliable results.</li>
</ol>

<h3 style="color:{TEXT};">6.5 XOR Encoder and Decoder with your own HEX password</h3>
<ol>
<li>Open <b>XOR Encoder</b>, type or paste the text (any language, emoji included).</li>
<li>Enter a hexadecimal password of any length, for example <code>0xA1B2C3</code>, <code>00ff10</code> or <code>474</code>. Leading zeros are kept: <code>0001</code> is two bytes. An odd digit count is read as a number (<code>0x474</code> = <code>04 74</code>); turn on Strict mode to reject odd lengths instead.</li>
<li>Press Encrypt and copy the HEX result.</li>
<li>Open <b>XOR Decoder</b>, paste the HEX, enter exactly the same password and press Decrypt.</li>
</ol>
<h2 {h}>7. Understanding Analysis Results</h2>
<p>Each candidate has <b>score = quality x prior</b>.</p>
<ul>
<li><b>Quality (0 to 1)</b> measures how text-like or structurally valid the output is, using printable-character
share, letter frequencies (English, and optionally Persian) and structural evidence such as a valid compressed stream.</li>
<li><b>Prior</b> expresses how plausible the method is by itself. Methods that can succeed by accident, such as XOR or
Latin-1, receive lower priors.</li>
<li><b>Confidence</b> is none (below 0.35), low (below 0.60), medium (below 0.80) or high. It is capped for guess-based
methods and for short samples.</li>
</ul>
<p>Readable output from a guessed key is evidence, not proof. The analyzer never claims to decrypt data without the
correct algorithm and key.</p>

<h2 {h}>8. Keyboard Shortcuts</h2>
<table border="1" cellspacing="0" cellpadding="6" width="60%">
<tr><th {th}>Shortcut</th><th {th}>Action</th></tr>
<tr><td>Ctrl+Enter</td><td>Run the current tab</td></tr>
<tr><td>Ctrl+L</td><td>Clear the current tab</td></tr>
<tr><td>Ctrl+O</td><td>Import a file into the input editor</td></tr>
<tr><td>Ctrl+S</td><td>Export the output</td></tr>
<tr><td>Ctrl+1 to Ctrl+9</td><td>Switch to tabs 1 to 9</td></tr>
<tr><td>Ctrl+0</td><td>Switch to tab 10 (History)</td></tr>
<tr><td>Ctrl+Shift+1, Ctrl+Shift+2</td><td>Switch to tab 11 (About) and tab 12 (Settings)</td></tr>
<tr><td>Ctrl+Q</td><td>Quit</td></tr>
</table>

<h2 {h}>9. Security Notes and Limitations</h2>
<ul>
<li>Encoding (Base64, hexadecimal, URL), hashing (SHA, HMAC) and encryption (AES-GCM) are different things.
Only encryption hides data.</li>
<li>XOR with a repeating key is not secure. It is included for learning only.</li>
<li>AES-GCM uses a fresh random salt and nonce for every message. Any change to the encrypted data is detected.</li>
<li>Plaintext shown on screen, copied to the clipboard or exported is not protected by the application.</li>
<li>The history database is not encrypted. It never stores passwords or keys, and it keeps no content for
encrypt, decrypt and HMAC operations.</li>
<li>Python cannot reliably erase secrets from memory. Use a trusted computer.</li>
<li>The built-in Persian letter-frequency table is approximate. A custom table can be supplied in Settings.</li>
</ul>

<h2 {h}>10. Troubleshooting</h2>
<table border="1" cellspacing="0" cellpadding="6" width="100%">
<tr><th {th}>Message or symptom</th><th {th}>Meaning and solution</th></tr>
<tr><td>Odd number of hexadecimal digits</td><td>Every byte needs two digits. Add or remove one digit.</td></tr>
<tr><td>Invalid hexadecimal character</td><td>Only 0-9, a-f and the separators space, colon, dash, comma and underscore are allowed.</td></tr>
<tr><td>Decryption failed</td><td>The password or key is wrong, or the encrypted data was modified.</td></tr>
<tr><td>Not a valid CipherLab Pro container</td><td>Paste the complete JSON produced by the Encrypt tab, without changes.</td></tr>
<tr><td>Bytes are not valid UTF-8</td><td>The data is not text in that encoding. Choose another encoding or view the raw hexadecimal.</td></tr>
<tr><td>File is too large</td><td>Increase the import limit in Settings, or use a smaller file.</td></tr>
<tr><td>Result is INCONCLUSIVE</td><td>The data is too short, random, or encrypted with an unknown method. This is a valid outcome.</td></tr>
</table>

<h2 {h}>11. Technical Information</h2>
<table border="1" cellspacing="0" cellpadding="6" width="100%">
<tr><td><b>Version</b></td><td>{APP_VERSION}</td></tr>
<tr><td><b>Language and interface</b></td><td>Python 3.12, PySide6 (Qt)</td></tr>
<tr><td><b>Cryptography</b></td><td>AES-GCM and PBKDF2-HMAC-SHA256 from the <code>cryptography</code> package; hashing and HMAC from the Python standard library</td></tr>
<tr><td><b>Encrypted format</b></td><td>CipherLabPro, version 1 (authenticated JSON container)</td></tr>
<tr><td><b>Storage</b></td><td>settings.json, history.db (SQLite) and cipherlab.log, kept locally</td></tr>
<tr><td><b>Data folder</b></td><td><code>{data_dir}</code></td></tr>
</table>

<h2 {h}>12. Developer</h2>
<p>CipherLab Pro was designed and developed by <b>Taha Zohrabi</b>, programmer, Shiraz, Iran.</p>
"""


class AboutTab(BaseTab):
    title = "About"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.place = QLabel("IRAN  \u00b7  SHIRAZ")
        self.name = QLabel("TAHA ZOHRABI")
        self.role = QLabel("Programmer")
        self.subtitle = QLabel(f"CipherLab Pro  v{APP_VERSION}  \u2022  Offline encoding, cryptography and analysis toolkit")
        for label in (self.place, self.name, self.role, self.subtitle):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        for w in (self.place, self.name, self.role, self.subtitle, self.line):
            layout.addWidget(w)
        layout.addWidget(self.browser, 1)
        self.apply_theme()

    def apply_theme(self) -> None:
        """Re-colour the header and the document for the active theme."""
        p = palette()
        self.place.setStyleSheet(f"color:{p['ACCENT']}; font-size:34px; font-weight:700; letter-spacing:4px;")
        self.name.setStyleSheet(f"color:{p['ACCENT']}; font-size:46px; font-weight:700;")
        self.role.setStyleSheet(f"color:{p['MUTED']}; font-size:15px;")
        self.subtitle.setStyleSheet(f"color:{p['TEXT']}; font-size:14px;")
        self.line.setStyleSheet(f"color:{p['BORDER']}; background:{p['BORDER']}; max-height:1px;")
        self.browser.setHtml(build_html())

    def run(self) -> None:
        """Nothing to run on the About page."""
