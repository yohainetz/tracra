import unittest
import os

from imap_tools import MailMessage, MailMessageFlags
import glob
import mailbox
import tracra_export
from utils_resource import ResourceManager
from whois_worker import WhoisWorker
from datetime import timezone, datetime, timedelta
import csv

MSG_FILES_PATH = "tests/aol_messages/"
XLSX_TEST_FILENAME = "aol_test"
TEST_EMAIL = "jojoschaeffer@aol.de"
MAIL_LIMIT = 8


class MailboxTest(unittest.TestCase):


    def test_xlsx_export(self):
        tracra_export.writeMails(self.mailbox.analyzed_mails, XLSX_TEST_FILENAME, True)

        tracking_sender_data = self.mailbox.tracking_senders
        tracra_export.write_plaintext_tracking(list(map(list, tracking_sender_data.items())), XLSX_TEST_FILENAME+"tracking_senders")

    def mail_test(self):
        pass

    # prepare mailbox, import eml files
    def setUp(self):
        filenames = glob.glob(MSG_FILES_PATH+"*.eml")
        messages = []
        mail_counter = 0
        for filename in filenames:
            with open(filename, 'rb') as f:
                bytes_data = f.read()
                message = MailMessage.from_bytes(bytes_data)
                messages.append(message)

                # break if limit reached
                mail_counter += 1
                if mail_counter >= MAIL_LIMIT:
                    break

        print("Imported ", len(messages), "mails.")
        self.mailbox = mailbox.MailboxAnalyzeObject()
        self.mailbox.forename = "Johannes"
        self.mailbox.lastname = "Schäffer"
        self.mailbox.email = TEST_EMAIL
        self.mailbox.email_aliases = [TEST_EMAIL]
        self.mailbox.importMails(messages, "INBOX")
        self.mailbox.analyzeMails()
        self.whois_worker = WhoisWorker(self.mailbox.analyzed_mails)
        self.whois_worker.start()
        self.whois_worker.wait()

        print("Analyzed ", len(self.mailbox.analyzed_mails), "mails.")


    def tearDown(self):
        # clean files
        #os.remove(XLSX_TEST_FILENAME+".xlsx")
        pass


def loadAssertData(msg):
    datestr = msg.date.astimezone(timezone(timedelta(hours=1))).strftime('%y%m%dT%H')
    filename = datestr + "* " + msg.from_ + " * " + msg.subject + ".csv"
    filepath = glob.glob(MSG_FILES_PATH + filename)
    with open(filepath) as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=' ')
        maildata = {}
        resources = []
        for row in csvreader:
            resources.append(row)


def load_single_test_mail(index=0):
    filenames = glob.glob(MSG_FILES_PATH + "*.eml")
    filename = filenames[index]
    with open(filename, 'rb') as f:
        bytes_data = f.read()
        message = MailMessage.from_bytes(bytes_data)
        return message
    return None