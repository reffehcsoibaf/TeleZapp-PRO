# -*- mode: python ; coding: utf-8 -*-
# O programa (pasta com TeleZapp.exe). Gerado por ferramentas/empacotar.py.
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

RAIZ = os.path.abspath(os.path.join(SPECPATH, "..", ".."))

datas = [(os.path.join(RAIZ, "telezapp", "ajuda"), "telezapp/ajuda"),
         (os.path.join(RAIZ, "telezapp", "sons"), "telezapp/sons"),
         (os.path.join(RAIZ, "telezapp", "imagens"), "telezapp/imagens")]
ICONE = os.path.join(RAIZ, "telezapp", "imagens", "telezapp.ico")
binaries = []
hiddenimports = []
# Extensoes (extensoes\<nome>\extensao.py): sao carregadas por caminho em
# tempo de execucao, entao vao como arquivos, sem testes nem __pycache__.
EXT = os.path.join(RAIZ, "extensoes")
if os.path.isdir(EXT):
    for pasta, subs, arqs in os.walk(EXT):
        subs[:] = [s for s in subs if s not in ("__pycache__", "testes", ".git")]
        for arq in arqs:
            if arq.endswith((".pyc", ".bat", ".md")):
                continue
            rel = os.path.relpath(pasta, RAIZ)
            datas.append((os.path.join(pasta, arq), rel))
# modulos da biblioteca padrao que as extensoes usam e o PyInstaller nao ve
hiddenimports += ["sqlite3", "mimetypes", "glob", "shutil", "subprocess",
                  "unicodedata", "xml.sax.saxutils", "csv", "ctypes.wintypes"]
hiddenimports += collect_submodules("telethon")
hiddenimports += collect_submodules("hachoir")
hiddenimports += collect_submodules("telezapp")
for pacote in ("neonize", "magic", "pyzipper", "accessible_output2", "cv2",
               "emoji", "av", "livekit", "truststore",
               # Windows Hello da protecao ao entrar
               "winrt"):
    d, b, h = collect_all(pacote)
    datas += d
    binaries += b
    hiddenimports += h
hiddenimports += collect_submodules(
    "Cryptodome", filter=lambda n: "SelfTest" not in n)
# os aplicativos de robo: o wx carrega estas DLLs sozinho, em tempo de execucao
hiddenimports.append("wx.html2")
import wx
import glob
_wxdir = os.path.dirname(wx.__file__)
binaries += [(c, "wx") for c in
             glob.glob(os.path.join(_wxdir, "WebView2Loader.dll")) +
             glob.glob(os.path.join(_wxdir, "wxmsw*u_webview_vc140_x64.dll"))]

a = Analysis(
    [os.path.join(SPECPATH, "iniciar.py")],
    pathex=[RAIZ], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=[], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="TeleZapp PRO",
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False, disable_windowed_traceback=False,
          icon=ICONE, version=os.environ.get("TELEZAPP_VERSAO"))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               upx_exclude=[], name="TeleZapp PRO")
