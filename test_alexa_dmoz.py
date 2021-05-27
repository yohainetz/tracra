import domainhelper

dh = domainhelper.DomainHelper()

domains = dh.alexa_cache.keys()

dmoz_cats = []

for domain in domains:
    try:
        dmoz_cats += dh.dmoz_domain_category(domain).lower().split("|")
    except:
        pass

dmoz_cats = list(set(dmoz_cats))

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
lower_keywords = [key.lower() for key in dmoz_keywords]

for val in dmoz_cats:
    found = False
    for keyword in lower_keywords:
        if keyword in val:
            found = True
            break
    if not found:
        print(val)