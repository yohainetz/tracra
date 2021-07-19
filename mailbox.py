from threading import Thread

from imap_tools import MailBox, AND, MailMessageFlags
from mailanalyzeobject import MailAnalyzeObject
import xml.etree.ElementTree as ET
import urllib.request
from lxml import etree
from collections import defaultdict
from tqdm import tqdm
import logging
from domainhelper import DomainHelper
from PyQt5.QtCore import QThread, pyqtSignal, QObject


class MailboxAnalyzeObject(QThread):
    _pbar_val_signal = pyqtSignal(int)
    _pbar_val_update_signal = pyqtSignal(int)
    _pbar_init_signal = pyqtSignal(str, str, int)
    _pbar_finished_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.folders = defaultdict(list)
        self.analyzed_mails = []
        self.email = None
        self.login = None
        self.forename = None
        self.lastname = None
        self.name_aliases = []
        self.sender_count = defaultdict(int)
        self.mailcounter = 0
        self.email_aliases = []
        self.link_counter = 0
        self.tracking_senders = defaultdict(lambda: defaultdict(int))
        self.additional_meta_infos = {"skipped_mails": 0}

    def set_email(self, email):
        self.email = email.lower()

    def add(self, foldername, msg_list):
        self.folders[foldername] = msg_list

    def all_msgs(self):
        return [msg for folder in self.folders.values() for msg in folder]

    def count(self, func):
        return len(filter(lambda x: func(x), self.all_msgs()))

    def count_in_folder(self, func, folder):
        pass

    def inferIMAPServer(self, email_address):
        txt_arr = email_address.split("@")
        domain = txt_arr[1]

        # try autonconfig

        username, hostname = "", ""
        try:
            if domain.startswith("aol."):
                username = email_address
                hostname = "imap.aol.com"
        except:
            pass
        try:
            url = 'http://autoconfig.' + domain + '/mail/config-v1.1.xml?emailaddress=' + email_address
            username, hostname = self.autodiscover(url)
            if username == "%EMAILADDRESS%":
                username = email_address
            elif username == "%EMAILLOCALPART%":
                username = email_address.split("@")[0]
            return username, hostname
        except Exception as e:
            logging.debug(e)

        try:
            url = "http://autoconfig." + domain + "/?emailaddress=" + email_address
            username, hostname = self.autodiscover(url)
            if username == "%EMAILADDRESS%":
                username = email_address
            elif username == "%EMAILLOCALPART%":
                username = email_address.split("@")[0]
            return username, hostname
        except Exception as e:
            logging.debug(e)
        # try thunderbird's ISPDB
        try:
            url = "https://autoconfig.thunderbird.net/v1.1/" + domain
            username, hostname = self.autodiscover(url)
            if username == "%EMAILADDRESS%":
                username = email_address
            elif username == "%EMAILLOCALPART%":
                username = email_address.split("@")[0]

            return username, hostname
        except Exception as e:
            logging.debug(e)

        return username, hostname

    def add_mail(self, msg, foldername):
        mail_id = "mail_" + str(self.mailcounter)
        try:
            self.mailcounter += 1
            mo = MailAnalyzeObject(msg, foldername, self, mail_id)
            self.analyzed_mails.append(mo)
        except Exception as e:
            self.additional_meta_infos["skipped_mails"] += 1
            pass

    def add_mails(self, msg_list, foldername):
        for msg in msg_list:
            self.add_mail(msg, foldername)

    def test_login(self, login, password, imap_server):
        mailbox_connect_attempts = 3

        for _ in range(mailbox_connect_attempts):
            try:
                if imap_server == "imap.gmail.com":
                    mailbox = MailBox(imap_server).xoauth2(login, password)
                else:
                    mailbox = MailBox(imap_server).login(login, password)
                if mailbox is not None:
                    return True
            except:
                return False
        return False

    def fetchMails(self, password, imap_server):
        print("Retrieving...")
        LIMIT_PER_FOLDER = 85
        try_reverse = True
        mailbox = None

        mailbox_connect_attempts = 3

        for _ in range(mailbox_connect_attempts):
            if imap_server == "imap.gmail.com":
                mailbox = MailBox(imap_server).xoauth2(self.email, password)
            else:
                mailbox = MailBox(imap_server).login(self.login, password)
            if mailbox is not None:
                break

        folder_count = 0
        for folder in mailbox.folder.list():
            foldername = folder['name']
            folderflags = folder['flags']
            folderstatus = None
            try:
                folderstatus = mailbox.folder.set(foldername)
            except Exception as e:
                pass
            if folderstatus is None:
                try:
                    folderstatus = mailbox.folder.set('"' + foldername + '"')
                except Exception as e:
                    pass

            if (folderstatus is None) or mailbox.folder.get() != foldername:
                print("Error! Skip folder", foldername)
                continue
            print_foldername = self.print_foldername(foldername, folder_count, folderflags)
            if print_foldername.endswith("_sent"):
                continue
            if print_foldername.endswith("_draft"):
                continue
            print("Fetch folder", foldername, "...")
            folder_count += 1
            success_on_folder = False
            if try_reverse:
                try:
                    limit = LIMIT_PER_FOLDER
                    tmp_msg_list = []
                    date_check = False
                    self._pbar_init_signal.emit("Hole E-Mails aus " + foldername + "...", "E-Mails", LIMIT_PER_FOLDER)
                    for msg in tqdm(mailbox.fetch(AND(all=True), reverse=True), unit=" E-Mails"):
                        if (not date_check) and (msg.date.year < 2019):
                            break
                        date_check = True
                        tmp_msg_list.append(msg)
                        limit -= 1
                        self._pbar_val_update_signal.emit(1)
                        if limit <= 0:
                                break
                    self.add_mails(tmp_msg_list,print_foldername)
                    success_on_folder = True
                except Exception as e:
                    print(e)
                    if len(tmp_msg_list) > 50 or len(tmp_msg_list) > LIMIT_PER_FOLDER - 10:
                        success_on_folder = True
                        self.add_mails(tmp_msg_list, print_foldername)
                    else:
                        print("Error on folder. Try again non-reverse", foldername)
            if not success_on_folder:
                try:
                    limit = LIMIT_PER_FOLDER
                    tmp_msg_list = []
                    date_check = False
                    self._pbar_init_signal.emit("Hole E-Mails aus " + foldername + "...", "E-Mails", LIMIT_PER_FOLDER)
                    for msg in tqdm(mailbox.fetch(AND(all=True)), unit=" E-Mails"):
                        if (not date_check) and (msg.date.year < 2019):
                            break
                        date_check = True
                        tmp_msg_list.append(msg)
                        limit -= 1
                        self._pbar_val_update_signal(1)
                        if limit <= 0:
                                break
                    self.add_mails(tmp_msg_list,print_foldername)
                except:
                    print("Error on folder", foldername)

        return True


    def importMails(self, mails, foldername):
        for msg in tqdm(mails, unit=" E-Mails"):
            self.add_mail(msg, foldername)

    def analyzeMails(self):
        print("Analyze...")
        self._pbar_init_signal.emit("Analysiere","E-Mails", len(self.analyzed_mails))
        for mail in tqdm(self.analyzed_mails, unit=" E-Mails"):
            try:
                self._pbar_val_update_signal.emit(1)
                mail.process()
                if mail.cache["#TRACKING_CLICK_URLS_IN_MAIL"] > 0:
                    self.tracking_senders[mail.from_]["CLICK"] += 1
                if mail.cache["#TRACKING_OTHER_URLS_IN_MAIL"] > 0:
                    self.tracking_senders[mail.from_]["OTHER"] += 1
            except Exception as e:
                self.additional_meta_infos["skipped_mails"] += 1
                print(e)
                print(mail.subject)


    def run(self):
        self.fetchMails(self.password, self.imap_server)
        self.analyzeMails()
        self._pbar_finished_signal.emit()

    def autodiscover(self, url, type="imap"):
        #print("Autodiscover Try via " + url)
        response = urllib.request.urlopen(url)
        if response.status == 200:
            text = response.read()
            tree = etree.fromstring(text)
            imapServer = tree.xpath("emailProvider/incomingServer[@type='imap']")[0]
            username = imapServer.xpath("username")[0].text
            hostname = imapServer.xpath("hostname")[0].text
            return username, hostname
        else:
            return False

    def print_foldername(self, real_foldername, counter, flags):
        foldername = "FOLDER_"
        foldername += str(counter) + (" ".join(flags))
        real_foldername = real_foldername.lower()
        if real_foldername in ["sent", "gesendet", "gesendete"]:
            foldername += "_sent"
        elif real_foldername in ["inbox", "posteingang"]:
            foldername += "_inbox"
        elif real_foldername in ["junk"]:
            foldername += "_junk"
        elif real_foldername in ["spam"]:
            foldername += "_spam"
        elif real_foldername in ["trash", "mülleimer", "papierkorb", "delete", "deleted"]:
            foldername += "_trash"
        elif real_foldername in ["drafts", "entwürfe", "draft"]:
            foldername += "_draft"
        elif real_foldername in ["archiv", "archive", "archived"]:
            foldername += "_archive"
        elif real_foldername in ["bulk"]:
            foldername += "_bulk"
        return foldername