
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 10 12:28:05 2019

@author: Nayana Patil
"""

import os
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
    
    def __init__(self, download_dir=None, headless=False, driver_path = os.path.join(os.getcwd(), "drivers/chromedriver")):
        try:
            print("making tmp directory for saving csvs", download_dir)
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
            
        self.chrome_options = chrome_options
    
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args, **kwargs):
        self.close()
        
    def open(self):
        if sys.platform.startswith("win"):
            self.driver_path += ".exe"
        
        self.driver = Chrome(chrome_options=self.chrome_options, executable_path=self.driver_path)
        
        if self.headless:
            self.enable_download_in_headless_chrome(self.driver, self.download_dir)
            
        self.driver.set_window_size(1920, 1080)
        
    def close(self):
        self.driver.quit()

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
            
    def login(self, creds, url='https://app.corecon.com/dist/index.html#/login', element_ids = {"company_id": "companyid", "username": "username", "#password": "password"}):
        # Change this function to your needs and add other functions, etc...
        print("Logging in")
        
        # CHANGE THIS METHOD
        
        self.driver.get(url)
        sleep(10)
        
        for key in creds.keys():
            sleep(1)
            field = self.driver.find_element_by_id(element_ids[key])
            field.clear()
            field.send_keys(creds[key])
        
        field.send_keys(Keys.RETURN)
        sleep(10)
        
        title = self.driver.title
        if "Corecon" not in title:
            raise AuthenticationError(
                ("Probably didn't authenticate sucesfully. "
                 "The title says '{}'. Please check your credentials.").format(title))
        
        print("Logged in")
        
    def get_report(
            self,
            url = '',
            projects = ''
            ):
        
        # DELETABLE
        
        print("get_report")
        
#        url = "https://app.corecon.com/OldUI/Dashboards/DashboardMain.aspx"
        url = "https://www.xero.com/nz/advisors/"
        self.driver.get(url)
        sleep(5)
        
        self.select_projects(url = url, projects = projects)
        
        export_button = self.driver.find_element_by_id("lnkExport")
        export_button.click()
        
        final_export_button = self.driver.find_element_by_xpath("//*[contains(text(), 'Export to Excel')]")
        final_export_button.click()
        
#        count = 0 #for debug
#        limit = 20
        while True:
            report_path = glob_csv(self.download_dir)
            files = []
            for i in range(len(report_path)):
                file = report_path[i]
                if file.name.endswith('.csv'):
                    files.append(file)
                else:
                    continue
#            if count > limit: #for debug
#                raise ValueError("Looping too many times") #for debug
            if not files:
                print("Waiting for the report to be downloaded")
                sleep(5)
            else:
                print("Report downloaded to ", files)
                sleep(3)
                break
        
    def select_projects(
            self,
            url = '',
            projects = []
            ):
        
        #DELETABLE
        
        print("select_projects")
        
        url = url.replace('.aspx', 'Filter.aspx')
        self.driver.get(url)
        sleep(5)
        
        project_filter_type_element = self.driver.find_element_by_name("ctl00$ContentPlaceHolder1$ddlProjectFilterType")
        select = Select(project_filter_type_element)
        select.select_by_visible_text("Multiple Active Only")
        sleep(2)
        
        if type(projects) != list:
            print("Logging: Object 'projects' is not of type 'list'. Defaulting to all projects.")
            check_all_projects_element = self.driver.find_element_by_id("chkAllProjects")
            check_all_projects_element.click()
        else:
            raise ValueError("Specific project selection not implemented yet")
            
        sleep(3)
        
        submit_button = self.driver.find_element_by_id("ctl00_ContentPlaceHolder1_btnSelect__3")
        sleep(1)
        submit_button.click()
        
        sleep(5)
    
    def _locate_export_button(self, element_id = "reportoptions"):
#        print("Looking for export button")
        btn = self.driver.find_element_by_id(element_id)
        return(btn)
    
def glob_csv(csv_dir):
    return list(Path(csv_dir).glob("*.csv*"))

def robotize_date(dt_str, tz = "Pacific/Auckland"):
    if dt_str is None:
        return
    cal = parsedatetime.Calendar()
    t_struct, status = cal.parseDT(dt_str, tzinfo = timezone(tz))
    if status != 1:
        raise ValueError("Couldn't convert '{}' to a datetime".format(dt_str))
    print(t_struct)
    d = t_struct.date()
    converted = str(d)
    print("Converted", dt_str, "to", converted)
    return d

def clean_file(download_dir, skip_rows = 0):
    #DELETABLE
    paths = glob_csv(download_dir)
    for file in paths:
#        df_header = pd.read_csv(file, chunksize = 1, nrows = skip_rows)
        df = pd.read_csv(file, skiprows = skip_rows)
        df.to_csv(file, index = False)

def move_file(download_dir, outdir, filenames = None):
    #DELETABLE
    paths = glob_csv(download_dir)
    for i in range(len(paths)):
        path = paths[i]
        if filenames is None:
            filename = path.name
            split = filename.split('.')
            filename = '.'.join([split[0],split[len(split)-1]])
        else:
            filename = filenames[i].replace(' ', '_')
        print("Moving: " + str(path) + " to " + str(outdir / filename))
        shutil.move(path, outdir / filename)
        
        
def get_region_urls(wd, region):
        search_input = wd.driver.find_element_by_id('advisors-filter-location-input')
        search_input.clear()
        search_input.send_keys(region)
        wd.driver.implicitly_wait(5)
        search_input.send_keys(u'\ue007')
        search_input.send_keys(u'\ue007')

#    contents = wd.driver.find_elements_by_tag_name('a')
#    region_urls = []
#    region_names = []
#    for content in contents:
#        text= 'https://www.xero.com/nz/advisors/find-advisors/?type=advisors';
#        if text in content.get_attribute('href'):
#            
#            link = content.get_attribute('href')
#            region_urls.append(link)
#            
#            name = content.text
#            region_names.append(name)
#        
#    return pd.DataFrame({'Region_URL': region_urls, 'Region_Name': region_names})
    
def go_next_page():
    try:
        next_button = wd.driver.find_element_by_class_name('is-dormant')
    except:
        advisor_df, number_pages = get_advisor_url(wd, region_url)
        next_button = wd.driver.find_element_by_class_name('pagination-next')
        next_button.click()
    
    
def get_advisor_url_pagination():
    temp_advisor_urls=[]
    temp_advisors=[] 
    advisor_names = wd.driver.find_elements_by_class_name('advisors-result-card-brand-image')
    advisor_links = wd.driver.find_elements_by_class_name('advisors-result-card-link')
    for i in range(len(advisor_names)):
        temp_advisors.append(advisor_names[i].get_attribute('alt'))
        temp_advisor_urls.append(advisor_links[i].get_attribute('href'))
    
    return pd.DataFrame({'Advisor_url': temp_advisor_urls, 'Advisor': temp_advisors})   
  
def pagination(wd, n_retries = 0, retry_limit = 10):
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
        
        
        
        
#        print("element not found")
#        next_button = None
#        count = 0
#        count_timeout_limit = 10
#        while next_button is None:
#            sleep(2)
#            try:
#                next_button = wd.driver.find_element_by_xpath("//button[@class='pagination-direction pagination-next']")
#                next_button.click()
#                print("clicked")
#            except ElementNotInteractableException:
#                count += 1
#                print("Retry #{}: element still not found".format(count))
#            if count >= count_timeout_limit:
#                break
    
def get_advisor_url(wd, region_url, first):
    advisor_urls=[]
    advisors=[] 
    print("get_advisor "+str(first))
    print("get_advisor "+region_url)
    
    wd.driver.get(Current_page_url)
    
    advisor_names = wd.driver.find_elements_by_class_name('advisors-result-card-brand-image')
    advisor_links = wd.driver.find_elements_by_class_name('advisors-result-card-link')
    search_result_batch = wd.driver.find_element_by_class_name('searchfilterresults-advisors')
    search_results = wd.driver.find_element_by_xpath("/html/body/main/div[2]/div[2]/div[1]/div/div/div/div[1]")
    search_result_total = search_results.text
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
#    advisor_data['advisor_page'] = Current_page_url
#    print("advisor_page"+advisor_data['advisor_page'])
        
    return advisor_data


def get_advisor_apps(wd, advisor_df, location, page, Current_page_url):
    apps_alt=[]
    apps_advisors = []
    advisor_urls = advisor_df.Advisor_url
    for j in range(len(advisor_urls)):
        print("Region: '{region}', Page: '{page}', Advisor: '{advisor}'".format(region = location, page = page, advisor = advisor_df.iloc[j].Advisor))
        wd.driver.get(advisor_df.iloc[j].Advisor_url)
        apps = wd.driver.find_elements_by_class_name('advisors-profile-experience-app-icon')
        for i in range(len(apps)):
            apps_advisors.append(advisor_df.iloc[j].Advisor)
            apps_alt.append(apps[i].get_attribute('alt'))
             
    wd.driver.get(Current_page_url)
    return pd.DataFrame({'city': location, 'Page':page,'Advisors': apps_advisors, 'App': apps_alt,})
          

def search_by_region(wd, base_url, region):
    wd.driver.get(base_url)
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
    return search_input_text


def main(params, datadir = '/data/', download_dir = '/tmp/downloads/', headless=True):
    
    outdir = Path(datadir) / 'out/tables/'
    
    if sys.platform.startswith("win"):
        download_path = os.getcwd() + '\\' + download_dir
    else:
        download_path = download_dir
       
        #start new
    base_url = params.get('base_url', "https://www.xero.com/nz/advisors/find-advisors/")
    regions = params.get('regions')#use this format for optional arguments
    wd = DriverBuilder(headless= headless, download_dir=download_dir)
    with wd:# USE wd.open() instead to open window and wd.close() to close window
        xero_apps_df = pd.DataFrame()
        for region in regions:
            location = search_by_region(wd, base_url, region)
            Current_page_url = wd.driver.current_url
            
            advisor_data = get_advisor_url(wd, region, 0)
            advisor_df = advisor_data['advisor_url_df']
            page_number = advisor_data['page_numbers']
#            advisor_pagination_url = advisor_data['advisor_page']
            for k in range(1, page_number):
                apps_df = get_advisor_apps(wd, advisor_df, location, k, Current_page_url)
                xero_apps_df = xero_apps_df.append(apps_df, ignore_index = True)
                
                pagination(wd)
                Current_page_url = wd.driver.current_url
                print(Current_page_url)
                advisor_data = get_advisor_url(wd, Current_page_url, k)
                advisor_df = advisor_data['advisor_url_df']
        xero_apps_df.to_csv (r'C:\Users\Nayana Patil\Github\xero-connected-app\tmp\downloads\Xero_Apps_NZ.csv', index = None, header=True)
#       
        
        
        
def testing():
    os.chdir("C:/Users/Nayana Patil/Github/xero-connected-app")
    with open("data/config.json") as f:
        cfg = json.load(f)
    params = cfg["parameters"]
    headless = False
    datadir = 'data/'
    download_dir = "tmp\\downloads"

if __name__ == "__main__":
    with open("/data/config.json") as f:
        cfg = json.load(f)
    try:
        main(cfg["parameters"])
    except Exception as err:
        print(err)
        traceback.print_exc()
        sys.exit(1)
        
print("main.py finished.")

