from imap_tools import MailBox, AND, MailMessageFlags
from bs4 import BeautifulSoup
from adblockparser import AdblockRules
from urllib.parse import urlparse
import socket
import whois  # pip install python-whois
from resourceanalyzeobject import ResourceAnalyzeObject
import domainhelper
from collections import defaultdict
from domainhelper import DomainHelper
import html2text
import re
from hashed_helper import HashHelper
import tldextract
from lxml import etree
from chardet import detect

from utils_nlp import NLPUtils


class MailAnalyzeObject:
    def __init__(self, msg, foldername, mailbox, mail_id, force_text=False):
        self.mailbox = mailbox
        if force_text:
            self.html = None
        elif msg.html and msg.html.strip() != "":
            self.html = msg.html
            # add txt version of html email to mailbox
            mo = MailAnalyzeObject(msg, foldername, self.mailbox, mail_id + "_text", True)
            self.mailbox.analyzed_mails.append(mo)
        else:
            self.html = None
        if self.html:
            self.text = html2text.html2text(self.html)
        else:
            try:
                encoded_text = msg.text.encode('raw_unicode_escape')
                encoding = detect(encoded_text)['encoding']
                self.text = encoded_text.decode(encoding)
            except Exception as e:
                self.text = msg.text
        self.headers = msg.headers
        self.mail_id = mail_id
        self.to = msg.to
        self.from_ = msg.from_.lower()
        self.from_values = msg.from_values
        self.to_values = msg.to_values
        self.cc_values = msg.cc_values
        self.bcc_values = msg.bcc_values
        self.reply_to_values = msg.reply_to_values
        self.cc = msg.cc
        if "@" in msg.from_:
            self.from_domain = msg.from_.split("@")[1]
        else:
            self.from_domain = ""
        self.folder = foldername
        self.cache = dict()
        self.mtas = self.extractMTAs()
        try:
            self.flags = msg.flags
        except:
            self.flags = {}
        self.subject = msg.subject
        self.date = msg.date
        self.attachments = [(a.filename, a.size) for a in msg.attachments]

        self.web_resources = []
        self.cache["MIME_STRUCTURE"] = str(mime_structure_new(msg.obj))

    def process(self):

        self.processLinks()

        self.fillCache()

    def fillCache(self):
        self.cache["FOLDER"] = self.folder
        self.cache["MAIL_ID"] = self.mail_id
        self.cache["YEAR"] = self.date.year
        self.cache["#TRACKING_OTHER_URLS_IN_MAIL"] = len(list(filter(lambda x: x.isNonClickTracker(), self.web_resources)))
        self.cache["#TRACKING_CLICK_URLS_IN_MAIL"] = len(list(filter(lambda x: x.isClickTracker(), self.web_resources)))
        self.cache["#NON_TRACKING_URLS_IN_MAIL"] = len(self.web_resources) - self.cache["#TRACKING_OTHER_URLS_IN_MAIL"] - self.cache["#TRACKING_CLICK_URLS_IN_MAIL"]

        from_desc, to_desc, cc_desc, bcc_desc = self.describe_from_to_cc()
        self.cache["TO"] = str(to_desc)
        self.cache["FROM"] = str(from_desc)
        self.cache["CC"] = str(cc_desc)
        self.cache["BCC"] = str(bcc_desc)

        self.cache["FLAG_ANSWERED"] = "ANSWERED" in self.flags
        self.cache["FLAG_SEEN"] = "SEEN" in self.flags
        self.cache["FLAG_FLAGGED"] = "FLAGGED" in self.flags
        self.cache["KEYWORDS"] = ",".join(self.keywords())
        self.cache["PERSONAL_SALUTATION"] = ",".join(self.containsPersonalSalutation())
        self.cache["SIGNATURE_BLOCK"] = ",".join(self.signature_block())
        self.cache["RETURN_RECEIPT_HEADER"] = self.readReceiptHeader()
        self.cache["#MTAS"] = len(self.mtas)
        self.cache["#MTA_DIFFERENT_DOMAINS"] = len(self.different_mta_domains())
        self.cache["HTML_PLAIN"] = self.html_plain()
        self.cache["#ATTACHMENTS"] = len(self.attachments)
        self.cache["RAW_SUBJECT"] = self.subject
        self.cache["RAW_FROM"] = self.from_
        self.cache["COMMON_MAIL_PROVIDER"] = self.from_common_mail_provider()
        self.cache["SPF_DKIM_DMARC"] = ",".join(self.dkim_dmarc_spf())
        self.cache["USERAGENT_XMAILER"] = ",".join(self.useragent_xmailer())

        self.cache["MAILINGLIST_PARAMETER"] = self.mailingListParameter()
        self.cache["SENDER_ALEXA_RANKING"] = DomainHelper().alexa_ranking(self.from_domain)
        self.cache["SENDER_TRANCO_RANKING"] = DomainHelper().tranco_ranking(self.from_domain)
        self.cache["DFE_DOMAIN_CATEGORIZATION"] = DomainHelper().dfe_domain_category(self.from_domain)
        self.cache["DMOZ_DOMAIN_CATEGORIZATION"] = ",".join(DomainHelper().filtered_dmoz_domain_category(self.from_domain))
        self.cache["SENDER_TLD"] = tldextract.extract(self.from_domain)[2]
        self.cache["COMMON_EMAIL_MARKETING_SERVICE"] = self.sent_by_marketing_service()
        self.cache["RE_FWD"] = self.re_fwd()

        self.cache["SENDER_NUMBER"] = DomainHelper().enumerate_email_addr(self.from_)
        self.cache["SENDERDOMAIN_NUMBER"] = DomainHelper().enumerate_domain(self.from_domain)
        self.cache["WITHOUT_SUBDOMAIN_NUMBER"] = self.no_subdomain_enumeration()
        self.cache["#SENDER_SUBDOMAINS"] = DomainHelper().count_subdomains(self.from_domain)
        self.cache["SENDER_LENGTH"] = len(self.from_)
        self.cache["SENDERDOMAIN_LENGTH"] = len(self.from_domain)
        self.cache["MAIN_ADDRESSEE"] = ",".join(self.main_addressee())
        lang_rating, readabality_rating = NLPUtils().lang_readability(self.text)
        self.cache["LANGUAGE"] = str(lang_rating)
        self.cache["READABILITY"] = str(readabality_rating)

        self.cache["#TEXT_CHARACTERS"] = len(self.text)
        self.cache["#TEXT_SPACES"] = len(self.text.split(" "))
        self.cache["TEXT_DUPLICATE"] = NLPUtils().text_known(self.text,self.mail_id)

        self.cache["COUNT_HTML_TAGS"] = str(self.html_count_tags())

    def processLinks(self):
        self.mailbox.link_counter = 0
        if self.html:
            soup = BeautifulSoup(self.html, 'html.parser')
            for link in soup.find_all('a'):
                location = link.get('href', None)
                if location is None:
                    continue
                if location.strip() == "":
                    continue
                if location[0] == "#":
                    continue

                resourceObject = ResourceAnalyzeObject(self, location, self.mailbox.link_counter, link)
                self.mailbox.link_counter += 1
                self.web_resources.append(resourceObject)
            for img in soup.find_all('img'):
                location = img.get('src', None)
                if location is None:
                    continue
                if location.strip() == "":
                    continue
                if location[0] == "#":
                    continue

                resourceObject = ResourceAnalyzeObject(self, location, self.mailbox.link_counter, img)
                self.mailbox.link_counter += 1
                self.web_resources.append(resourceObject)
            for link in soup.find_all("link"):
                location = link.get('href', None)
                if location is None:
                    continue
                if location.strip() == "":
                    continue
                if location[0] == "#":
                    continue
                resourceObject = ResourceAnalyzeObject(self, location, self.mailbox.link_counter, link)
                self.mailbox.link_counter += 1
                self.web_resources.append(resourceObject)
            for script in soup.find_all("script"):
                location = script.get('src', "")
                resourceObject = ResourceAnalyzeObject(self, location, self.mailbox.link_counter, script)
                self.mailbox.link_counter += 1
                self.web_resources.append(resourceObject)
        else:  # plain text mail
            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-;?-Z_=@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                              self.text)
            for url in urls:
                resourceObject = ResourceAnalyzeObject(self, url, self.mailbox.link_counter, None)
                self.mailbox.link_counter += 1
                self.web_resources.append(resourceObject)

    # analysis methods

    def mta(self):
        origin = self.headers['Received'][-1]
        origin_server = self.headers['Received'][-1].split(' ')[1]
        return origin_server

    def extractMTAs(self):
        return self.headers.get('Received', [])

    def different_mta_domains(self):
        servers = []
        for mta in self.mtas:
            mta2 = mta.split(" ")
            if len(mta2) > 1:
                servers.append(mta2[1])
        domains = [DomainHelper().removeSubdomain(server) for server in servers]
        # remove duplicates
        return list(set(domains))

    def readReceiptHeader(self):
        header_fields = ["X-Confirm-Reading-To",
                         "Disposition-Notification-To",
                         "Return-Receipt-To"]
        if any(field in header_fields for field in self.headers.keys()):
            return True
        else:
            return False

    def whoisCountry(self):
        return DomainHelper().whoisCountry(self.from_domain)

    def whoisOwner(self):
        return DomainHelper().whoisOwner(self.from_domain)

    def containsPersonalSalutation(self):
        text = self.text
        forename = self.mailbox.forename
        lastname = self.mailbox.lastname
        results = []
        if forename + " " + lastname in text:
            results.append("FULL")
        elif lastname + " " + forename in text:
            results.append("FULL")
        elif " "+forename in text:
            results.append("FORENAME")
        elif " "+lastname in text:
            results.append("LASTNAME")

        for name in self.mailbox.name_aliases:
            if " "+name in text:
                results.append("ALIAS")
                break

        return results

    def html_plain(self):
        if self.html is not None:
            return "HTML"
        elif self.text is not None:
            return "PLAIN"
        else:
            return "ERROR"

    def mailingListParameter(self):
        header_fields = ["List-Help",
                     "List-Post",
                     "List-Subscribe",
                     "List-Id",
                     "List-Unsubscribe",
                     "List-Archive",
                     "List-Help"]
        if any(field in header_fields for field in self.headers.keys()):
            return True
        else:
            return False

    def from_common_mail_provider(self):
        return DomainHelper().commomMailProvider(self.from_domain)

    def main_addressee(self):
        valuelist = [("FROM",self.from_values),("CC", self.cc_values), ("BCC", self.bcc_values), ("TO", self.to_values)]
        collected = []

        for signal, values in valuelist:
            if isinstance(values,dict):
                values = [values]
            for valhash in values:
                mailaddr = valhash['email'].lower()
                if mailaddr in self.mailbox.email_aliases:
                    collected.append(signal)
        return collected

    def describe_from_to_cc(self):
        valuelist = [("FROM",self.from_values),("CC", self.cc_values), ("BCC", self.bcc_values), ("TO", self.to_values)]
        collected = defaultdict(list)
        for signal, values in valuelist:
            # pack to tuple if it's not
            if isinstance(values,dict):
                values = [values]
            for valhash in values:
                mailaddr = valhash['email'].lower()
                if mailaddr.strip() == "" or mailaddr is None or (not "@" in mailaddr):
                    collected[signal].append((-1))
                    continue
                addr_domain = mailaddr.split("@")[1]

                desc_hash = {"is_alias": False}
                if mailaddr in self.mailbox.email_aliases:
                    desc_hash["is_alias"] = True

                desc_hash["ADDR_ID"] = DomainHelper().enumerate_email_addr(mailaddr)
                desc_hash["ADDR_LEN"] = len(mailaddr)
                desc_hash["DOMAIN_ID"] = DomainHelper().enumerate_domain(addr_domain)
                desc_hash["NO_SUBDOMAIN_ID"] = DomainHelper().enumerate_no_subdomain(addr_domain)
                collected[signal].append(desc_hash)
        return collected["FROM"],collected["TO"],collected["CC"],collected["BCC"]

    def re_fwd(self):
        lower_subject = self.subject.lower()
        if lower_subject.startswith("re:"):
            return "RE"
        elif lower_subject.startswith("aw:"):
            return "RE"
        elif lower_subject.startswith("fwd:"):
            return "FWD"
        elif lower_subject.startswith("wg:"):
            return "FWD"
        return None

    def dkim_dmarc_spf(self):
        auth_types = []
        for field in self.headers.get("Authentication-Results", []):
            segments = [item.strip() for subfield in field.split(";") for item in subfield.split(" ")]
            for segment in segments:
                if segment.startswith("spf="):
                    auth_types.append(segment)
                elif segment.startswith("dmarc="):
                    auth_types.append(segment)
                elif segment.startswith("dkim="):
                    auth_types.append(segment)
        return auth_types

    def useragent_xmailer(self):
        l = []
        ua = self.headers.get("User-Agent")
        if ua is not None:
            l.append(" ".join(ua))
        xm = self.headers.get("X-Mailer")
        if xm is not None:
            l.append(" ".join(xm))

        return l

    def keywords(self):
        keys_to_fetch = ["MDNSent", "Draft", "Deleted", "$NotJunk",
                         "NONJUNK","$Junk", "$Forwarded", "FORWARDED",
                         "JUNK", "NOTJUNK", "ANSWERED"]
        keys_to_fetch_lower = [key.lower() for key in keys_to_fetch]
        lower_flags = [flag.lower() for flag in self.flags]
        collected_keys = []
        return [key for key in keys_to_fetch_lower if key in lower_flags]
        #for key in keys_to_fetch_lower:
        #return collected_keys

    def no_subdomain_enumeration(self):
        nd = DomainHelper().removeSubdomain(self.from_domain)
        return DomainHelper().enumerate_domain(nd)

    def signature_block(self):
        l = []
        if self.from_ in self.text:
            l.append("SENDER_ADDRESS_IN_BODY")
        if self.from_values:
            fromstr = self.from_values.get("name", "").strip().replace("\"", "")
            self.cache["FROM_DISPLAY_LENGTH"] = len(fromstr)
            if len(fromstr) > 3:
                if fromstr in self.text:
                    l.append("DISPLAY_FROM_IN_BODY")

        return l

    # HELPER for parallel whois fetching
    def collect_domains(self):
        domains = []
        for ro in self.web_resources:
            if ro.url_domain is not None:
                domains.append(ro.url_domain)
            else:
                #print(ro, ro.html)
                pass

        domains.append(self.from_domain)
        return domains

    def fill_whois_fields(self):
        self.cache["WHOIS_COUNTRY"] = self.whoisCountry()
        self.cache["WHOIS_OWNER"] = self.whoisOwner()
        for ro in self.web_resources:
            ro.fill_whois_fields()

    def sent_by_marketing_service(self):
        auth_header = list(self.headers.get("Authentication-Results", []))
        combinedStr = " ".join(list(self.mtas) + list(auth_header))

        signals = ["(Mailchimp)",
                   "mailjet.com",
                   "mcsignup.com",
                   "mcsv.net",
                   "mcdlv.net",
                   "mailchimpapp.net",
                   "rsgsv.net",
                   "getresponse.com",
                   "sendinblue.com",
                   "aweber.com",
                   "sendgrid.net",
                   "mailgun.net",
                   "expertsender.com",
                   "hubspot.net",
                   "omnidlv.com"
                   ]

        for signal in signals:
            if signal + " " in combinedStr:
                return True
            if signal + ";" in combinedStr:
                return True
        return None

    def html_count_tags(self):
        try:
            if self.html:
                count = defaultdict(int)
                parser = etree.HTMLParser()
                root = etree.fromstring(self.html, parser=parser)
                for ele in root.iter():
                    count[ele.tag] += 1
                return dict(count)
            else:
                return None
        except Exception as e:
            return "parsing error"


def mime_structure_new(msg_object):
    try:
        arr = []
        if isinstance(msg_object, str):
            return (msg_object)
        else:
            arr.append((msg_object.get_content_type(), msg_object.get_content_charset(), len(msg_object)))
        payload = msg_object.get_payload()
        if not isinstance(payload, str):

            for part in payload:
                part_arr = []
                part_arr.append((part.get_content_type(), part.get_content_charset(), len(payload)))
                if part.is_multipart():
                    part_arr.append([mime_structure_new(part)])
                arr.append(part_arr)
        return arr
    except Exception as e:
        return ["parsing failed"]