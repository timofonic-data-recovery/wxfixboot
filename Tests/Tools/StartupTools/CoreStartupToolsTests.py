#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# CoreStartupTools tests for WxFixBoot Version 2.0.1
# This file is part of WxFixBoot.
# Copyright (C) 2013-2017 Hamish McIntyre-Bhatty
# WxFixBoot is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 or,
# at your option, any later version.
#
# WxFixBoot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WxFixBoot.  If not, see <http://www.gnu.org/licenses/>.

#Do future imports to prepare to support python 3. Use unicode strings rather than ASCII strings, as they fix potential problems.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

#Import modules
import unittest
import wx

#Import test functions & data.
from . import CoreStartupToolsTestFunctions as Functions
from . import CoreStartupToolsTestData as Data

class TestPanel(wx.Panel):
    def __init__(self, parent):
        """Initialises the panel"""
        wx.Panel.__init__(self, parent=parent)
        self.frame = parent

class TestWindow(wx.Frame):
    def __init__(self):
        """Initialises TestWindow"""
        wx.Frame.__init__(self, parent=None, title="WxFixBoot Tests", size=(1,1), style=wx.SIMPLE_BORDER)

class TestDeterminePackageManager(unittest.TestCase):
    def setUp(self):
        Tools.coretools.Startup = True
        Functions.CoreTools = CoreTools()

    def tearDown(self):
        del Tools.coretools.Startup
        del Functions.CoreTools

    def testDeterminePackageManager1(self):
        self.assertEqual(CoreStartupTools().DeterminePackageManager(APTCmd="which apt-get", YUMCmd="which yum"), Functions.DeterminePackageManager(APTCmd="which apt-get", YUMCmd="which yum"))

class TestGetFSTabInfo(unittest.TestCase): #*** Do another test with a fake fstab file(s) XD ***
    def setUp(self):
        Tools.StartupTools.core.DiskInfo = Data.ReturnEmptyDiskInfoDict()
        Functions.DiskInfo = Data.ReturnEmptyDiskInfoDict()

    def tearDown(self):
        del Tools.StartupTools.core.DiskInfo
        del Functions.DiskInfo

    def testGetFSTabInfo1(self):
        self.assertEqual(CoreStartupTools().GetFSTabInfo(MountPoint="", OSName="ThisIsATest"), Functions.GetFSTabInfo(MountPoint="", OSName="ThisIsATest"))

class TestDetermineOSArchitecture(unittest.TestCase):
    def setUp(self):
        Tools.coretools.Startup = True
        Functions.CoreTools = CoreTools()

    def tearDown(self):
        del Tools.coretools.Startup
        del Functions.CoreTools

    def testDetermineOSArchitecture1(self):
        self.assertEqual(CoreStartupTools().DetermineOSArchitecture(MountPoint=""), Functions.DetermineOSArchitecture(MountPoint=""))
