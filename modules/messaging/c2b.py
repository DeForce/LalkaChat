# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import re, random

class c2b():
	def __init__(self, confFolder):
		# Creating filter and replace strings.
		self.filter=[u'жопа']
		self.replace=[u'погода']

	def getMessage(self, message):
		# Replacing the message if needed.
		# Please do the needful
		for replace in self.filter:
			message['text'] = message['text'].replace(replace,random.choice(self.replace))
		return message