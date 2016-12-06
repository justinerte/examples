#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, request, url_for,render_template,redirect,make_response,send_file

import os
import shutil
from os import path
from wordcloud import WordCloud
from crawler import Crawler
from engine import SearchEngine

app = Flask(__name__)

class Wordcloud(object):
    link = ""
    img = ""

    def __init__(self, link, img):
        self.link = link
        self.img = img

def main():

	S = SearchEngine()
	S.build_index('article')

	while True:
		words = raw_input('input search key words (\'q\' to quit): ')
		if words != 'q':
			words = [w for w in words.split(' ') if w != '']
			S.search(words)
		else:
			break

def cloudPicSaver():
    cloudPicsDirectory = './static/images/cloudPics/'
    if not os.path.exists(cloudPicsDirectory):
        os.mkdir(cloudPicsDirectory)

    for file in os.listdir('./article'):
        if file.endswith(".txt"):
            text = open(path.join('./article', file)).read()
            wordcloud = WordCloud().generate(text)
            wordcloud.to_file(cloudPicsDirectory+file[:-4]+'.png')

def prepareDocs():
    if os.path.exists('./article'):
        shutil.rmtree('./article')
    if os.path.exists('./pages'):
        shutil.rmtree('./pages')
    if os.path.exists('./static/images/cloudPics/'):
        shutil.rmtree('./static/images/cloudPics/')
    print "not exist article folder and preparing......"
    C = Crawler(init_page='https://news.google.com',save_html_to='pages',save_txt_to='article')
    C.crawl(workers=4,pages=300)
    os.mkdir('./static/images/cloudPics/')
    cloudPicSaver()
    print "Article folder preparing done!"


def getLink(file):
    for line in open(file):
        rec = line.strip()
        # print rec
        if (rec.startswith('http://'))or (rec.startswith('https://')) :
            return line

@app.route("/")
def hello():
    return render_template('index.html')

@app.route("/all")
def getAllNews():
    list=[]
    img_src="../static/images/cloudPics/"
    article_src="./article/"
    cloudPics_dir = "./static/images/cloudPics/"

    for file in os.listdir(cloudPics_dir):
        obj = Wordcloud(getLink(article_src+file[:-4]+'.txt'), img_src+file)
        if getLink(article_src+file[:-4]+'.txt') != None:
            list.append(obj)
    return render_template('searchresult.html',john=list)

@app.route("/search", methods=['POST', 'GET'])
def getKeyword():
    search_num = 0
    keyWord = request.form['searchResult']
    # print keyWord[1]
    keyWord = str(keyWord)
    keyWord = keyWord.lower()
    keyWord = keyWord.decode('utf-8')
    keyWord_test = keyWord.split()
    # print len(keyWord_test)
    article_src="./article/"
    cloudPics_dir = "./static/images/cloudPics/"
    img_src="../static/images/cloudPics/"
    # list = []
    list_result =[] 
    for file in os.listdir(article_src):
        content = open(article_src+file).read()
        content = content.decode('utf-8')
        # print content 
        # print len(keyWord_test)
        cnt_len = len(keyWord_test)
        for cnt_keyword in range(0,cnt_len):
            keyWord_test[cnt_keyword] = keyWord_test[cnt_keyword].decode('utf-8')
            print keyWord_test[cnt_keyword]
            if keyWord_test[cnt_keyword] in content:
                # print "hello"
                # print keyWord
                # print file
                print getLink(article_src+file)
                # print obj
                obj = Wordcloud(getLink(article_src+file[:-4]+'.txt'), img_src+file[:-4]+'.png')
                # print obj
                if getLink(article_src+file[:-4]+'.txt') != None:
                    list_result.append(obj)
                    # print list
    list_result = list(set(list_result))
    # for search_num in  range(1,5):
    #     list_result.append(list[search_num])
    # return render_template('searchresult.html',john=list_result)  
    # print "hello"
    # print list 
    return render_template('searchresult.html',john=list_result)


if __name__ == '__main__':
    if not os.path.exists('article'):
        print "not exist article folder and preparing......"
        prepareDocs()
        print "Done!"
    else:
        print "Documents folder existed!!"
    app.run(debug=True)
