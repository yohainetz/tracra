from __future__ import print_function, unicode_literals

from datetime import datetime
from pathlib import Path

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread
from PyQt5.QtGui import QTextDocument, QTextBlock

import tracra_export
from mailbox import MailboxAnalyzeObject
from oauth_utils import openOauthWebsite, generateOauthString
import os, sys
from multiprocessing import freeze_support
from PyQt5.QtWidgets import *
from utils_resource import ResourceManager

from whois_worker import WhoisWorker


class TracraMain(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Email Tracking Studie 2021")
        self.mailbox = MailboxAnalyzeObject()
        self.email = None
        self.imap = None
        self.password = None
        self.email_aliases_set = set()
        self.name_aliases_set = set()
        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(QLabel("Hinweis: Vor- und Nachname werden benötigt um herauszufinden, ob eine E-Mail eine persönliche Ansprache enthält."))
        self.form_layout = QFormLayout()
        # Add widgets to the layout
        self.forename_edit = QLineEdit()
        self.lastame_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.form_layout.addRow("Vorname:", self.forename_edit)
        self.form_layout.addRow("Nachname:", self.lastame_edit)
        self.form_layout.addRow("Email:", self.email_edit)

        self.main_layout.addLayout(self.form_layout)
        self.forward_button = QPushButton("Weiter")
        self.forward_button.setDefault(True)
        self.main_layout.addWidget(self.forward_button)

        self.setLayout(self.main_layout)

        self.forward_button.clicked.connect(self.process_login_form)

    def fetchMailsAndWriteToDisk(self):
        self.forward_button.setDisabled(True)
        self.pbar = QProgressBar()
        self.pbar_label = QLabel()
        self.main_layout.addWidget(self.pbar_label)
        self.main_layout.addWidget(self.pbar)
        self.mailbox.password = self.password
        self.mailbox.imap_server = self.imap
        self.mailbox.email_aliases = list(self.email_aliases_set)

        # Step 2: Create a QThread object
        #self.thread = QThread()

        #self.mailbox._pbar_finished_signal.connect(self.mailbox.quit)
        #self.mailbox._pbar_finished_signal.connect(self.mailbox.deleteLater)


        self.mailbox._pbar_val_signal.connect(self.pbar_signal_val)
        self.mailbox._pbar_val_update_signal.connect(self.pbar_signal_update)
        self.mailbox._pbar_init_signal.connect(self.pbar_signal_init)
        self.mailbox.finished.connect(self.do_whois)

        # Step 4: Move mailbox to the thread
        #self.mailbox.moveToThread(self.thread)
        self.mailbox.start()



    def do_whois(self):
        print("Begin Whois")
        self.whois_worker = WhoisWorker(self.mailbox.analyzed_mails)
        self.whois_worker.progress_reporter._pbar_val_signal.connect(self.pbar_signal_val)
        self.whois_worker.progress_reporter._pbar_val_update_signal.connect(self.pbar_signal_update)
        self.whois_worker.progress_reporter._pbar_init_signal.connect(self.pbar_signal_init)

        self.whois_worker.finished.connect(self.whois_worker.progress_reporter.quit)
        self.whois_worker.finished.connect(self.whois_worker.progress_reporter.deleteLater)
        self.whois_worker.start()
        self.whois_worker.finished.connect(self.write_to_files)

    def write_to_files(self):
        now = datetime.now()
        datestr = now.strftime("%m-%d_%H-%M")
        self.pbar_label.setText("Schreibe Dateien")
        ret = QMessageBox.question(self, "Fertig",
                                   "Fertig! Wähle nun einen Ort zum Speichern der Ausgabedateien.",
                                   QMessageBox.Ok)

        defaultpath = None
        try:
            defaultpath = str(Path.home())
        except Exception as e:
            pass
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder for Output', defaultpath)
        tracra_export.writeMails(self.mailbox.analyzed_mails, "output_"+datestr, folderpath,False, meta_infos=self.mailbox.additional_meta_infos)
        tracking_sender_data = self.mailbox.tracking_senders
        tracra_export.write_plaintext_tracking(tracking_sender_data, "likely_tracking_"+datestr, folderpath)
        self.pbar_label.setText("Dateien geschrieben nach: " + folderpath)
        self.prepare_exit()

    def process_login_form(self):


        self.mailbox.email = self.email_edit.text().strip().lower()
        self.mailbox.forename = self.forename_edit.text()
        self.mailbox.lastname = self.lastame_edit.text()
        self.email_aliases_set.add(self.mailbox.email)

        self.email_alias_form()

    def google_form(self):
        self.forward_button.clicked.disconnect()
        ret = QMessageBox.question(self, "GMAIL","Google erfordert eine explizite Erlaubnis um auf Emails zuzugreifen. Du wirst gleich auf google.com weitergeleitet um dem Zugriff zuzustimmen.", QMessageBox.Ok)

        #prompt(confirmquestion)
        openOauthWebsite()

        self.acces_token_edit = QLineEdit()
        self.form_layout.addRow("Gmail Access Token", self.acces_token_edit)

        self.forward_button.clicked.connect(self.process_google_form)


    def process_google_form(self):
        self.forward_button.clicked.disconnect()
        access_token = self.acces_token_edit.text()
        auth_code = generateOauthString(access_token, self.mailbox.email)
        self.password = auth_code

        if self.mailbox.test_login(self.mailbox.email, self.password, self.imap):
            self.fetchMailsAndWriteToDisk()
        else:
            QMessageBox.question(self,"Login Fehler","Eine Verbindung mit dem Mail-Server konnte nicht hergestellt werden. Bitte prüfe die Login-Daten.", QMessageBox.Retry)
            openOauthWebsite()
            self.acces_token_edit.setText("")
            self.forward_button.clicked.connect(self.process_google_form)

    def imap_form(self):
        infered_login, infered_imap = self.mailbox.inferIMAPServer(self.mailbox.email)

        self.imap_edit = QLineEdit(infered_imap)
        self.login_edit = QLineEdit(infered_login)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        self.form_layout.addRow("IMAP Server",self.imap_edit)
        self.form_layout.addRow("Login",self.login_edit)
        self.form_layout.addRow("Passwort",self.password_edit)

        self.forward_button.clicked.disconnect()
        self.forward_button.clicked.connect(self.process_imap_form)

    def process_imap_form(self):
        self.forward_button.clicked.disconnect()
        self.imap = self.imap_edit.text()
        self.password = self.password_edit.text()
        self.mailbox.login = self.login_edit.text()
        if self.mailbox.test_login(self.mailbox.login, self.password, self.imap):
            self.fetchMailsAndWriteToDisk()
        else:
            QMessageBox.about(self,"Login Fehler","Eine Verbindung mit dem Mail-Server konnte nicht hergestellt werden. Bitte prüfe die Login-Daten.")
            self.forward_button.clicked.connect(self.process_imap_form)



    def prepare_exit(self):
        #self.main_layout.addWidget(QLabel(
        #    "Vorgang abgeschlossen. Du findest die Ausgabedateien in dem Ordner, in dem auch dieses Programm liegt."))
        self.exit_btn = QPushButton("Beenden.")
        self.exit_btn.clicked.connect(self.exit_form)
        self.main_layout.addWidget(self.exit_btn)

    def exit_form(self):
        sys.exit("Programm beendet.")

    def email_alias_form(self):

        self.email_alias_edit = QPlainTextEdit()
        self.form_layout.addRow("E-Mail Aliasse\n(Ein Alias pro Zeile)",self.email_alias_edit)

        self.name_alias_edit = QPlainTextEdit()
        self.form_layout.addRow("Namensvarianten\n(Eine pro Zeile)", self.name_alias_edit)

        self.forward_button.clicked.disconnect()
        self.forward_button.clicked.connect(self.process_alias_form)

    def process_alias_form(self):
        namedoc = self.name_alias_edit.toPlainText()
        for name in namedoc.split("\n"):
            if name != "":
                self.name_aliases_set.add(name)

        emaildoc = self.email_alias_edit.toPlainText()
        for email in emaildoc.split("\n"):
            if email != "":
                self.email_aliases_set.add(email)

        # next form depends on imap input
        if self.mailbox.email.endswith("gmail.com"):
            self.imap = "imap.gmail.com"
            self.google_form()
        else:
            self.imap_form()

    def pbar_signal_init(self, label, unit, new_max):
        self.pbar.setValue(0)
        self.pbar_label.setText(label)
        self.pbar.setMaximum(new_max)

    def pbar_signal_val(self, val):
        self.pbar.setValue(int(val))

    def pbar_signal_update(self, val):
        self.pbar.setValue(self.pbar.value() + int(val))


if __name__ == "__main__":
    freeze_support()

    app = QApplication(sys.argv)
    tracra_main = TracraMain()
    tracra_main.show()
    exit_code = app.exec_()
    sys.exit(exit_code)
    