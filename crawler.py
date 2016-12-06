#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
import re
import tempfile
import os, sys, time
import multiprocessing as mp
import Queue
from multiprocessing.sharedctypes import Value

# global variables
RE_URL = re.compile('(?:href=")(?P<url>http[s]?://[^"]+.html)"')
RE_TITLE = re.compile('<title>(?P<title>[^<]+)</title>')
RE_ARTICLE = re.compile('<p>(?P<para>.*?)</p>')
RE_XML = re.compile('<[^>]*>')
RE_TEXT = re.compile('[^a-zA-Z]')

# helper functions
def WriteToFile(fname, content):
	with open(fname, 'w') as f:
		f.write(content)

def ReadFromFile(fname):
	content = ''
	if os.path.isfile(fname):
		with open(fname, 'r') as f:
			content = f.read()
	return content


# stop control
RUNNING = Value('i', 0, lock=True)
def alive():
	return RUNNING.value > 0


class URLDatabase:

	''' Record what URL we have crawled, so as to
		avoid crawling the second time.

		Used by URLExtractor.
	'''

	__db = set()
	__lock = mp.Lock()

	def __init__(self):
		pass

	def insert(self, url):
		if url in URLDatabase.__db:
			return False
		succeed = False
		URLDatabase.__lock.acquire()
		if url not in URLDatabase.__db:
			URLDatabase.__db.add(url)
			succeed = True
		URLDatabase.__lock.release()
		return succeed


class PageDownloader(mp.Process):

	''' Download page and save to save_path/xxx.html

		Used by Crawler.
	'''

	def __init__(self, _id, u_in, f_outs, save_path):
		super(PageDownloader, self).__init__()
		self.in_url = u_in
		self.out_files = f_outs
		self.id = _id
		self.save_path = save_path

	def get_title(self, html):
		html = html.replace('\n', '')
		t = RE_TITLE.findall(html)
		if len(t) == 0:
			return None
		else:
			return t[0].strip()

	def run(self):
		global RUNNING

		while alive():
			try:
				url = self.in_url.get(True, 1)

				content = urllib.urlopen(url).read()
				title = self.get_title(content)
				if title != None:
					path = '{}/{}_{}.html'.format(self.save_path, RE_TEXT.sub('_', title[0:20]), tempfile.mktemp(dir=''))
					title_result = '\n'.join([title, url, content])
					WriteToFile(path,title_result)
					RUNNING.value -= 1
					for of in self.out_files:
						of.put(path)
						of.task_done()
					print 'PageDownloader [{}] - downloaded \'{}...\', saved to ...{}'.format(self.id, url[:20], path[-20:])
				else:
					print 'PageDownloader [{}] - abandon \'{}\''.format(self.id, title)
			except Queue.Empty:
				print 'PageDownloader [{}] no input'.format(self.id)
				continue
			except:
				print 'PageDownloader [{}] unexpected error:', sys.exc_info()
				break


class URLExtractor(mp.Process):

	''' Extract urls from html files, push to queue.

		Used by Crawler.
	'''

	def __init__(self, _id, f_in, u_out):
		super(URLExtractor, self).__init__()
		self.in_file = f_in
		self.out_url = u_out
		self.db = URLDatabase()
		self.id = _id

	def run(self):
		while True:
			try:
				fname = self.in_file.get(True, 1)
			
				content = open(fname, 'r').read()
				count = 0
				for url in RE_URL.findall(content):
					if self.db.insert(url):
						self.out_url.put(url)
						self.out_url.task_done()
						count += 1
				print 'URLExtractor [{}] - {} new url from {}'.format(self.id, count, fname)
			except Queue.Empty:
				print 'URLExtractor [{}] - no input'.format(self.id)
				if alive():
					continue
				else:
					break
			except:
				print 'URLExtractor [{}] unexpected error:', sys.exc_info()
				break


class ArticleExtractor(mp.Process):

	''' Extract articles from html files in save_path/xxx.txt

		Used by Crawler.
	'''

	def __init__(self, _id, f_in, save_path):
		super(ArticleExtractor, self).__init__()
		self.in_file = f_in
		self.id = _id
		self.save_path = save_path

	def text_filter(self, text):
		return RE_TEXT.sub(' ', RE_XML.sub('', text))

	def run(self):
		while True:
			try:
				fname = self.in_file.get(True, 1)

				content = ReadFromFile(fname)
				paras = [self.text_filter(p) for p in RE_ARTICLE.findall(content)]
				article = '\n'.join(content.split('\n')[:2] + paras)
				article = article.lower()
				path = '{}/{}.txt'.format(self.save_path, fname[fname.rfind('/')+1:fname.rfind('.')])
				# path_original = '{}/{}_original.txt'.format(self.save_path, fname[fname.rfind('/')+1:fname.rfind('.')])
				WriteToFile(path, article)
				# WriteToFile(path_original, article)
				print 'ArticleExtractor [{}] - new article {} [{}]'.format(self.id, path, fname)
			except Queue.Empty:
				print 'ArticleExtractor [{}] - no input'.format(self.id)
				if alive():
					continue
				else:
					break
			except:
				print 'ArticleExtractor [{}] unexpected error:', sys.exc_info()
				break


class Crawler:

	''' Crawl web pages from internet.
	'''

	def __init__(self, init_page, save_html_to, save_txt_to):
		self.url_queue = mp.JoinableQueue(1000)
		self.page_queue1 = mp.JoinableQueue()
		self.page_queue2 = mp.JoinableQueue()
		self.html_path = save_html_to
		self.txt_path = save_txt_to
		try:
			os.mkdir(save_html_to)
		except:
			pass
		try:
			os.mkdir(save_txt_to)
		except:
			pass

		self._load()
		if self.url_queue.empty():
			self.url_queue.put(init_page)
			self.url_queue.task_done()

	# save progress
	def _save(self):
		urls = []
		while not self.url_queue.empty():
			urls.append( self.url_queue.get() )
		WriteToFile('~url', '\n'.join(urls))
		p1 = []
		while not self.page_queue1.empty():
			p1.append( self.page_queue1.get() )
		WriteToFile('~p1', '\n'.join(p1))
		p2 = []
		while not self.page_queue2.empty():
			p2.append( self.page_queue1.get() )
		WriteToFile('~p2', '\n'.join(p2))

	# load progress
	def _load(self):
		urls = ReadFromFile('~url').split('\n')
		for url in urls:
			if url != '' and not self.url_queue.full():
				self.url_queue.put(url)
				self.url_queue.task_done()
		p1 = ReadFromFile('~p1').split('\n')
		for p in p1:
			if p != '':
				self.page_queue1.put(p)
				self.page_queue1.task_done()
		p2 = ReadFromFile('~p2').split('\n')
		for p in p2:
			if p != '':
				self.page_queue2.put(p)
				self.page_queue2.task_done()

	# main procedure
	def crawl(self, workers, pages):
		global RUNNING

		downloader_count = max(0, workers)
		urlextractor_count = 1
		articleextractor_count = 1
		RUNNING.value = max(0, pages)

		# create workers
		page_downloaders = [
			PageDownloader(i, self.url_queue,
				[self.page_queue1, self.page_queue2],
				self.html_path)
			for i in xrange(downloader_count)]
		url_extractors = [
			URLExtractor(i, self.page_queue1, self.url_queue)
			for i in xrange(urlextractor_count)]
		article_extractors = [
			ArticleExtractor(i, self.page_queue2, self.txt_path)
			for i in xrange(articleextractor_count)]
		for pd in page_downloaders:
			pd.start()
		for ue in url_extractors:
			ue.start()
		for ae in article_extractors:
			ae.start()

		# cleanup
		while alive():
			time.sleep(1)

		self._save()
		for pd in page_downloaders:
			pd.join()
		for ue in url_extractors:
			ue.join()
		for ae in article_extractors:
			ae.join()

