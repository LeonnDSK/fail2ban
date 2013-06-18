# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 
# $Revision$

__author__ = "Cyril Jaquier"
__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import time, logging

from datetemplate import DatePatternRegex, DateTai64n, DateEpoch, DateISO8601
from threading import Lock

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class DateDetector:
	
	def __init__(self):
		self.__lock = Lock()
		self.__templates = list()
		self.__known_names = set()

	def _appendTemplate(self, template):
		name = template.getName()
		if name in self.__known_names:
			raise ValueError("There is already a template with name %s" % name)
		self.__known_names.add(name)
		self.__templates.append(template)
	
	def appendTemplate(self, template, **kwargs):
		if isinstance(template, str):
			template = DatePatternRegex(template, **kwargs)
		else:
			assert not kwargs
		DateDetector._appendTemplate(self, template)

	def addDefaultTemplate(self):
		self.__lock.acquire()
		try:
			# asctime
			self.appendTemplate("%a %b %d %H:%M:%S %Y")
			# asctime without year
			self.appendTemplate("%a %b %d %H:%M:%S")
			# standard
			self.appendTemplate("%b %d %H:%M:%S")
			# simple date
			self.appendTemplate("%Y/%m/%d %H:%M:%S")
			# simple date too (from x11vnc)
			self.appendTemplate("%d/%m/%Y %H:%M:%S")
			# previous one but with year given by 2 digits
			# (See http://bugs.debian.org/537610)
			self.appendTemplate("%d/%m/%y %H:%M:%S")
			# Apache format [31/Oct/2006:09:22:55 -0000]
			self.appendTemplate("%d/%b/%Y:%H:%M:%S")
			# CPanel 05/20/2008:01:57:39
			self.appendTemplate("%m/%d/%Y:%H:%M:%S")
			# custom for syslog-ng 2006.12.21 06:43:20
			self.appendTemplate("%Y.%m.%d %H:%M:%S")
			# named 26-Jul-2007 15:20:52.252 
			self.appendTemplate("%d-%b-%Y %H:%M:%S")
			# 17-07-2008 17:23:25
			self.appendTemplate("%d-%m-%Y %H:%M:%S")
			# 01-27-2012 16:22:44.252
			self.appendTemplate("%m-%d-%Y %H:%M:%S")
			# TAI64N
			template = DateTai64n()
			template.setName("TAI64N")
			self.appendTemplate(template)
			# Epoch
			template = DateEpoch()
			template.setName("Epoch")
			self.appendTemplate(template)
			# ISO 8601
			template = DateISO8601()
			template.setName("ISO 8601")
			self.appendTemplate(template)
			# Only time information in the log
			self.appendTemplate("%H:%M:%S", anchor=True)
			# <09/16/08@05:03:30>
			self.appendTemplate("<%m/%d/%y@%H:%M:%S>", anchor=True)
			# MySQL: 130322 11:46:11
			self.appendTemplate("%y%m%d %H:%M:%S", anchor=True)
			# Apache Tomcat
			self.appendTemplate("%b %d, %Y %I:%M:%S %p")
		finally:
			self.__lock.release()
	
	def getTemplates(self):
		return self.__templates
	
	def matchTime(self, line):
		self.__lock.acquire()
		try:
			for template in self.__templates:
				match = template.matchDate(line)
				if not match is None:
					logSys.debug("Matched time template %s" % template.getName())
					return match
			return None
		finally:
			self.__lock.release()

	def getTime(self, line):
		self.__lock.acquire()
		try:
			for template in self.__templates:
				try:
					date = template.getDate(line)
					if date is None:
						continue
					logSys.debug("Got time using template %s" % template.getName())
					return date
				except ValueError:
					pass
			return None
		finally:
			self.__lock.release()

	def getUnixTime(self, line):
		date = self.getTime(line)
		if date == None:
			return None
		else:
			return time.mktime(tuple(date))

	##
	# Sort the template lists using the hits score. This method is not called
	# in this object and thus should be called from time to time.
	
	def sortTemplate(self):
		self.__lock.acquire()
		try:
			logSys.debug("Sorting the template list")
			self.__templates.sort(key=lambda x: x.getHits(), reverse=True)
			t = self.__templates[0]
			logSys.debug("Winning template: %s with %d hits" % (t.getName(), t.getHits()))
		finally:
			self.__lock.release()
