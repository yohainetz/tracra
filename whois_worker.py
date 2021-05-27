from PyQt5.QtCore import QThread, pyqtSignal
from tqdm import tqdm
from time import sleep
import os
import whois  # pip install whois
import multiprocessing as mp

from domainhelper import DomainHelper


class WhoisWorker(QThread):
    def __init__(self, mail_objects):
        super().__init__()
        self.progress_reporter = WhoisProgressReporter()
        self.mail_objects = mail_objects

    def run(self):
        PROCESSES = 8
        with mp.Manager() as manager:
            queue = mp.Queue()
            whois_cache = manager.dict()
            domain_counter = mp.Value('i', 0)
            domain_set = set()
            for mail in self.mail_objects:
                for domain in mail.collect_domains():
                    domain_set.add(domain)

            for domain in domain_set:
                queue.put(domain)
                domain_counter.value += 1
            del (domain_set)

            done_counter = mp.Value('i', 0)
            self.progress_reporter.done_counter = done_counter
            self.progress_reporter.domain_counter = domain_counter
            p0 = self.progress_reporter
            worker = []
            for i in range(PROCESSES):
                wProcess = mp.Process(target=parallel_whois_worker, args=(queue, whois_cache, done_counter))
                worker.append(wProcess)
            for w in worker:
                w.start()
            os.system('cls' if os.name == 'nt' else 'clear')
            p0.start()

            # for w in worker:
            #    w.join()
            while not queue.empty():
                sleep(10)
            print("Whois complete")
            sleep(10)
            for w in worker:
                w.terminate()

            p0.terminate()
            print("Whois done")

            DomainHelper().whois_cache = dict(whois_cache)
            del (whois_cache)

        for mail in tqdm(self.mail_objects, unit=" E-Mails"):
            mail.fill_whois_fields()


def parallel_whois_worker(domain_queue, whois_cache, done_counter):
    while True:
        if domain_queue.empty():
            break
        try:
            domain = domain_queue.get()
            if whois_cache.get(domain) is None:
                entry = whois_request(domain)
                whois_cache[domain] = entry
            with done_counter.get_lock():
                done_counter.value += 1
        except:
            break


def whois_request(domain):
    try:
        """ Returns relevant whois data for given domain.  """
        w = whois.query(domain).__dict__
        domainEntry = {
            "country": w.get('registrant_country'),
            "organization": w.get('org'),
            "holderName": w.get('name'),
            "holderAddr": w.get('address')
        }
        return domainEntry
    except:
        domainEntry = {
            "country": "WHOIS REQUEST FAILED",
            "organization": "WHOIS REQUEST FAILED",
            "holderName": "WHOIS REQUEST FAILED",
            "holderAddr": "WHOIS REQUEST FAILED"
        }
        return domainEntry


class WhoisProgressReporter(QThread):
    _pbar_val_signal = pyqtSignal(int)
    _pbar_val_update_signal = pyqtSignal(int)
    _pbar_init_signal = pyqtSignal(str, str, int)
    _pbar_finished_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.domain_counter = None
        self.done_counter = None

    def run(self):
        self._pbar_init_signal.emit("WHOIS", "Domains", self.domain_counter.value)
        with tqdm(total=self.domain_counter.value, unit=" Domains") as pbar:
            while True:
                with self.done_counter.get_lock():
                    pbar.update(self.done_counter.value)
                    self._pbar_val_update_signal.emit(self.done_counter.value)
                    self.done_counter.value = 0
                    sleep(2)
