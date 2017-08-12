from __future__ import print_function
from urllib import request, error, parse

import requests
import os
import re
import sys
from tqdm import tqdm
from urllib.request import urlopen

categories = {
    'Ai': 'AI',
    'Ad': 'Advocacy',
    'Au': 'Audio',
    'Bm': 'Business & Marketing',
    'Cm': 'Community Management',
    'De': 'Design',
    'Es': 'eSports',
    'Ed': 'Game Career - Education',
    'Gn': 'Game Narrative',
    'In': 'Indipendent Games',
    'Lq': 'Localization - QA',
    'Mo': 'Monetization',
    'Or': 'Other',
    'Pr': 'Production',
    'Pg': 'Programming',
    'Sg': 'Serious Games',
    'Ta': 'Smartphone - Table Games',
    'On': 'Social - Online Games',
    'Vr': 'Virtual - Augmented Reality',
    'Va': 'Visual Arts'}

base_vault_url = "http://www.gdcvault.com"
gdc_url_free = 'http://www.gdcvault.com/free/gdc-17'
gdc_url_all = 'http://www.gdcvault.com/browse/gdc-17'

gdc_url = gdc_url_all

year_folder = "2017/"

ds_url = 'http://s3-2u.digitallyspeaking.com/'
xml_url = 'http://evt.dispeak.com/ubm/gdc/sf17/xml/'

login_url = 'http://gdcvault.com/api/login.php'
logout_url = 'http://gdcvault.com/logout'

# possible values 500,1300
quality = '1300'

title_reggexp = r"<title>GDC Vault - (.*)</title>"
video_item_regexp = r"session_item.*href=\"(.*)\""
video_player_regexp = r"<iframe.*player.html.xml=(.*).xml"
pdf_regexp = r"<iframe.*player.html.xml=(.*).xml"

username = ""
password = ""

logFileName = "log.txt"

savedCookies = None

def get_category_url(lbl):
    return gdc_url + '/?categories=' + lbl


def text(msg):
    print("[gdc-downloader] " + msg)


def error(message):
    print("[gdc-downloader] Error: " + message)
    sys.exit(1)


def message(msg):
    print("[gdc-downloader] Message: " + msg)


def download_file(url, name, folder):
    local_filename = folder + '/' + name
    r = requests.get(url, stream=True)

    file_size = int(r.headers['Content-Length'])

    if not os.path.exists(folder):
        os.makedirs(folder)

    if os.path.exists(local_filename):
        message(local_filename + " already exists, skipping")
        return

    #lets put it in log so if it failed we at least knew what was a last file
    with open(logFileName, "+a") as file:
        file.write("\n" + local_filename)

    with open(local_filename, 'wb') as f:
        for data in tqdm(r.iter_content(chunk_size=1024), desc=local_filename, leave=True, total=(file_size / 1024),
                         unit='KB'):
            if data:
                f.write(data)

    return local_filename


def download_url(url):
    try:
        if savedCookies is None:
            response = urlopen(url)
        else:
            response = requests.get(url, cookies=savedCookies)
    except HTTPError as e:
        error("http error: " + "\"" + str(e) + "\"")
    except URLError as e:
        error("url error (make sure you're online): " + "\"" + str(e) + "\"")

    if savedCookies is None:
        return response.read().decode('utf-8')
    else:
        return response.text


def get_video_list_urls(catUrl):
    html = download_url(catUrl)
    found = re.findall(video_item_regexp, html)
    return found


def get_video_url(link):
    html = download_url(base_vault_url + link)
    found = re.search(video_player_regexp, html)

    if not found:
        return None

    video_xml = found.group(1)
    xml = download_url(xml_url + video_xml + '.xml')

    found = re.search('(asset.*' + video_xml + '.*' + quality + '\.mp4)', xml)

    if found is not None:
        return ds_url + found.group(0)
    else:
        return None

def get_title(link):
    html = download_url(base_vault_url + link)
    found = re.search(title_reggexp, html)

    if found is not None:
        title = found.group(0)
        title = title.replace("<title>", "");
        title = title.replace("</title>", "");
        title = title.replace("GDC Vault - ", "");
        return title
    else:
        return None

def login_gdc(login, pwd):
    global savedCookies
    if login != "" and pwd != "":
        response = requests.post(login_url, data={'email': login, 'password': pwd})
        print('Login status code: ' + str(response.status_code))
        if response.status_code == 500:
            phpsession = response.cookies['PHPSESSID']    
            savedCookies = dict(PHPSESSID=phpsession)
            print("500 returned on login. Prolly logged to many times. Wait 10 minutes and try again")
            raise Exception("Bad login")
            return False
        # Set cookies
        phpsession = response.cookies['PHPSESSID']
        userHash = response.cookies['user_hash']
        savedCookies = dict(PHPSESSID=phpsession, user_hash=userHash)
    else:
        print("Credentials are empty.")
        return False
    return True

def logout_gdc():
        response = requests.get(logout_url, cookies=savedCookies)
        print('Logout status code: ' + str(response.status_code))
        cookies = None

def _main():
    # Input Validation
    print("Welcome to GDC Stealer.");
    try:
        if len(sys.argv) > 1:
            global username, password
            username = sys.argv[1]
            password = sys.argv[2]
            print("Login: " + username);
            print("Password: " + password);
        login = login_gdc(username, password)
        if login:
            global gdc_url
            gdc_url = gdc_url_all
        else:
            logout_gdc()
            print("Login Failed. Only free videos will be downloaded")
            gdc_url = gdc_url_free

        print("Downloading videos from: " + gdc_url);


        for category in categories:
            cat_url = get_category_url(category)
            video_links = get_video_list_urls(cat_url)

            for link in video_links:
                video_url = get_video_url(link)
                if video_url is not None:
                    file_name = get_title(link)

                    if  file_name is None:
                        file_name = link.split("/")[-1].replace('-', '') + '_' + link.split("/")[-2]
                    else:
                        file_name = file_name.replace('<', '')
                        file_name = file_name.replace('>', '')
                        file_name = file_name.replace(':', ' -')
                        file_name = file_name.replace('"', '')
                        file_name = file_name.replace('/', '')
                        file_name = file_name.replace('\\', '')
                        file_name = file_name.replace('|', ' -')
                        file_name = file_name.replace('?', '')
                        file_name = file_name.replace('*', '')

                    print("-------------------------------------------------------------------")
                    print("Dowloading " + file_name)
                    print("-------------------------------------------------------------------")
                    download_file(video_url, file_name + '.mp4', year_folder + categories[category])
    except Exception as inst:
        print('Exception!')
        print(type(inst))
        print(inst.args)
        print(inst)
        logout_gdc()

    logout_gdc()


if __name__ == "__main__":
    _main()