# Email Tracking Crawler

## Setup

Developed and tested using Python 3.8. 
Install requirements via PIP `pip install -r requirements.txt`. I recommend using [Anaconda](https://www.anaconda.com). 

Fetch spacy models via `spacy download de_core_news_sm` and `spacy download en_core_web_sm`.

**Resources**: Download archive from https://studie.jschaeffer.de/media/downloads/tracra/tracra_resources.zip and unzip as `tracra_resources` in this directory. It contains alexa and tranco lists, tracking protection lists etc.

**Launch** tool via `python tracra_guimain.py` and enter name, forename, email, password. You can navigate in the forms using arrow keys, tab, enter. After you've checked the server settings, the tool will fetch mails via imap and analyze them.
_Make sure your mail server allows IMAP access._ 

Output is written to `output.xlsx`

**OS specific instructions**

On Windows you my need to install `pip install windows-curses`. 

To install package `editdistance` on OSX Intel (not M1) set build flag `export ARCHFLAGS="-arch x86_64"` before running `pip install`.


## build self contained binary

Install PyInstaller `python -m pip install PyInstaller`

`pyinstaller --name="Tracra" --windowed --hidden-import cmath --additional-hooks-dir=. --clean tracra_guimain.py`

### build on windows 

Download wheel for `pycld2` from `https://www.lfd.uci.edu/~gohlke/pythonlibs/#pycld2` and install using `pip install pycld****.whl`

`pyinstaller --name="Tracra" --onefile --windowed --hidden-import cmath --additional-hooks-dir=. --clean tracra_guimain.py`
