import socket
import whois  # pip install whois
from PyQt5.QtCore import pyqtSignal, QObject
from py_singleton import singleton
import csv
import logging
import tldextract
import multiprocessing as mp
from tqdm import tqdm
from time import sleep
import editdistance
import os
from utils_resource import ResourceManager

@singleton
class DomainHelper():

    def __init__(self):
        self.whois_cache = {} # to be filled later via multiprocessing
        # read alexa
        self.alexa_cache = {}
        alexa_f = ResourceManager().get_res_path(["tracra_resources","top-1m-2.csv"])
        alexa_count = 0
        with open(alexa_f, "r", encoding="utf-8") as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            for row in csvreader:
                self.alexa_cache[row[1]] = int(row[0])
                alexa_count += 1
        logging.debug("Imported ", alexa_count, "alexa values")

        # read tranco
        self.tranco_cache = {}
        tranco_f = ResourceManager().get_res_path(["tracra_resources", "tranco_KL4W.csv"])
        tranco_count = 0
        with open(tranco_f, "r", encoding="utf-8") as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            for row in csvreader:
                self.tranco_cache[row[1]] = int(row[0])
                tranco_count += 1
        logging.debug("Imported ", tranco_count, "tranco values")

        # for domain enumeration (instead of hashing)
        self.domain_enumeration_cache = {}
        self.domain_enumeration_counter = 0

        # full domain variants (includes subdomains)
        self.full_domain_enumeration_cache = {}
        self.full_domain_enumeration_counter = 0

        # for mail address enumeration
        self.email_enumeration_cache = {}
        self.email_enumeration_counter = 0

        # read common mail provider domain list
        self.mail_provider_list = []
        with open(ResourceManager().get_res_path(["tracra_resources","5992856","free_email_provider_domains.txt"]), "r", encoding="utf-8") as listfile:
            self.mail_provider_list = listfile.read().splitlines()

        self.url_categorization = {}
        with open(ResourceManager().get_res_path(["tracra_resources","URL-categorization-DFE.csv"]), "r", encoding="utf-8") as csvfile:
            csvreader = csv.DictReader(csvfile)
            for row in csvreader:
                self.url_categorization[row['url']] = row['main_category']

        self.dmoz_categories = {}
        with open(ResourceManager().get_res_path(["tracra_resources","dmoz_domain_category.csv"]), "r", encoding="utf-8") as csvfile:
            csvreader = csv.reader(csvfile, delimiter=",")
            for row in csvreader:
                self.dmoz_categories[row[0]] = row[1]

    def retrieveWhoisData(self, domain):

        if domain in self.whois_cache:
            return self.whois_cache[domain]
        else:
             return {
                    "country": "WHOIS REQUEST FAILED",
                    "organization": "WHOIS REQUEST FAILED",
                    "holderName": "WHOIS REQUEST FAILED",
                    "holderAddr": "WHOIS REQUEST FAILED"
                }


    def whoisOwner(self, domain):
        whoisName = self.retrieveWhoisData(domain).get('name', "")
        if "redacted" in whoisName.lower():
            return "redacted"
        elif whoisName == "":
            return "none"
        elif "FAILED" in whoisName:
            return "WHOIS REQUEST FAILED"
        else:
            return "other"

    # return registrant country of domain using whois
    def whoisCountry(self, domain):
        return self.retrieveWhoisData(domain).get('country', None)

    # return alexa ranking for domain (in chunks of 50)
    def alexa_ranking(self, domain):
        if domain not in self.alexa_cache:
            return None
        else:
            pos = self.alexa_cache[domain]
            return (pos // 50)*50

    # return tranco ranking for domain (in chunks of 50)
    def tranco_ranking(self, domain):
        if domain not in self.tranco_cache:
            return None
        else:
            pos = self.tranco_cache[domain]
            return (pos // 50) * 50

    # removes subdomain from domain string
    def removeSubdomain(self, domain):
        ext = tldextract.extract(domain)
        return '.'.join(ext[1:])

    def without_www(self, domain):
        ext = tldextract.extract(domain)
        subdomains = ext[0]
        if subdomains == "www":
            return '.'.join(list(ext[1:]))
        elif subdomains.startswith("www."):
            subdomains = subdomains[4:]
            return '.'.join([subdomains] + list(ext[1:]))
        else:
            return domain

    def edit_distance(self, domain1, domain2):
        return editdistance.distance(self.without_www(domain2),self.without_www(domain1))

    # return true if sender_domain is in list of common mail providers
    def commomMailProvider(self, sender_domain):
        return sender_domain in self.mail_provider_list

    def dfe_domain_category(self, domain):
        return self.url_categorization.get(domain, None)

    def dmoz_domain_category(self, domain):
        cat = self.dmoz_categories.get("www."+domain, None)
        if cat is None:
            cat = self.dmoz_categories.get(domain, None)
        return cat

    def filtered_dmoz_domain_category(self, domain):
        cat = self.dmoz_domain_category(domain)
        if cat:
            return get_dmoz_keywords(cat)
        return []

    def enumerate_domain(self, domain):
        if domain.strip() == "" or domain is None:
            return -1
        domain = self.without_www(domain)
        index = self.domain_enumeration_cache.get(domain)
        if index is None:
            self.domain_enumeration_counter += 1
            self.domain_enumeration_cache[domain] = self.domain_enumeration_counter
            return self.domain_enumeration_counter
        else:
            return index

    def enumerate_no_subdomain(self, domain):
        nosubdomain = self.removeSubdomain(domain)
        return self.enumerate_domain(nosubdomain)

    def enumerate_email_addr(self, email):
        index = self.email_enumeration_cache.get(email)
        if index is None:
            self.email_enumeration_counter += 1
            self.email_enumeration_cache[email] = self.email_enumeration_counter
            return self.email_enumeration_counter
        else:
            return index

    def count_subdomains(self, url):
        subdomains = tldextract.extract(url)[0]
        www_str = ""
        if subdomains.startswith("www."):
            www_str = " (www)"
        if subdomains == '':
            return "0"
        return str(len(subdomains.split("."))) + www_str


dmoz_keywords = ["Business","Computers","computer","News_and_Media","Society/Law","Radio_and_television","Shopping","cities_and_communes",
                "watch_TV","media","E-mail","email","telecommunications","Society/government","Society/political","society/environmental_Protection",
                "marketing_and_advertisement","society","alternative_media","Aid_organizations_and_charities","Help_and_Development","science",
                "education","leisure","Transportation_and_Logistics","Social_Networking","Food_and_drink","Software","work_and_job","knowledge",
                "tourism","travel","hotels","search_engines","search_engine","Financial_Services","Banking_Services","Games","Video_games",
                "art","Online-Shops","banking","shipping","the_internet","railroad","traffic","food_and_beverage",
                "hospitality","economy/services","information_technology","government","sport","auctions",
                "culture","entertainment","enterprise","publishing_and_printing","map","maps","information","health",
                "news","directories","state","economy","public_administration","habitation","museums","museum",
                "accomodation","internet","trade_and_services","colleges","children_and_adolescents","social_networks",
                "recreation","pets","investment","autos","house","garden","research","finance","childcare","family",
                 "game","commercial","cooking","vehicle","top/reference","top/home"]
lower_dmoz_keywords = [key.lower() for key in dmoz_keywords]

def get_dmoz_keywords(dmoz_path):
    cats = []
    for keyword in lower_dmoz_keywords:
        if keyword in dmoz_path.lower():
            cats.append(keyword)
    return cats