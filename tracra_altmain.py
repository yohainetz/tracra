
from __future__ import print_function, unicode_literals
from PyInquirer import prompt, print_json
from tracra_export import writeMails
from mailbox import MailboxAnalyzeObject
from oauth_utils import openOauthWebsite, generateOauthString
import pandas as pd
import os, sys
from multiprocessing import freeze_support

class StudyApp:

    def __init__(self):
        self.mailbox = MailboxAnalyzeObject()
        self.email = None
        self.imap = None
        self.password = None
        self.email_alias_set = set()

    def fetchMailsAndWriteToDisk(self):
        self.mailbox.fetchMails(self.password, self.imap)

        self.mailbox.analyzeMails()
        writeMails(self.mailbox.analyzed_mails, "output", False)

    def login_form(self):
        questions = [
            {
                "type": 'input',
                "name": "first_name",
                "message": "Vorname"
            },
            {
                "type": 'input',
                "name": "last_name",
                "message": "Nachname"
            },
            {
                "type": 'input',
                "name": "email",
                "message": "Email"
            }
        ]
        print("Hinweis: Vor- und Nachname werden benötigt um herauszufinden, ob eine E-Mail eine persönliche Ansprache enthält.")
        print("Die E-Mail-Adresse wird neben dem Login auch genutzt um herauszufinden, \
            ob diese beim Öffnen von E-Mails oder beim Klicken auf Links von einem externen Akteur \
            mitgelesen werden könnte. Zu diesem Zweck werden auch mögliche Aliase abgefragt.")
        answers = prompt(questions)
        self.mailbox.email = answers['email'].strip().lower()
        self.mailbox.forename = answers['first_name']
        self.mailbox.lastname = answers['last_name']
        self.email_alias_set.add(self.mailbox.email)

        self.email_alias_form()

        if self.mailbox.email.endswith("gmail.com"):
            self.imap = "imap.gmail.com"
            self.google_form()
        else:
            self.imap_form()

    def google_form(self):

        confirmquestion = [
            {"type": "input",
             "message": "Google erfordert eine explizite Erlaubnis um auf Emails zuzugreifen. Du wirst gleich auf google.com weitergeleitet um dem Zugriff zuzustimmen. Drücke dafür Enter.",
             "name": "continue"
             }
        ]

        prompt(confirmquestion)
        openOauthWebsite()

        tokenquestion = [
            {"type": "input",
             "message": "Access Token",
             "name": "token"
             }
        ]

        answers = prompt(tokenquestion)
        access_token = answers["token"]

        auth_code = generateOauthString(access_token, self.mailbox.email)
        self.password = auth_code
        self.fetchMailsAndWriteToDisk()
        self.exit_form()

    def imap_form(self):
        infered_login, infered_imap = self.mailbox.inferIMAPServer(self.mailbox.email)
        questions = [
            {
                "type": 'input',
                "name": "imap",
                "message": "IMAP Server",
                "default": infered_imap
            },
            {
                "type": 'input',
                "name": "login",
                "message": "Login",
                "default": infered_login
            },
            {
                "type": 'password',
                "name": "password",
                "message": "Passwort"
            }
        ]
        answers = prompt(questions)

        self.imap = answers['imap']
        self.password = answers['password']
        self.mailbox.login = answers['login']
        self.fetchMailsAndWriteToDisk()
        self.exit_form()

    def exit_form(self):
        questions = [
            {
                "type": 'input',
                "name": "exit_propmpt",
                "message": "Fertig. Drücke Enter zum schließen."
            }
        ]
        answers = prompt(questions)
        sys.exit("Programm beendet.")

    def email_alias_form(self):
        ask_again = True

        while ask_again:
            questions = [
                {
                    "type": 'input',
                    "message": "Solltest du E-Mail-Aliasse nutzen, kannst du diese hier angeben. \
                        Jeweils einen Alias eintragen, dann Enter drücken. \
                        Falls nicht, lasse das Feld leer und drücke einfach Enter um Fortzufahren.",
                    "name": "alias"
                }
            ]
            answers = prompt(questions)
            alias = answers['alias'].strip().lower()
            if alias != "":
                self.email_alias_set.add(alias)
            else:
                ask_again = False
                self.mailbox.email_aliases = list(self.email_alias_set)


if __name__ == "__main__":
    freeze_support()
    APP = StudyApp()
    APP.login_form()