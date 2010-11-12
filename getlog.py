#!/usr/bin/python

#Copyright (C) 2010  Eder Luis Jorge - edinho.jorge@gmail.com
#
#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 3 of the License, or
#any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

__author__="Eder Luis Jorge"

import ConfigParser
import os
import pexpect
import shutil
import sys
import threading
import wx

#CONSTANTS
CONFIG_FILE = 'getlog.conf'
GETLOG_SECTION = 'GETLOG'

#GLOBAL VARIABLES
global getlog_config_index
global username
global user_password
global list_section

#CLASSES
class CopyAndZip(threading.Thread):
    def __init__ (self, command, dir_to_compress, zip_name):
      threading.Thread.__init__(self)
      self.command = command
      self.dir_to_compress = dir_to_compress
      self.zip_name = zip_name
      self.p = None
      self.copystatus = 0
    def run(self):
        self.copystatus = 0
        self.p=pexpect.spawn(self.command, timeout=None)
        self.p.expect(['password', 'Password', 'user_password', 'user_password'], timeout=None)
        self.p.sendline(user_password)
        self.copystatus = 1
        self.p.expect(pexpect.EOF)
        self.copystatus = 2
        os.system("zip -r %s %s" %(self.zip_name, self.dir_to_compress))
        self.copystatus = 3
        
        #v2.7 or superior
        #shutil.make_arquive(self.zipName, 'zip', self.dir_to_compress)
    def get_copystatus(self):
        return self.copystatus

    def get_copystatus_text(self):
        if self.copystatus == 0:
            return 'Preparing to copy'
        elif self.copystatus == 1:
            return 'Copying remote files'
        elif self.copystatus == 2:
            return 'Compressing files'
        elif self.copystatus == 3:
            return 'Files copied'
        else:
            return 'Please wait'


#FUNCTIONS/METHODS
def load_config():
    global config
    global options
    global getlog_config_index
    global list_section
    options = []
    config = ConfigParser.RawConfigParser()
    config.read(os.path.dirname(sys.argv[0]) + "/" + CONFIG_FILE);
    list_section = config.sections()
    list_section.sort()

    i=-1
    for section in list_section:
        i+=1
        if section==GETLOG_SECTION:
            #JUMPING GETLOG SECTION
            getlog_config_index = i
            continue

        print '[%d]%s' %(i, section)
        options.append(section)

def save_config():
    config = ConfigParser.RawConfigParser()
    config.read(CONFIG_FILE);

    config.add_section('Section3')
    config.set('Section1', 'int', '15')

    with open(CONFIG_FILE, 'wa') as configfile:
        config.write(configfile)

def get_files(section):

    tempDir = config.get(GETLOG_SECTION, 'tempdir')
    destDir = tempDir + section + '/'
    server = config.get(section, 'server')

    try:
        shutil.rmtree(destDir, True)
        os.makedirs(destDir)
    except:
        print 'Error creating directory', destDir

    print 'Getting %s logs from %s server to %s local dir' %(section, server, destDir)
    arquivos = config.get(section, 'files').split(',')
    if config.has_option(section, 'files_optional'):
        if show_yesno_dialog("Do you want to retrieve optional files for %s?" %(section)):
            arquivos.extend(config.get(section, 'files_optional').split(','))

    dialog = wx.ProgressDialog('Get log', 'Getting files', 100, None, wx.PD_ELAPSED_TIME)
    dialog.SetSize((350, 200))
    dialog.SetMinSize((350, 200))

    files = " ".join(arquivos)
    readable_files = [truncate_long_names(s) for s in arquivos]
    

    command = 'scp -r -o StrictHostKeyChecking=no %s@%s:\"%s\" %s.' %(username, server, files, destDir)
    c = CopyAndZip(command, destDir, tempDir + section + '.zip')
    c.start()
    while c.isAlive():
        wx.MilliSleep(50)
        dialog.Pulse("Copying files \n%s\n%s\nPlease wait." %("\n".join(readable_files), c.get_copystatus_text()))

    dialog.Destroy()

def truncate_long_names(s, max_size=35, delimiter='/'):
    if len(s) > max_size:
        tokens = s.split(delimiter)
        s = s[0:max_size - len(tokens[len(tokens) - 1]) - 4] + '...' + delimiter + tokens[len(tokens) - 1]
    return s


def load_user():
    global username
    username = config.get(GETLOG_SECTION, "default_user")

    askForUser = bool(config.get(GETLOG_SECTION, "ask_for_user"))

    if (askForUser):
        dialog = wx.TextEntryDialog( None, 'Enter server username', 'Get log', username )
        if dialog.ShowModal() == wx.ID_CANCEL:
            dialog.Destroy()
            quit()
        username = dialog.GetValue()

    if (not(username)):
        username = 'root'

def show_choices():
    dialog = wx.MultiChoiceDialog( None, 'Choose the items to collect logs', 'Get log', options )

    if dialog.ShowModal() == wx.ID_CANCEL:
        dialog.Destroy()
        quit()

    returnValue = dialog.GetSelections()
    dialog.Destroy()
    return returnValue

def ask_for_password():
    global user_password
    user_password = ''#R94g8ee3H'
    dialog = wx.PasswordEntryDialog(None, 'Input the server password', 'Server password', user_password)

    if dialog.ShowModal() == wx.ID_CANCEL:
        dialog.Destroy()
        quit()

    user_password = dialog.GetValue()
    dialog.Destroy()

def show_yesno_dialog(text):
    dialog = wx.MessageDialog(None, text, 'Get log',wx.YES_NO|wx.ICON_QUESTION)

    returnValue = False
    if dialog.ShowModal() == wx.ID_YES:
        returnValue = True

    dialog.Destroy()

    return returnValue


#MAIN FUNCTION#
def main():
    print "Running getlog tool"

    load_config()
    app = wx.PySimpleApp()
    indexes = show_choices()
    load_user()
    ask_for_password()

    for i in indexes:
        #for console mode. It needs a rethink
        #if int(i) == getlog_config_index:
        #    print 'GETLOG section selected. Jumping get_files prcedure for it.'
        #    continue
        if int(i) < getlog_config_index:
            print list_section[int(i)]
            get_files(list_section[int(i)])
        else:
            print list_section[int(i)+1]
            get_files(list_section[int(i)+1])

    
if __name__ == "__main__": main()