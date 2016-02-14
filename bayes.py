# -*- coding: utf-8 -*-
import codecs
import re
import sys
from optparse import OptionParser

from nltk.classify import NaiveBayesClassifier

space = re.compile('[\'".,!?\\s\\(\\)]+')
cats = ('positiivne', 'negatiivne', 'neutraalne', 'vastuoluline')
classifier = None
corpus_name = 'korpus.csv'


def load_corpus():
	print("Load corpus: ", corpus_name)
	features = []
	with codecs.open(corpus_name, 'r', encoding='utf-8') as f:
		# for line in f: print line
		for line in f:
			row = line.split(',', 1)
			words = space.split(row[1])
			feats = dict([(word, True) for word in words])
			features.append((feats, row[0]))
	return features


def get_classifier():
	global classifier
	if not classifier:
		corpus = load_corpus()
		if corpus:
			print("Train")
			classifier = NaiveBayesClassifier.train(corpus)
			# print >> sys.stderr,  classifier.labels()
			# print >> sys.stderr,  classifier.most_informative_features(n=10)
		else:
			print("No corpus!", file=sys.stderr)


def classify(words):
	get_classifier()
	feats = dict([(word, True) for word in words])
	return classifier.classify(feats)


def prob_classify(words):
	get_classifier()
	feats = dict([(word, True) for word in words])
	return classifier.prob_classify(feats)


def doit():
	get_classifier()
	if classifier:
		for para in sys.stdin:
			words = space.split(para)
			feats = dict([(word, True) for word in words])
			print()
			classifier.classify(feats)


def main():
	global classifier_name
	parser = OptionParser(usage='Usage: %prog file')
	parser.add_option('-f', '--file', dest="filename", help='Corpus file')
	opts, args = parser.parse_args()

	if opts.filename:
		corpus_name = opts.filename

	doit()


if __name__ == '__main__':
	main()
