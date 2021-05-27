from imap_tools import MailBox, AND, MailMessageFlags
from bs4 import BeautifulSoup
from adblockparser import AdblockRules
from urllib.parse import urlparse
from domainhelper import DomainHelper
from utils_blocklist import BlocklistHelper
from hashed_helper import HashHelper
import re
import editdistance # ARCHFLAGS="-arch x86_64"
import tldextract


class ResourceAnalyzeObject:
    def __init__(self, mail, url, counter, html=None):
        self.url = url.strip()
        self.url_domain = None
        self.html = html
        self.mail = mail
        self.tracking = False
        self.cache = dict()
        self.counter = counter

        #try:
        if html is None:
            self.url_domain = urlparse(self.url).netloc
            self.fillCache()
        elif html.name == "link":
            self.url_domain = urlparse(self.url).netloc
            self.fillCache()
            html_attrs_without_href = {field: self.html.attrs.get(field) for field in ["rel","type","itemprop"]}
            self.cache["HTML_TAG_ADDITIONAL"] = str(html_attrs_without_href)
        elif self.url.startswith("mailto:"):
            self.mailto = self.url
            maildomain_arr = self.url.split("@")
            if len(maildomain_arr) > 1:
                maildomain = maildomain_arr[1]
                self.url_domain = DomainHelper().removeSubdomain(maildomain)
            self.fillMailtoCache()
        elif html.name == "script":
            if self.url == "":
                # local script
                self.cache["HTML_TAG_ADDITIONAL"] = "local script"
                self.url_domain = ""
            else:
                # remote script
                self.cache["HTML_TAG_ADDITIONAL"] = "remote script"
                self.url_domain = urlparse(self.url).netloc
            self.fillCache()
        elif self.url.startswith("https:") or self.url.startswith("http:"):
            self.url_domain = urlparse(self.url).netloc
            self.fillCache()

        else:
            pass

        #except Exception as e:
        #    print("fillCache() failed:", e)
        #    print("for", self.url, "in", self.mail.subject)
        #    self.cache["HTML_TAG"] = str(self.html)
        #    # TODO remove debug


    def process(self):
        pass

    def fillCache(self):
        self.cache["BLOCKED_BY"] = ", ".join(self.blockedBy())
        self.cache["EMAIL_LEAKAGE"] = ",".join(self.parameterContainsMail())
        self.cache["#HTTP_PARAMETER"] = len(self.params())
        self.describe_params()
        path_len, path_ele = self.count_path(self.url)
        self.cache["PATH_LENGTH"] = path_len
        self.cache["#PATH_ELEMENTS"] = path_ele
        self.cache["DESCRIBE_PATH_ELES"] = ",".join([str(tupl) for tupl in self.describe_path_eles()])
        self.cache["URL_LENGTH"] = len(self.url)
        self.cache["THIRD_PARTY"] = self.mail.from_domain not in self.url_domain
        self.cache["URL"] = self.url
        self.cache["PARENT_SUBJECT"] = self.mail.subject
        self.cache["ALEXA_RANKING"] = DomainHelper().alexa_ranking(self.url_domain)
        self.cache["TRANCO_RANKING"] = DomainHelper().tranco_ranking(self.url_domain)
        self.cache["TLD"] = tldextract.extract(self.url_domain)[2]
        self.cache["DFE_DOMAIN_CATEGORIZATION"] = DomainHelper().dfe_domain_category(self.url_domain)
        self.cache["DMOZ_DOMAIN_CATEGORIZATION"] = DomainHelper().dmoz_domain_category(self.url_domain)
        self.cache["WITHOUT_SUBDOMAIN_NUMBER"] = self.no_subdomain_enumeration()
        self.cache["#SUBDOMAINS"] = DomainHelper().count_subdomains(self.url_domain)
        self.cache["LINK_COUNTER"] = self.counter

        self.cache["DOMAIN_NUMBER"] = DomainHelper().enumerate_domain(self.url_domain)
        self.cache["MAIL_ID"] = self.mail.mail_id
        self.cache["EDITDISTANCE_URLDOMAIN_FROMDOMAIN"] = editdistance.distance(self.mail.from_domain, self.url_domain)
        self.cache["UNSUBSCRIBE_INDICATORS"] = ",".join(self.unsubscribe_indicators())

        if self.html is not None:
            self.cache["HTML_TAG"] = self.html.name
            self.cache["TRACKING_PIXEL"] = self.isTrackingPixel()
            self.evaluateLinkDisplayText()  # fill display link cache fields
            self.cache["PRIMARY_ACTION"] = self.primary_action()

    def fillMailtoCache(self):
        self.cache["HTML_TAG"] = self.html.name
        self.cache["HTML_TAG_ADDITIONAL"] = "mailto"
        self.cache["URL"] = self.url
        self.cache["PARENT_SUBJECT"] = self.mail.subject
        self.cache["MAIL_ID"] = self.mail.mail_id
        self.cache["LINK_COUNTER"] = self.counter
        if self.url_domain:
            self.cache["TLD"] = tldextract.extract(self.url_domain)[2]
            self.cache["THIRD_PARTY"] = self.mail.from_domain not in self.url_domain
            self.cache["DFE_DOMAIN_CATEGORIZATION"] = DomainHelper().dfe_domain_category(self.url_domain)
            self.cache["DMOZ_DOMAIN_CATEGORIZATION"] = ",".join(DomainHelper().filtered_dmoz_domain_category(self.url_domain))
            self.cache["DOMAIN_NUMBER"] = DomainHelper().enumerate_domain(self.url_domain)
            self.cache["WITHOUT_SUBDOMAIN_NUMBER"] = self.no_subdomain_enumeration()
        else:
            pass



    def params(self, url=None):
        if url is None:
            url = self.url
        params = []
        for paramPair in list(filter(None, urlparse(url).query.split("&"))):
            paramKey, paramValue = None, None
            paramArr = paramPair.split("=")
            paramKey = paramArr[0]
            if len(paramArr) > 1:
                paramValue = paramArr[1]
            params.append((paramKey, paramValue))
        return params

    def paramsNonEmpty(self):
        return list(filter(lambda p: p[1] is not None, self.params()))

    def parameterContainsMail(self):
        hh = HashHelper()
        res_list = []
        params = self.paramsNonEmpty()
        for email in self.mail.mailbox.email_aliases:
            res_list += [hh.hashed(email, p[1]) for p in params]
        return list(filter(lambda h: h is not None, res_list))

    def whoisCountry(self):
        return DomainHelper().whoisCountry(self.url_domain)

    def whoisOwner(self):
        return DomainHelper().whoisOwner(self.url_domain)

    def blockedBy(self):
        return BlocklistHelper().checkUrl(self.url)

    def isTracker(self):
        if self.url.startswith("mailto:"):
            return False
        if self.blockedBy() != []:
            return True
        if self.html and self.isTrackingPixel():
            return True

    def isTrackingPixel(self):
        if self.html.name == "img":
            if (self.html.get("width") == "1") and (self.html.get("height") == "1"):
                if len(self.params()) > 0:
                    return True
                else:
                    return "1x1px"
        return None

    def evaluateLinkDisplayText(self):
        if self.html.name != "a":
            return None
        linktext = self.html.get_text()
        m = re.search('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',linktext)
        diff_result = None
        if m == None:
            diff_result = "No URL"
        else:
            texturl = m.group(0).strip().lower()
            textdomain = urlparse(texturl).netloc
            if texturl in self.url.lower():
                diff_result = "SAME"
            elif self.url.lower() in texturl:
                diff_result = "SAME"
            elif self.url_domain.lower() in textdomain:
                diff_result = "SAME_DOMAIN"
            elif textdomain in self.url_domain.lower():
                diff_result = "SAME_DOMAIN"
            else:
                diff_result = "DIFFERENT"

            self.cache["EDITDISTANCE_DISPLAYLINK_URL"] = self.link_display_editdistance(texturl)
            self.cache["DISPLAYLINK_#PARAMS"] = len(self.params(texturl))
            self.cache["DISPLAYLINK_#SUBDOMAINS"] = DomainHelper().count_subdomains(texturl)
            self.cache["DISPLAYLINK_URL_LENGTH"] = len(texturl)
            path_len, path_ele = self.count_path(texturl)
            self.cache["DISPLAYPATH_LENGTH"] = path_len
            self.cache["DISPLAY_#PATH_ELEMENTS"] = path_ele

            self.cache["EDITDISTANCE_DISPLAYLINKDOMAIN_URLDOMAIN"] = editdistance.distance(self.url_domain, textdomain)
            self.cache["EDITDISTANCE_DISPLAYLINKDOMAIN_FROMDOMAIN"] = editdistance.distance(textdomain, self.mail.from_domain)

        self.cache["DISPLAYLINK_TEXT"] = diff_result

    def primary_action(self):
        html_classes = self.html.get('class',[])
        signals = ["primary","button","btn"]
        for html_class in html_classes:
            for signal in signals:
                if signal in html_class:
                    return signal
        return None

    def no_subdomain_enumeration(self):
        nd = DomainHelper().removeSubdomain(self.url_domain)
        return DomainHelper().enumerate_domain(nd)

    def link_display_editdistance(self, display_url):
        return editdistance.distance(self.url, display_url)

    def fill_whois_fields(self):
        self.cache["WHOIS_COUNTRY"] = self.whoisCountry()
        self.cache["WHOIS_OWNER"] = self.whoisOwner()

    def count_path(self, url):
        path = urlparse("http://www.google.com/images/photos/zasf?img=435").path
        if path == "":
            return 0, 0
        else:
            return len(path), len(path.split("/"))


    def describe_params(self):
        params = self.params()
        describe_keys = [str(describe_single_param(p[0])) for p in params]
        describe_values = [str(describe_single_param(p[1])) for p in params]
        self.cache["DESCRIBE_PARAM_KEYS"] = ",".join(describe_keys)
        self.cache["DESCRIBE_PARAM_VALS"] = ",".join(describe_values)

    def describe_path_eles(self):
        path = urlparse(self.url).path
        if path.startswith("/"):
            path = path[1:]
        if path == "" or path == "/":
            return []
        path_eles = path.split("/")
        return [describe_single_param(pele) for pele in path_eles]

    def unsubscribe_indicators(self):
        res = []
        if self.html:
            if self.html.name == "a":
                linktext = self.html.get_text().lower()
                signal_words = ["abbestellen",
                                "unsubscribe",
                                "abmelden",
                                "abonnement",
                                "beenden"]
                for signal in signal_words:
                    if signal in linktext:
                        res.append(signal)
        # plain URL
        signal_words = ["abbestellen",
                        "unsubscribe",
                        "abmelden",
                        "abonnement",
                        "beenden"]
        for signal in signal_words:
            if signal in self.url:
                res.append("url_"+signal)

        return res



def describe_single_param(val):
    #find_domains = "^((?!-))(xn--)?[a-z0-9][a-z0-9-_]{0,61}[a-z0-9]{0,1}\.(xn--)?([a-z0-9\-]{1,61}|[a-z0-9-]{1,30}\.[a-z]{2,})$"
    find_domains = "((?!-))(xn--)?[a-z0-9][a-z0-9-_]{0,61}[a-z0-9]{0,1}\.(xn--)?([a-z0-9\-]{1,61}|[a-z0-9-]{1,30}\.[a-z]{2,})"
    val_type = "unknown"
    extra = None
    if val is None:
        return None, None, None
    if val.isnumeric():
        val_type = "numeric"
    elif val.isalpha():
        val_type = "alpha"
    elif val.isalnum():
        val_type = "alnum"
    if val.lower() == "mail":
        extra = "mail"
    elif val.lower() == "id":
        extra = "id"
    elif re.search(find_domains, val):
        extra = "domain-indication"
    return len(val), val_type, extra