# -*- coding: utf-8 -*-
"""
Created on Thu Oct 10 12:28:05 2019

@author: Nayana Patil
"""

import os
import stat
from os import path, remove
from time import sleep
import sys
from pathlib import Path

from selenium.webdriver import Chrome
from selenium.webdriver.chrome import webdriver as chrome_webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException

import json
import traceback
import shutil
import pandas as pd
import parsedatetime
import pytz
from pytz import timezone
from datetime import datetime

class DriverBuilder():
    def __init__(self, download_dir=None, headless=False, driver_path = "/code/chromedriver"): # driver_path = os.path.join(os.getcwd(), "drivers/chromedriver")
        try: 
#            print("making tmp directory for saving csvs", download_dir)
            os.makedirs(download_dir)
        except FileExistsError:
            pass
        
        self.download_dir = download_dir
        self.headless = headless
        self.driver_path = driver_path
        
        chrome_options = chrome_webdriver.Options()
        if download_dir:
            prefs = {'download.default_directory': download_dir,
                     'download.prompt_for_download': False,
                     'download.directory_upgrade': True,
                     'safebrowsing.enabled': False,
                     'safebrowsing.disable_download_protection': True}

            chrome_options.add_experimental_option('prefs', prefs)

        if headless:
            chrome_options.add_argument("--headless")
            
        chrome_options.add_argument("start-maximized") # open Browser in maximized mode
        chrome_options.add_argument("disable-infobars") # disabling infobars
        chrome_options.add_argument("--disable-extensions") # disabling extensions
        chrome_options.add_argument("--disable-gpu") # applicable to windows os only
        chrome_options.add_argument("--disable-dev-shm-usage") # overcome limited resource problems
        chrome_options.add_argument("--no-sandbox") # Bypass OS security model
        
        chrome_options.add_argument("--enable-javascript")
#        chrome_options.add_argument("--disable-popup-blocking")
            
        self.chrome_options = chrome_options
    
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args, **kwargs):
        self.close()
        
    def open(self):
        if sys.platform.startswith("win") and not self.driver_path.endswith('.exe') and not self.driver_path.lower() == 'default':
            self.driver_path += ".exe"
            
#        print("Using driver path: {}".format(self.driver_path))
        
        if self.driver_path.lower() == 'default':
            self.driver = Chrome(chrome_options=self.chrome_options)
        else:
            self.driver = Chrome(chrome_options=self.chrome_options, executable_path=str(Path(self.driver_path)))
        
        if self.headless:
            self.enable_download_in_headless_chrome(self.driver, self.download_dir)
            
        self.driver.set_window_size(1920, 1080)
        
    def close(self):
        self.driver.quit()
        
    def enable_download_in_headless_chrome_old(self):
        # downloading files in headless mode doesn't work!
        # file isn't downloaded and no error is thrown
        #add missing support for chrome "send_command"  to selenium webdriver
        # https://bugs.chromium.org/p/chromium/issues/detail?id=696481#c39
        self.driver.command_executor._commands["send_command"] = ("POST", '/session/{}/chromium/send_command'.format(self.driver.session_id))
        params = {
            'cmd': 'Page.setDownloadBehavior',
            'params': {'behavior': 'allow', 'downloadPath': self.download_dir}
        }
        self.driver.execute("send_command", params)

    def enable_download_in_headless_chrome(self, driver, download_dir):
        """
        there is currently a "feature" in chrome where
        headless does not allow file download: https://bugs.chromium.org/p/chromium/issues/detail?id=696481
        This method is a hacky work-around until the official chromedriver support for this.
        Requires chrome version 62.0.3196.0 or above.
        """

        # add missing support for chrome "send_command"  to selenium webdriver
        driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')

        params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
        command_result = driver.execute("send_command", params)
        print("response from browser:")
        for key in command_result:
            print("result:" + key + ":" + str(command_result[key]))
   

def get_region_urls(wd, region):
        search_input = wd.driver.find_element_by_id('advisors-filter-location-input')
        search_input.clear()
        search_input.send_keys(region)
        wd.driver.implicitly_wait(5)
        search_input.send_keys(u'\ue007')
        wd.driver.implicitly_wait(5)
        search_input.send_keys(u'\ue007')
        print('in the region page')
    
#def go_next_page():
#    try:
#        next_button = wd.driver.find_element_by_class_name('is-dormant')
#    except:
#        advisor_df, number_pages = get_advisor_url(wd, region_url)
#        next_button = wd.driver.find_element_by_class_name('pagination-next')
#        next_button.click()
#    
    
#def get_advisor_url_pagination():
#    temp_advisor_urls=[]
#    temp_advisors=[] 
#    advisor_names = wd.driver.find_elements_by_class_name('advisors-result-card-brand-image')
#    advisor_links = wd.driver.find_elements_by_class_name('advisors-result-card-link')
#    for i in range(len(advisor_names)):
#        temp_advisors.append(advisor_names[i].get_attribute('alt'))
#        temp_advisor_urls.append(advisor_links[i].get_attribute('href'))
    
#    return pd.DataFrame({'Advisor_url': temp_advisor_urls, 'Advisor': temp_advisors})   
  
def pagination(wd, n_retries = 0, retry_limit = 20):
    try:
        next_button = wd.driver.find_element_by_xpath("//button[@class='pagination-direction pagination-next']")
        next_button.click()
    except NoSuchElementException:
        pass
    except ElementNotInteractableException as e:
        sleep(2)
        print("Retry #{}: Element not interactable.".format(n_retries))
        if n_retries >= retry_limit:
            raise e
        pagination(wd, n_retries + 1)
    sleep(2)
  
def get_advisor_url(wd, first):
    advisor_urls=[]
    advisors=[] 
    sleep(5)
    advisor_names = wd.driver.find_elements_by_class_name('advisors-result-card-brand-image')
    advisor_links = wd.driver.find_elements_by_class_name('advisors-result-card-link')
    search_result_batch = wd.driver.find_element_by_class_name('searchfilterresults-advisors')
    wd.driver.implicitly_wait(5)
    search_results = wd.driver.find_element_by_class_name('advisor-search-tally')
    search_results_p = search_results.find_element_by_tag_name('p')
    search_result_total = search_results_p.text
    search_result_total = search_result_total.split(' ')
    search_result_batch = search_result_batch.get_attribute('data-global-search-batch')
    advisor_pages = int(search_result_total[3]) / int(search_result_batch)
    for i in range(len(advisor_names)):
        if '/accountant/' in advisor_links[i].get_attribute('href').lower():
            advisors.append(advisor_names[i].get_attribute('alt'))
            advisor_urls.append(advisor_links[i].get_attribute('href'))
    
    advisor_data=dict()
    advisor_data['advisor_url_df']= pd.DataFrame({'Advisor_url': advisor_urls, 'Advisor': advisors})
    advisor_data['page_numbers'] = round(advisor_pages)
    print('page numbers'+ str(round(advisor_pages)))
    return advisor_data


def get_advisor_apps(wd, advisor_df, location, page, Current_page_url):
    apps_alt=[]
    apps_advisors = []
    advisor_urls = advisor_df.Advisor_url
    for j in range(len(advisor_urls)):
#        print("Region: '{region}', Page: '{page}', Advisor: '{advisor}'".format(region = location, page = page, advisor = advisor_df.iloc[j].Advisor))
        wd.driver.get(advisor_df.iloc[j].Advisor_url)
        apps = wd.driver.find_elements_by_class_name('advisors-profile-experience-app-icon')
        for i in range(len(apps)):
            apps_advisors.append(advisor_df.iloc[j].Advisor)
            apps_alt.append(apps[i].get_attribute('alt'))
            
    wd.driver.get(Current_page_url)
    return pd.DataFrame({'city': location, 'Advisors': apps_advisors, 'App': apps_alt, 'page': page})
          

def search_by_region(wd, base_url, region):
    
    wd.driver.get(base_url)
    sleep(5)
    search_input = wd.driver.find_element_by_id('advisors-filter-location-input')
    search_input.send_keys(Keys.CONTROL + "a");
    search_input.send_keys(Keys.DELETE);
    search_input.send_keys(region)
    sleep(5)
    search_input.send_keys(u'\ue007')
    search_input_text = search_input.get_attribute("value")
    split_text = search_input_text.strip().split(',')
    split_text = list(split_text)
    country = split_text[len(split_text)-1]
    city = split_text[0]
    if len(split_text) > 2:
        state = split_text[1]
    else:
        state = 'null'
    sleep(5)
    search_input.send_keys(u'\ue007')
    sleep(5)
    Current_page_url = wd.driver.current_url
    return search_input_text

def write_csv(df, fp, fp_exists_mode = 'a', index = False, header = False):
    
    def align_cols(df, fp):
        check_df = pd.read_csv(fp, nrows = 1)
        check_df = check_df.append(df, ignore_index = True)
        return check_df[1:]
    
    if not fp.exists():
        df.to_csv(fp, index = index)
    else:
        df = align_cols(df, fp)
        df.to_csv(fp, mode = fp_exists_mode, index = index, header = header)


def main(params, datadir = '/data/', download_dir = '/tmp/downloads/', headless=True, driver_path = "default"):
    
#    os.system("export PYTHONIOENCODING=utf8")

    outdir = Path(datadir) / 'out/tables/'
    
    if sys.platform.startswith("win"):
        download_path = os.getcwd() + '\\' + download_dir
    else:
        download_path = download_dir
       
        #start new
    base_url = params.get('base_url', "https://www.xero.com/nz/advisors/find-advisors/")
    regions = params.get('regions')#use this format for optional arguments
#    filename = params.get('filename')
    for region in regions:
            wd = DriverBuilder(headless= headless, download_dir=download_dir, driver_path = driver_path)
            with wd:# USE wd.open() instead to open window and wd.close() to close window
            location = search_by_region(wd, base_url, region)
            Current_page_url = wd.driver.current_url
            advisor_data = get_advisor_url(wd, 0)
            advisor_df = advisor_data['advisor_url_df']
            page_number = advisor_data['page_numbers']
            for k in range(1, page_number):
                wd.driver.delete_all_cookies()
                apps_df = get_advisor_apps(wd, advisor_df, location, k, Current_page_url)
                write_csv(df = apps_df, fp = Path(outdir) / (region + '.csv'))
                pagination(wd)
                Current_page_url = wd.driver.current_url
                advisor_data = get_advisor_url(wd, k)
                advisor_df = advisor_data['advisor_url_df']
     
def testing():
        os.chdir("D:/xero_apps")
        with open("data/config.json") as f:
            cfg = json.load(f)
        params = cfg["parameters"]
        headless = False
        datadir = 'data/'
        download_dir = "tmp\\downloads"
        driver_path = os.path.join(os.getcwd(), "drivers/chromedriver")
        
if __name__ == "__main__":
    with open("/data/config.json") as f:
        cfg = json.load(f)
    try:
        main(cfg["parameters"])
    except Exception as err:
        print(err)
        traceback.print_exc()
        sys.exit(1)
        
#print("main.py finished.")

