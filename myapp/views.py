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

    # recuperer les liens de tous les categories
    response = requests.get(base_url)
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


def ajax_calls(request):

    if request.method == 'POST':
        received_json_data = json.loads(request.body)
        action = received_json_data['action']

        if action == "scraper-pages":
            liste_to_scrape = received_json_data['liste_to_scrape']
            data = scrape_liste_categrie_selinieum(liste_to_scrape)
            # data = scrape_liste_categrie_bs4(liste_to_scrape)
            excel_file = data.to_excel("output.xlsx")
            return JsonResponse(data={}, safe=False)
            
        return JsonResponse(data={}, safe=False)

def download_file(request):
    # Generate the file contents
    file_contents = "This is the file content."

    # Create an HttpResponse with appropriate headers for file download
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="example.xlsx"'
    return response

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

                    driver.get(url_produit)
                    time.sleep(10)

                    prix_actuel_produit = driver.find_element(By.CLASS_NAME, "current-price-value")
                    ref_produit = driver.find_element(By.CLASS_NAME, "product-reference")
                    image_produit = driver.find_element(By.CLASS_NAME, "no-sirv-lazy-load")

                    all_image_produit = driver.find_elements(By.CLASS_NAME, "magictoolbox-selector")
                    description_produit = driver.find_element(By.CLASS_NAME, "product-information")

                    partner_name = driver.find_element(By.CLASS_NAME, "manufacturer_image")
                    nom_produit = driver.find_element(By.CLASS_NAME, "productpage_title")

                    try:
                        attachment = driver.find_element(By.CLASS_NAME, "attachment")

                        if attachment:
                            s = attachment.find_element(By.TAG_NAME, "a").get_attribute('href')
                            produit['attachment'] = s
                        else:
                            print("no attachement", nom_produit.text)
                    except:
                        pass
                    full_description = driver.find_element(By.CLASS_NAME, "product-description")

                    list_flag = driver.find_element(By.CLASS_NAME, "product-flags.js-product-flags")
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

                    
                    # if in_stock:
                    #     if in_stock.text:
                    #         produit['disponibilite'] = in_stock.text
                    #     else:
                    #         if out_of_stock:
                    #             produit['disponibilite'] = out_of_stock.text
                      

                    if partner_name:
                        produit['partenaire'] = partner_name.find_element(By.TAG_NAME, 'img').get_attribute('alt')
                    else:
                        produit['partenaire'] = None
                    
                    if nom_produit:
                        produit['produit'] = nom_produit.text
                    else:
                        produit['produit'] = None

                    if full_description:
                        produit['full_description'] = full_description.get_attribute('innerHTML')
                    else:
                        produit['full_description'] = None

                    if description_produit:
                        produit['short_description'] = description_produit.get_attribute('innerHTML')
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
                    produit['image'] = liste_image
                    
                    if prix_actuel_produit:
                        produit['prix'] = prix_actuel_produit.text.replace('\n', '').strip().replace('DH', "").replace("TTC", "").strip()
                    else:
                        produit['prix'] = None
                    
                    liste_all_product_details.append(produit)
                    

                                
            
    df = pd.DataFrame(liste_all_product_details)
    return df
    



