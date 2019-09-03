# -*- coding: utf-8 -*-
"""Funções para coleta e processamento de cupons"""

import requests 
from bs4 import BeautifulSoup
import threading

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1)'\
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
}

# chama todas as funções de coleta 
def get_discounts():
    ''' 
    discountsglobal pode bloquear as requisições 
    Comentar linha caso aconteça
    '''
    # lista de funções de coleta
    site_functions = [
            get_all_onlinetutorials_links,
            get_all_discountsglobal_links, 
            get_all_learnviral_links,
    ]

    thread_list = []
    for f in site_functions:
        thread = SiteThread(f)
        thread.start()
        thread_list.append(thread)
    coupons_list = []
    for thread in thread_list:
        coupons_list = coupons_list + thread.join()
    
    # remove cupons iguais e que não possuem desconto
    coupons_dict = {}
    for coupon_dict in coupons_list:
        for url,name in coupon_dict.items():
            if 'https://www.udemy.com/course/' and \
                '?couponCode=' not in url: # não possui desconto
                continue
            coupons_dict[url.strip()] = name.strip()
    return coupons_dict

# Classe thread para retornar resultados das funções de coleta
class SiteThread(threading.Thread): 
    def __init__(self,func,args=None):
        threading.Thread.__init__(self)
        self.kwargs = args
        self.func = func
        self.result = ""

    def run (self):
        if self.kwargs:
            self.result = self.func(**self.kwargs)
        else:
            self.result = self.func()
                  
    def join(self):
        threading.Thread.join(self)
        return self.result
    
# função de coleta 1
def get_all_discountsglobal_links(): 
    coupons = []
    url = "http://udemycoupon.discountsglobal.com/coupon-category/free-2/"
    try:
        r = requests.get(url,headers=headers)
        soup = BeautifulSoup(r.text,'html5lib')
        for div in soup.findAll('div',{'class':'item-panel'}):
            name = div.find('h3').find('a').text 
            name = name.replace('Discount: 100% off – ','')
            name = name.replace('Discount: 75% off – ','')
            name = name.replace('100% off ','')
            url = div.find('div',{'class':'link-holder'}).find('a').get('href') 
            coupons.append({url:name})
    except Exception as e:
        print('get_all_discountsglobal_links',e)      
    return coupons

# função de coleta 2
def get_all_learnviral_links(): 
    coupons = []
    url = "https://udemycoupon.learnviral.com/coupon-category/free100-discount/"
    try:
        r = requests.get(url,headers=headers)
        soup = BeautifulSoup(r.text,'html5lib')
        titles = [
            title.text.replace('[Free]','') for title in \
            soup.findAll('h3',{'class':'entry-title'})
        ]
        urls = [
            a.get('href') for a in \
            soup.findAll('a',{'class':'coupon-code-link btn promotion'})
        ]
        coupons = [{url:name} for (url,name) in zip(urls,titles)]
    except Exception as e:
        print('get_all_learnviral_links',e)      
    return coupons

# função de coleta 3
def get_all_onlinetutorials_links(): 
    coupons = []
    url = "https://onlinetutorials.org"
    try:
        r = requests.get(url,headers=headers)
        soup = BeautifulSoup(r.text,'html5lib')
        titles = [
            title.find('a').text for title in \
            soup.findAll('h3',{'class':'entry-title'})
        ]
        urls = [
            a.get('href') for a in \
            soup.findAll('a',{'class':'coupon-code-link button promotion'})
        ]
        coupons = [{url:name} for (url,name) in zip(urls,titles)]
    except Exception as e:
        print('get_all_onlinetutorials_links',e)    
    return coupons