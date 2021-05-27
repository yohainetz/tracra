import os
import sys
from pathlib import Path
import platform

from py_singleton import singleton

@singleton
class ResourceManager:

    def get_res_path(self, partial_path):
        if isinstance(partial_path,str):
            partial_path = [partial_path]
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            bundle_dir = Path(sys._MEIPASS)
        else:
            bundle_dir = Path(__file__).parent

        return os.path.join(Path.cwd(), bundle_dir, *partial_path)

        if getattr(sys, 'frozen', False) and False:
            # If the application is run as a bundle, the PyInstaller bootloader
            # extends the sys module by a flag frozen=True and sets the app
            # path into variable _MEIPASS'.
            # application_path = sys._MEIPASS
            lastind = sys.executable.rindex("tracra_guimain")
            curpath = sys.executable[:lastind]
            application_path = os.path.join(curpath)
            return os.path.join(".",*partial_path)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
            #application_path = os.path.join(sys.executable,"..")
        return os.path.join(application_path, *partial_path)

    def get_write_path(self,destname):
        if platform.system() == "Windows":
            return os.path.join(Path.cwd(), destname)
        else:
            return os.path.join(Path(__file__).parent.parent.parent.parent, destname)