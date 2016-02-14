# -*- coding: utf-8 -*-
import codecs
import re
import sys
from optparse import OptionParser

import bayes

# translation
try:
	from ekorpus.lib.base import *
except ImportError:
	def _(s):
		return s

silent = None
hybrid = 1

htmlStart = """
<html><head>
<style>
</style>
</head>
<body>
"""

htmlEnd = """
</body>
</html>
"""
paraOpen = '<div class="'
paraClose = '</div>'
words = ''


def load():
	global words
	if words:
		return words
	words = {}
	with codecs.open('sqnad.csv', 'r', encoding='utf-8') as f:
		for row in f:
			parts = row.split(',', 3)
			if len(parts) < 2:
				continue
			words[parts[0]] = parts[1]

	words['ei'] = ''
	words['ega'] = ''

	return words


def mark(text, word_list):
	space = re.compile('([\'".,!?\\s\\(\\)]+)')
	stop = re.compile("[,.!?]")
	para = re.compile("\\n")

	text_words = space.split(text)
	positive = negative = extreme = count = 0
	total = [0, 0, 0, 0]
	para_start = 0
	r = []
	stats = []
	bayes_stats = []
	word_style = {'1': 'word positiveW', '-1': 'word negativeW', '-8': 'word extremeW'}
	stat_style = {'positiivne': 'positiveB', 'negatiivne': 'negativeB', 'neutraalne': 'neutralB'}
	stat_words = []

	def do_bayes():
		feats = dict([(item, True) for item in stat_words if not space.match(item)])
		cs = bayes.prob_classify(feats)
		bayes_stats.append(cs)
		return stat_style[cs.max()]

	def close_para():

		if len(r) != para_start:

			s = '<a name="%d"></a>%s' % (len(stats), paraOpen)
			if extreme > 0:
				s += 'para extremeP'
			elif positive > negative:
				s += 'para positiveP'
			elif negative > positive:
				s += 'para negativeP'
			elif positive > 0:
				s += 'para mixedP'
			else:
				s += 'para neutralP'

			if hybrid:
				stat_class = do_bayes()
				s = s + " " + stat_class
				del stat_words[:]

			s += '">'

			r.insert(para_start, s)
			r.append(word)
			r.append(paraClose)
			total[0] += count
			total[1] += positive
			total[2] += negative
			total[3] += extreme
			stats.append((count, positive, negative, extreme))
		return len(r)

	try:
		i = iter(text_words)
		while 1:
			word = next(i)
			if not word:
				continue
			if para.search(word):
				para_start = close_para()
				positive = negative = extreme = count = 0
				continue

			if not space.search(word):
				count += 1
				if hybrid:
					stat_words.append(word)

			w = word.lower()
			if w in word_list:
				flag = word_list[w]

				if not flag:  # negator
					separator = next(i, '.')
					word += separator
					if stop.search(separator):  # neg eos
						r.append(word)
						continue

					word2 = next(i, '')
					if not word2:  # neg eof
						r.append(word)
						continue

					word += word2
					w = word2.lower()
					if w in word_list:
						flag = word_list[w]
						if flag == "1":
							flag = "-1"
						elif flag == "-1":
							flag = "1"
						elif flag == "-8":
							flag = "-8"
						else:
							flag = ''  # neg neg
					else:
						flag = "-1"

				if flag == "1":
					positive += 1
				elif flag == "-1":
					negative += 1
				elif flag == "-8":
					extreme += 1

				if flag:
					r.append('<span class="%s">' % (word_style[flag]))
				r.append(word)
				if flag:
					r.append("</span>")
			else:
				r.append(word)
			word = ''
	except StopIteration:
		pass
	close_para()
	rtn = '<div class="text">' + ''.join(r) + '</div>'

	# rtn:   html
	# total: word counts (count, positive, negative, extreme) for whole text
	# stats: list of word counts for each paragraph
	# bayesStats: prob distribution for each paragraph
	return rtn, total, stats, bayes_stats


def text_valence(total, para):
	# Calculate whole text emotion from paragraphs words counts.
	# here para = [neutral, positive, negative, mixed] total number of words in each type of paragraph.
	# and "all" is the total number of words in the text.

	count = 0  # number of different emotions
	max_val = pos = 0  # max and its position

	for i, val in enumerate(para):
		if val > 0:
			count += 1
		if val > max_val:
			max_val = val
			pos = i

	valence = _('mostly mixed')
	if count == 1:
		valence = [_('only neutral'), _('only positive'), _('only negative'), _('only mixed')][pos]
	elif count == 2:
		if (float(total) / max_val) < 1.5:
			valence = [_('mostly neutral'), _('mostly positive'), _('mostly negative'), _('mostly mixed')][pos]
	else:
		if (total / max_val) <= 1:
			valence = [_('mostly neutral'), _('mostly positive'), _('mostly negative'), _('mostly mixed')][pos]
	return valence


classifier2style = {'positiivne': 'tile positiveT', 'negatiivne': 'tile negativeT', 'neutraalne': 'tile neutralT'}


def chart_stats(total, stats, bayes_stats):
	# Create the bar for the statistical estimate

	if total[0] == 0:
		return ''

	r = ['<div class="chart">']
	i = 0
	for s in stats:
		prob = bayes_stats[i]
		classifier = prob.max()
		valence = classifier2style[classifier]

		label1 = _('positive =')
		label2 = _('negative =')
		label3 = _('neutral =')

		r.append(
			'''
			<a href="#%d">
				<div class="bar %s" style="width:%.2f%%">&nbsp;
				<span class="info">%s %d<br/>%s:<br/>&nbsp;%s %.2f<br/>&nbsp;%s %.2f<br/>&nbsp;%s %.2f</span>
				</div>
			</a>
			'''
			% (
				i, valence, (10000 * s[0] / total[0]) / 100.0, _('words:'), s[0], _("Probability"),
				label1, prob.prob('positiivne'), label2, prob.prob('negatiivne'), label3, prob.prob('neutraalne')
			)
		)
		i += 1

	r.append('</div>')
	# html bar of paragraph properties
	return "".join(r)


def chart(total, stats):
	# Create the bar for lexicon based estimation

	if total[0] == 0:
		return ''

	r = ['<div class="chart">']
	para = [0, 0, 0, 0]  # neutral, positive, negative, mixed
	i = 0
	for s in stats:
		positive = s[1]
		negative = s[2]
		extreme = s[3]
		valence = 'tile neutralT'
		if extreme > 0:
			para[2] = para[2] + s[0]  # count all words in this paragraph as negative
			valence = 'tile extremeT'
		elif positive > negative:
			para[1] = para[1] + s[0]
			valence = 'tile positiveT'
		elif negative > positive:
			para[2] = para[2] + s[0]
			valence = 'tile negativeT'
		elif positive > 0:
			para[3] = para[3] + s[0]
			valence = 'tile mixedT'
		else:
			para[0] = para[0] + s[0]

		label1 = _('positive:')
		label2 = _('negative:')
		label3 = _('extreme:')

		r.append(
			'''
			<a href="#%d">
				<div class="bar %s" style="width:%.2f%%">&nbsp;
				<span class="info">%s %d<br/>%s %d<br/>%s %d<br/>%s %d</span>
				</div>
			</a>
			'''
			% (
				i, valence, (10000 * s[0] / total[0]) / 100.0, _('words:'), s[0], label1, positive, label2, negative,
				label3, extreme
			)
		)
		i += 1

	r.append('</div>')
	valence = text_valence(total[0], para)

	# valence: text valence name
	# html: html bar of paragraph properties
	return valence, format_valence(valence) + ("".join(r))


# <div class="bar" style="width:10%;height:90%;top:10%;background-color:blue">&nbsp;</div>


def format_valence(valence):
	return '<div class="textvalence">%s: %s</div>' % (_('Valence'), valence)


def mark_text(text, data_only, lexicon_based):
	# For web

	global words
	load()
	t = mark(text, words)
	s = chart(t[1], t[2])
	if data_only:
		if data_only == "2":
			return s[0]
		if data_only == "3":
			return emotion_bayes(t[3], t[1], t[2])
		return s[1] + t[0]
	if not lexicon_based:
		return t[0] + format_valence(emotion_bayes(t[3], t[1], t[2])) + chart_stats(t[1], t[2], t[3])
	return t[0] + s[1]


#    for c in cs.samples():
#      print c, cs.prob(c)

def emotion_bayes(emotions, total, stats):
	if total[0] == 0:
		return ''

	para = [0, 0, 0, 0]  # neutral, positive, negative, mixed
	for i, es in enumerate(emotions):
		e = es.max()
		n = stats[i][0]
		if e == "positiivne":
			para[1] = para[1] + n
		elif e == "negatiivne":
			para[2] = para[2] + n
		elif e == "neutraalne":
			para[0] = para[0] + n

	return text_valence(total[0], para)


def doit(filename):
	# Standalone

	global words
	load()
	fi = codecs.open(filename, 'r', encoding='utf-8')
	text = fi.read()
	fi.close()
	t = mark(text, words)
	s = chart(t[1], t[2])

	if not silent:
		fo = codecs.open(filename + '.html', 'w', encoding='utf-8')
		fo.write(htmlStart)
		fo.write(t[0])
		# fo.write(t[0].replace('\r','<br>'))
		fo.write(chart_stats(t[1], t[2], t[3]))
		fo.write(htmlEnd)
		fo.close()
	else:
		print("Dict:", s[0])
		print("Dict:", s[1])
		print("Bayes:", emotion_bayes(t[3], t[1], t[2]), t[3])


def main():
	global silent

	parser = OptionParser(usage='Usage: %prog file')
	parser.add_option('-s', '--silent', action="store_true", dest="silent", help='Silent: no html file')
	opts, args = parser.parse_args()
	if len(args) != 1:  # or not opts.segment:
		parser.print_help()
		sys.exit(1)
	if opts.silent:
		silent = opts.silent

	doit(args[0])


if __name__ == '__main__':
	main()
