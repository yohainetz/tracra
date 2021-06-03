import spacy
from py_singleton import singleton
from spacy.language import Language
from spacy_cld import LanguageDetector
from spacy_readability import Readability
import en_core_web_sm
import de_core_news_sm
from collections import defaultdict
import hashlib

#@Language.factory("language_detector")
#def create_language_detector(nlp, name):
#    return LanguageDetector(language_detection_function=None)

@singleton
class NLPUtils:

    def __init__(self):
        self.nlp = en_core_web_sm.load()
        self.nlp.add_pipe(LanguageDetector(), name='language_detector')
        self.nlp.add_pipe(Readability())

        self.german_nlp = de_core_news_sm.load()
        self.german_nlp.add_pipe(Readability())

        self.text_hash = {}

    def lang_readability(self, text):
        try:
            doc = self.nlp(text)
            # document level language detection. Think of it like average language of the document!
            lang = doc._.languages[0]
            lang_rating =  round(doc._.language_scores[lang], 5)
            readabality_rating = None
            if lang == "de":
                gerdoc = self.german_nlp(text)
                readabality_rating = (gerdoc._.flesch_kincaid_grade_level,
                                      gerdoc._.flesch_kincaid_reading_ease,
                                      gerdoc._.dale_chall,
                                      gerdoc._.smog,
                                      gerdoc._.coleman_liau_index,
                                      gerdoc._.automated_readability_index,
                                      gerdoc._.forcast
                                      )
            else:
                readabality_rating = (doc._.flesch_kincaid_grade_level,
                                        doc._.flesch_kincaid_reading_ease,
                                        doc._.dale_chall,
                                        doc._.smog,
                                        doc._.coleman_liau_index,
                                        doc._.automated_readability_index,
                                        doc._.forcast
                                        )
            return (lang,lang_rating), readabality_rating
        except:
            return None, None

    def text_known(self, text, mailid):
        if text.strip() == "":
            return None
        m = hashlib.md5()
        m.update(text.encode("utf8"))
        digest = m.hexdigest()
        if digest in self.text_hash:
            return self.text_hash[digest]
        else:
            self.text_hash[digest] = mailid
            return None