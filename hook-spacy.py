# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# HOOK FILE FOR SPACY
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import collect_data_files

# ----------------------------- SPACY -----------------------------
data = collect_all('spacy')

datas = data[0]
binaries = data[1]
hiddenimports = data[2]

# ----------------------------- THINC -----------------------------
data = collect_all('thinc')

datas += data[0]
binaries += data[1]
hiddenimports += data[2]

# ----------------------------- CYMEM -----------------------------
data = collect_all('cymem')

datas += data[0]
binaries += data[1]
hiddenimports += data[2]

# ----------------------------- PRESHED -----------------------------
data = collect_all('preshed')

datas += data[0]
binaries += data[1]
hiddenimports += data[2]

# ----------------------------- SYLLAPY -----------------------------
data = collect_all('syllapy')

datas += data[0]
binaries += data[1]
hiddenimports += data[2]

# ----------------------------- BLIS -----------------------------

data = collect_all('blis')

# ----------------------------- OTHER ----------------------------

hiddenimports += ['srsly.msgpack.util']


# ----------------------------- Sacy Model -------------------------
datas += collect_data_files("en_core_web_sm")
datas += collect_data_files("de_core_news_sm")

datas += data[0]
binaries += data[1]
hiddenimports += data[2]
# This hook file is a bit of a hack - really, all of the libraries should be in seperate hook files. (Eg hook-blis.py with the blis part of the hook)

# include resources
datas.extend([
    ('tracra_resources', 'tracra_resources'),
    #('src/lemmatization', 'lemmatization'),
    #('src/stop_word_lists', 'stop_word_lists'),
    #('src/wl_acks', 'wl_acks'),
    #('LICENSE.txt', '.')
    ])
