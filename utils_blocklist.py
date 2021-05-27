from adblockparser import AdblockRules
from py_singleton import singleton
import logging
import time
import json
from urllib.parse import urlparse
from utils_resource import ResourceManager


# read file


@singleton
class BlocklistHelper:

    def __init__(self):
        self.easylist_rules = None
        self.easylistgermany_rules = None
        self.disconnect_data = {}
        raw_rules = []
        easyprivf = ResourceManager().get_res_path(["tracra_resources","tracra_utils","easyprivacylist.txt"])
        with open(easyprivf, "r", encoding="utf-8") as easyprivacylist:
            raw_rules = easyprivacylist.readlines()
            self.easylist_rules = AdblockRules(raw_rules)
            adblock_rules_count = str(len(raw_rules))
            logging.debug("Imported " + adblock_rules_count + " Easylist rules")
        easyprivgerf = ResourceManager().get_res_path(["tracra_resources","tracra_utils","easylistgermany.txt"])
        with open(easyprivgerf, "r", encoding="utf-8") as easyprivacylist_ger:
            raw_rules = easyprivacylist_ger.readlines()
            self.easylistgermany_rules = AdblockRules(raw_rules)
            adblock_rules_count = str(len(raw_rules))
            logging.debug("Imported " + adblock_rules_count + " Easylist Germany rules")

        discoservf = ResourceManager().get_res_path(["tracra_resources","disconnect-tracking-protection","services.json"])
        with open(discoservf, "r", encoding="utf-8") as disconnectfile:
            obj = json.loads(disconnectfile.read())
            categories = obj["categories"].keys()
            for category in categories:
                for service in obj["categories"][category]:
                    service_domains = [urlparse(url).netloc for url in list(service.values())[0]]
                    for domain in service_domains:
                        if domain in self.disconnect_data:
                            self.disconnect_data[domain].append(category)
                        else:
                            self.disconnect_data[domain] = [category]
            disconnect_count = str(len(list(self.disconnect_data.keys())))
            logging.debug("Imported "+ disconnect_count + " disconnect.me rules")

    def checkUrl(self, url):
        domain = urlparse(url).netloc

        if domain == "":
            return []

        lists = []
        if self.easylist_rules.should_block(url):
            lists.append("Easylist")

        if self.easylistgermany_rules.should_block(url):
            lists.append("EasylistGermany")

        if domain in self.disconnect_data:
            for category in self.disconnect_data[domain]:
                lists.append("disconnect.me-" + category)

        return lists
