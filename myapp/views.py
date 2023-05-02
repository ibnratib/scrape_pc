from django.shortcuts import render
from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
import time
import json
from django.http import JsonResponse
from django.http import HttpResponse
from selenium import webdriver
import platform
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


# Detect the type of machine
os_type = platform.system()

# Initialize the Chrome WebDriver based on the detected OS type
if os_type == 'Windows':
    # Path to the downloaded Chrome WebDriver for Windows
    driver_path = 'chromedriver_win.exe'
elif os_type == 'Linux':
    # Path to the downloaded Chrome WebDriver for Linux
    driver_path = 'chromedriver_linux'

# Create an instance of Chrome WebDriver


# Create your views here.

def home(request):


    base_url = f"https://www.iris.ma"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "DNT": "1",
        "Connection": "close",
        "Upgrade-Insecure-Requests": "1",
    }

    # recuperer les liens de tous les categories
    response = requests.get(base_url, headers=headers)
    html_content = response.content
    soup = BeautifulSoup(html_content, "html.parser")
    menu_categories = soup.find("li", class_="menu_pr_category")
    liste_categorie = menu_categories.find_all("li", class_="mm_tabs_li")
    liste_url_categorie = []
    i = 10
    for categorie in liste_categorie:
        sous_categorie = {"url_sous_categorie": []}
        categorie_name = categorie.find("span", class_="mm_tab_name")
        i += 1
        if categorie_name:
            categorie_name = categorie_name.text.strip()

        sous_categorie['nom_categorie'] = categorie_name
        sous_categorie['id'] = "id" + str(i)
        url_liste_artictes = categorie.find_all("a", class_=("ets_mm_url"))
        for liste_articte in url_liste_artictes:
            sous_categorie['url_sous_categorie'].append(
                {"lien": liste_articte['href'], "nom": liste_articte.text})
        liste_url_categorie.append(sous_categorie)
    

    return render(request, 'index.html', {"categories": liste_url_categorie})

import zipfile
from datetime import datetime
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def ajax_calls(request):

    if request.method == 'POST':
        received_json_data = json.loads(request.body)
        action = received_json_data['action']

        if action == "scraper-pages":
            liste_to_scrape = received_json_data['liste_to_scrape']
            data = scrape_liste_categrie_selinieum(liste_to_scrape)
            data.to_excel("media/output.xlsx")
            with zipfile.ZipFile('media/output.zip', mode='w', compression=zipfile.ZIP_DEFLATED) as z:
                z.write("media/output.xlsx")
            fs = FileSystemStorage()
            data = {'url': fs.url('output.zip')}

            return JsonResponse(data)
            
        return JsonResponse(data={}, safe=False)



def scrape_liste_categrie_bs4(liste_url_categorie):

    liste_all_product_details = []
    if liste_url_categorie:
        
        for url_categorie in  liste_url_categorie:    
            # recuperere les liens des article de la categorie
            next_page = True
            i=1
            liste_url_produit = []
            nom_categorie = ""
            while next_page:
                url_page = url_categorie+f"?page={i}"
                response = requests.get(url_page)
                i +=1
                if (response.url != url_page and response.url != url_categorie) or (response.url != url_page and i >2):
                    next_page = False
                
                html_content = response.content
                soup = BeautifulSoup(html_content, "html.parser")

                list_titre_produit = soup.find_all("h3", class_="product-title")
                
                if next_page:
                    for titre_produit in list_titre_produit:
                        liste_url_produit.append(titre_produit.find("a")['href'])
                liste_url_produit = list(set(liste_url_produit))
                # recupere le nom de la categorie
                if not nom_categorie:
                    nom_categorie_tag = soup.find("h1", class_="h1")
                    if nom_categorie_tag:
                        nom_categorie = nom_categorie_tag.text

                
                
            if liste_url_produit:
                for url_produit in liste_url_produit:
                    produit = {"categorie": nom_categorie}
                    liste_image = []
                    response = requests.get(url_produit)
                    html_content = response.content
                    soup = BeautifulSoup(html_content, "html.parser")

                    prix_actuel_produit = soup.find("span", class_="current-price-value")
                    ref_produit = soup.find("div", class_="product-reference")
                    image_produit = soup.find("img", class_="no-sirv-lazy-load")

                    all_image_produit = soup.find_all("a", class_="magictoolbox-selector")
                    description_produit = soup.find('div', class_="product-information")
                    full_description = soup.find('div', class_="product-description")
                    
                    partner_name = soup.find("div", class_="manufacturer_image")
                    nom_produit = soup.find("h1", class_="productpage_title")

                    list_flag = soup.find("ul", "product-flags js-product-flags")
                    discount = list_flag.find("li", class_="product-flag discount")
                    in_stock = list_flag.find("li", class_="product-flag in_stock")
                    out_of_stock = list_flag.find("li", class_="product-flag out_of_stock")

                    nouveau_produit = list_flag.find("li", class_="product-flag new")

                    if discount:
                        produit['remise'] = discount.text
                    else:
                        produit['remise'] = None

                    if nouveau_produit:
                        produit['nouveau'] = nouveau_produit.text
                    else:
                        produit['nouveau'] = None

                    if in_stock:
                        produit['disponibilite'] = in_stock.text
                    else:
                        if out_of_stock:
                            produit['disponibilite'] = out_of_stock.text
                        else:
                            produit['disponibilite'] = None                       

                    if partner_name:
                        produit['partenaire'] = partner_name.find('img')['alt']
                    else:
                        produit['partenaire'] = None
                    
                    if nom_produit:
                        produit['produit'] = nom_produit.text
                    else:
                        produit['produit'] = None

                    if full_description:
                        produit['full_description'] = full_description
                    else:
                        produit['full_description'] = None

                    if description_produit:
                        produit['short_description'] = description_produit.find("p")
                    else:
                        produit['short_description'] = None

                    if ref_produit:
                        produit['reference'] = ref_produit.find('span').text
                    else:
                        produit['reference'] = None
                    
                    if image_produit:
                        liste_image.append(image_produit['src'])
                    else:
                        produit['image'] = None
                    if len(all_image_produit) >0:
                        for img in all_image_produit:
                            if img['href'] not in liste_image:
                                liste_image.append(img['href'])
                    produit['image'] = liste_image
                    
                    if prix_actuel_produit:
                        produit['prix'] = prix_actuel_produit.text.replace('\n', '').strip().replace('DH', "").replace("TTC", "").strip()
                    else:
                        produit['prix'] = None
                    liste_all_product_details.append(produit)

                                
            
    df = pd.DataFrame(liste_all_product_details)
    return df
    

def scrape_liste_categrie_selinieum(liste_url_categorie):
    driver = webdriver.Chrome()
    driver.maximize_window()  
    # URL de la page de connexion
    login_url = "https://www.disway.com/profile/login"

    # Données du formulaire de connexion

    email = "itaccess.share@gmail.com",
    password = "Tanger@/2023"

    # Lancer le navigateur
    driver_diway = webdriver.Chrome()
    driver_diway.get(login_url)

    # Remplir le formulaire de connexion
    email_field = driver_diway.find_element(By.NAME, "email")
    email_field.send_keys(email)

    password_field =  driver_diway.find_element(By.NAME, "password")
    password_field.send_keys(password)

    # Envoyer le formulaire en appuyant sur la touche Entrée
    password_field.send_keys(Keys.RETURN)
    
    liste_all_product_details = []

    # liste filter
    filtres = ["Cartouches d'impression",
                    "Vitesse d'impression noir",
                    "Qualité d'impression couleur",
                    "Qualité d'impression noire",
                    "Écran",
                    "Cycle d'utilisation",
                    "Mémoire installée",
                    "Poids net",
                    "Dimensions (l x p x h)",
                    "Capacité bac papier",
                    "Impression sans bordure",
                    "Connectivité",
                    "Processeur",
                    "Mémoire vive(RAM) installée",
                    "Taille du disque dur",
                    "Carte graphique",
                    "Mémoire vidéo dédiée",
                    "Poids en kg",
                    "Poids en kgTaille de l'écran",
                    "Clavier",
                    "Carte réseau Ethernet",
                    "Communication sans fil",
                    "Mémoire vive(RAM) maxi",
                    "Taille de l'écran (diagonale)"]
    if liste_url_categorie:
        
        for url_categorie in  liste_url_categorie:    
            # recuperere les liens des article de la categorie
            next_page = True
            i=1
            liste_url_produit = []
            nom_categorie = ""
            while next_page:
                url_page = url_categorie+f"?page={i}"
                response = requests.get(url_page)
                i +=1
                if (response.url != url_page and response.url != url_categorie) or (response.url != url_page and i >2):
                    next_page = False
                
                html_content = response.content
                soup = BeautifulSoup(html_content, "html.parser")

                list_titre_produit = soup.find_all("h3", class_="product-title")
                
                if next_page:
                    for titre_produit in list_titre_produit:
                        liste_url_produit.append(titre_produit.find("a")['href'])
                liste_url_produit = list(set(liste_url_produit))
                # recupere le nom de la categorie
                if not nom_categorie:
                    nom_categorie_tag = soup.find("h1", class_="h1")
                    if nom_categorie_tag:
                        nom_categorie = nom_categorie_tag.text
                
                
            if liste_url_produit:
                for url_produit in liste_url_produit:

                    # declaration des variables
                    produit = {"categorie": nom_categorie}
                    liste_image = []
                    price_disway = None
                    disponibilite_disway = None
                    disponibilite_iris = None
                    price_iris = None

                    # ouvrire iris pour un produit
                    driver.get(url_produit)
                    time.sleep(3)

                    #############################################################################
                    #############################################################################
                    #############################################################################
                    # recuperer le reference produit et lancer la recherche du produit dans disway

                    ref_produit = driver.find_element(By.CLASS_NAME, "product-reference")
                    try:
                        driver_diway.get(f"https://www.disway.com/{ref_produit.find_element(By.TAG_NAME,'span').text}")
                        driver_diway.refresh()
                        disponibilite =  driver_diway.find_element(By.CLASS_NAME, "Details_stock-value")
                        price =  driver_diway.find_element(By.CLASS_NAME, "Details_actual-price")
                        disponibilite_disway = disponibilite.text
                        price_disway = price.text.replace('.', '').replace('MAD', '')
                    except:
                        None
                    
                    #############################################################################
                    #############################################################################
                    #############################################################################
                    # trouver les diffrent section a scraper

                    prix_actuel_produit = driver.find_element(By.CLASS_NAME, "current-price-value")

                    try:
                        image_produit = driver.find_element(By.CLASS_NAME, "no-sirv-lazy-load")
                    except:
                        image_produit = None

                    try:
                        all_image_produit = driver.find_elements(By.CLASS_NAME, "magictoolbox-selector")
                    except:
                        pass

                    description_produit = driver.find_element(By.CLASS_NAME, "product-information")
                    partner_name = driver.find_element(By.CLASS_NAME, "manufacturer_image")
                    nom_produit = driver.find_element(By.CLASS_NAME, "productpage_title")
                    list_flag = driver.find_element(By.CLASS_NAME, "product-flags.js-product-flags")

                    # clicker le button description pour recuperer la description
                    try:
                        link = driver.find_element(By.LINK_TEXT, "DESCRIPTIF")
                        link.click()
                        full_description = driver.find_element(By.CLASS_NAME, "product-description").get_attribute('innerHTML')
                    except:
                        full_description = None

                    # clicker le button fiche technique pour recuperer la fiche technique
                    try:
                        link = driver.find_element(By.LINK_TEXT, "FICHE TECHNIQUE")
                        link.click()
                        fiche_technique = driver.find_element(By.CLASS_NAME, "product-features").get_attribute('innerHTML')

                        # recuperer les filtre
                        # créer un objet BeautifulSoup à partir du code HTML
                        soup = BeautifulSoup(fiche_technique, 'html.parser')

                        # trouver tous les éléments <dt> dans la page
                        elements_dt = soup.find_all('dt')

                        # trouver tous les éléments <dd> dans la page
                        elements_dd = soup.find_all('dd')

                        # initialiser un dictionnaire pour stocker les clés et les valeurs
                        data = {}

                        # parcourir les éléments <dt> et <dd> et ajouter les clés et les valeurs au dictionnaire
                        for i in range(len(elements_dt)):
                            key = elements_dt[i].text.strip()
                            value = elements_dd[i].text.strip()
                            data[key] = " ".join(value.split())

                        for filtre in filtres:
                            if data.get(filtre, None):
                                produit[filtre] = data.get(filtre, None)
                    except:
                        fiche_technique = None
                    
                    #############################################################################
                    #############################################################################
                    #############################################################################
                    # remplire les la liste des valeur

                    produit['fiche_technique'] = fiche_technique
                    produit['full_description'] = full_description

                    try:
                        discount = list_flag.find_element(By.CLASS_NAME, "discount")
                    except Exception:
                        discount = None

                    try:
                        in_stock = list_flag.find_element(By.CLASS_NAME, "in_stock")
                    except Exception:
                        in_stock = None

                    try:
                        out_of_stock = list_flag.find_element(By.CLASS_NAME, "out_of_stock")
                    except Exception:
                        out_of_stock = None

                    
                    if out_of_stock:
                        produit['disponibilite'] = out_of_stock.text
                    else:
                        produit['disponibilite'] = in_stock.text
          
                    try:
                        nouveau_produit = list_flag.find_element(By.CLASS_NAME, "new")
                    except Exception:
                        nouveau_produit = None
                    
                    if discount:
                        produit['remise'] = discount.text
                    else:
                        produit['remise'] = None

                    if nouveau_produit:
                        produit['nouveau'] = nouveau_produit.text
                    else:
                        produit['nouveau'] = None
                      
                    if partner_name:
                        produit['partenaire'] = partner_name.find_element(By.TAG_NAME, 'img').get_attribute('alt')
                    else:
                        produit['partenaire'] = None
                    
                    if nom_produit:
                        produit['produit'] = nom_produit.text
                    else:
                        produit['produit'] = None

                    if description_produit:
                        produit['short_description'] = description_produit.find_element(By.TAG_NAME, 'p').get_attribute('innerHTML')
                    else:
                        produit['short_description'] = None

                    if ref_produit:
                        produit['reference'] = ref_produit.find_element(By.TAG_NAME,'span').text
                    else:
                        produit['reference'] = None
                    
                    if image_produit:
                        liste_image.append(image_produit.get_attribute('src'))
                    else:
                        produit['image'] = None

                    if len(all_image_produit) >0:
                        for img in all_image_produit:
                            if img.get_attribute('href') not in liste_image:
                                liste_image.append(img.get_attribute('href'))
                    
                    if liste_image:
                        liste_image = ', '.join(x for x in liste_image)
                    produit['image'] = liste_image
                    
                    if prix_actuel_produit:
                        produit['prix'] = prix_actuel_produit.text.replace('\n', '').strip().replace('DH', "").replace("TTC", "").strip()
                    else:
                        produit['prix'] = None

                    #############################################################################
                    #############################################################################
                    #############################################################################
                    # comparer les prix et la disponibilite iris et disway
                    disponibilite_iris = produit['disponibilite']
                    float_price_iris = float(produit['prix'].replace(' ', '').replace(',', '.').replace('\u202f', '').strip())

                    if price_disway:
                        float_price_disway = float(price_disway.replace(' ', '').replace(',', '.').replace('\u202f', '').strip())
                        if float_price_disway >= 5000:
                            prix_final_disway = float_price_disway*1.25
                        else:
                            prix_final_disway = float_price_disway*1.27
                    else:
                        pass

                    if disponibilite_iris in ('En stock', 'Quantité limitée'):
                        if disponibilite_disway:
                            if disponibilite_disway == 'Disponible' or 'Unité(s) restante(s)' in disponibilite_disway:
                                if prix_final_disway < float_price_iris:
                                    produit['prix'] = prix_final_disway
                                    produit['disponibilite'] = disponibilite_disway
                                else:
                                    pass
                            else:
                                pass
                        else:
                            pass
                    else:
                        if disponibilite_disway:
                            produit['disponibilite'] = disponibilite_disway
                            if disponibilite_disway == 'Disponible' or 'Unité(s) restante(s)' in disponibilite_disway:
                                produit['prix'] = prix_final_disway
                            else:
                                if prix_final_disway < float_price_iris:
                                    produit['prix'] = prix_final_disway
                                else:
                                    pass
                    
                    liste_all_product_details.append(produit)
                    
    df = pd.DataFrame(liste_all_product_details)
    return df
