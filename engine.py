import os
from crawler import ReadFromFile

IGNORED = set(['', 'a', 'an', 'the', 'I', 'you', 'he',
	'she', 'her', 'his', 'him', 'myself', 'our', 'they',
	'their', 'them', 'myself', 'ourselves', 'herself',
	'himself', 'theyselves'])

class SearchResult(object):
    fileName = ""
    url = ""
    def __init__(self, fileName, url):
        self.fileName = fileName
        self.url = url

class SearchEngine:
	def __init__(self):
		self.inverted_index = {}
	def build_index(self, path):
		print 'Building index ({})...'.format(path),
		articles = [path+'/'+fn for fn in next(os.walk(path))[2] if fn[-4:] == '.txt']
                print articles
		for a in articles:
			content = ReadFromFile(a).split('\n')
			title, url = content[0], content[1]
			content = ' '.join(content[2:]).replace('\n', ' ')
			words = [w.lower() for w in content.split(' ') if w.lower() not in IGNORED]
			for w in words:
				self.inverted_index[w] = self.inverted_index.get(w, { (title, url):0 })
				self.inverted_index[w][title, url] = self.inverted_index[w].get((title, url), 0) + 1
		print 'Done'

	def search(self, words):
            words = [w.lower() for w in words]
            for w in words:
                    if not self.inverted_index.has_key(w):
                            print 'No result found.'
                            print
                            return

            freq = {}
            w = words[0]
            plist = self.inverted_index[w]
            for title, url in plist:
                    freq[title, url] = plist[title, url]
            for w in words[1:]:
                    plist = self.inverted_index[w]
                    for tu in freq.keys():
                            if not plist.has_key(tu):
                                    del freq[tu]
                    for tu in plist:
                            if freq.has_key(tu):
                                    freq[tu] += plist[tu]
            kv = [(freq[title, url], title, url) for title, url in freq]
            print '{} results found.'.format(len(kv)),
            if len(kv) > 5:
                    print 'only 5 displayed.'
            else:
                    print
            print
            i = 0
            result = []
            for f, t, u in reversed(sorted(kv)[-5:]):
                i += 1
                print 'result [{}]: key words appear {} times.'.format(i, f)
                obj = SearchResult(t,u)
                result.append(obj)
            return result
