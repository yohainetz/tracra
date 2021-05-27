from urllib.parse import urlparse

from bs4 import BeautifulSoup
from hashed_helper import HashHelper
from tqdm import tqdm
import glob


def params(url):
    params = []
    for paramPair in list(filter(None, urlparse(url).query.split("&"))):
        paramKey, paramValue = None, None
        paramArr = paramPair.split("=")
        paramKey = paramArr[0]
        if len(paramArr) > 1:
            paramValue = paramArr[1]
        params.append((paramKey, paramValue))
    return params

MSG_FILES_PATH = "/Users/jschaeffer/Downloads/emails/html/"

folders = glob.glob(MSG_FILES_PATH + "*")

for folder in tqdm(folders):
    email_addr = folder.split("/")[-1]
    mails = glob.glob(folder + "/*.html")
    for mailfile in mails:
        try:
            with open(mailfile,"r") as mf:
                soup = BeautifulSoup(mf, 'html.parser')
                res_list = []
                for link in soup.find_all('a'):
                    location = link.get('href', None)
                    if location is None:
                        continue
                    if location.strip() == "":
                        continue
                    if location[0] == "#":
                        continue
                    paramList = params(location)

                    hh = HashHelper()
                    res_list += [hh.hashed(email_addr, p[1]) for p in paramList]
                res_list = list(filter(lambda p: p is not None, res_list))
                res_list = list(filter(lambda p: 'urlencoded_quote' not in p, res_list))
                res_list = list(filter(lambda p: 'plain' not in p, res_list))

                if len(res_list) > 1:
                    print("Found in ",mailfile, ": ", str(res_list))
                    pass
        except:
            #print("Error on ", mailfile)
            pass
