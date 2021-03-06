#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# EssentialBackendTools test functions for WxFixBoot Version 2.0.2
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

#If you're wondering why this is here, it's so that there are some known good/sane functions to aid testing the ones in DialogTools.

#Do future imports to prepare to support python 3. Use unicode strings rather than ASCII strings, as they fix potential problems.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

#These all trick the EssentialBackendTools to calling a different function to those found in DialogTools without modifying the code.
#Return DlgResult too so it behaves the same way.

def ShowMsgDlg(Message, Kind="info"):
    """Shows a message dialog from a thread upon instruction"""
    if Kind == "info":
        Title = "WxFixBoot - Information"
        style = wx.OK | wx.ICON_INFORMATION

    elif Kind == "warning":
        Title = "WxFixBoot - Warning"
        style = wx.OK | wx.ICON_EXCLAMATION

    elif Kind == "error":
        Title = "WxFixBoot - Error"
        style = wx.OK | wx.ICON_ERROR

    dlg = wx.MessageDialog(ParentWindow.Panel, Message, Title, style, pos=wx.DefaultPosition)
    dlg.ShowModal()
    dlg.Destroy()

def ShowYesNoDlg(Message, Title="WxFixBoot - Question", Buttons=(None, None)):
    """Shows a yes/no dialog from a thread upon instruction"""
    dlg = wx.MessageDialog(ParentWindow.Panel, Message, Title, wx.YES_NO | wx.ICON_QUESTION)

    #Try to set custom Buttons labels if needed (handle attribute error on wx 2.8.11).
    if Buttons != (None, None):
        try:
            if dlg.SetYesNoLabels(Buttons[0], Buttons[1]):
                #If it worked get rid of the last unneccessary sentence in the message.
                dlg.SetMessage(' '.join(Message.split(".")[0:-1]))

        except AttributeError: pass

    #Where possible, destroy just before setting DlgResult to avoid potential race conditions.
    if dlg.ShowModal() == wx.ID_YES:
        dlg.Destroy()
        DlgResult = True

    else:
        dlg.Destroy()
        DlgResult = False

    return DlgResult

def ShowChoiceDlg(Message, Choices, Title="WxFixBoot - Select an Option"):
    """Shows a choice dialog from a thread upon instruction"""
    dlg = wx.SingleChoiceDialog(ParentWindow.Panel, Message, Title, Choices, pos=wx.DefaultPosition)

    #Where possible, destroy just before setting DlgResult to avoid potential race conditions.
    if dlg.ShowModal() == wx.ID_OK:
        DlgResult = dlg.GetStringSelection()
        dlg.Destroy()

    else:
        dlg.Destroy()
        DlgResult = False

    return DlgResult

def ShowTextEntryDlg(Message, Title="WxFixBoot - Text Entry"):
    """Shows a text entry dialog from a thread upon instruction"""
    dlg = wx.TextEntryDialog(ParentWindow.Panel, Message, Title, "", style=wx.OK|wx.CANCEL, pos=wx.DefaultPosition)

    #Where possible, destroy just before setting DlgResult to avoid potential race conditions.
    if dlg.ShowModal() == wx.ID_OK:
        DlgResult = dlg.GetValue()
        dlg.Destroy()

    else:
        dlg.Destroy()
        DlgResult = False

    return DlgResult

def ShowSaveFiledlg(Title="WxFixBoot - Select A File", Wildcard="All Files/Devices (*)|*"):
    """Shows a save file choice dialog from a thread upon instruction"""
    dlg = wx.FileDialog(ParentWindow.Panel, message=Title, defaultDir="/home", wildcard=Wildcard, style=wx.SAVE|wx.OVERWRITE_PROMPT)

    #Where possible, destroy just before setting DlgResult to avoid potential race conditions.
    if dlg.ShowModal() == wx.ID_OK:
        dlg.Destroy()
        DlgResult = dlg.GetPath()

    else:
        dlg.Destroy()
        DlgResult = False

    return DlgResult

#End Main Class.
