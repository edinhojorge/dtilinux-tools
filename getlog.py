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
    """Copy some remote files and Zip the folder.

    CopyAndZip is a class that receive a copy command
    through its constructor, and after the caller call the
    start method (see threading.Thread), it runs the command
    using pexpect and informs the password in a noninteractive
    mode. Then it zips the directory. The get_copystatus_text
    method returns a status text of the progress."""
    def __init__ (self, command, dir_to_compress, zip_name):
        """Initializes the classe and set the attributes.
        
        Keyword arguments: 
        command: SCP command. Feel free to get it off here. It
                 was used like this because I've already had the
                 command, and to show the progress bar, I needed
                 a thread. So, here we are.
        dir_to_compress: Full path of which dir will be zipped
        zip_name: Full path of the zip file that will be created

        """
        threading.Thread.__init__(self)
        self.command = command
        self.dir_to_compress = dir_to_compress
        self.zip_name = zip_name
        self.p = None
        self.copystatus = 0
    def run(self):
        """Process that will run in background.

        Execute the command, send the password and zip the dir where the
        remote files are supposed to be. While it's doing the process, it
        changes the copystatus attribute.

        """
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
        """Return the status code, 0 to 3.

        0 - 'Preparing to copy'
        1 - 'Copying remote files'
        2 - 'Compressing files'
        3 - 'Files copied'
        else - 'Please wait'

        """
        return self.copystatus

    def get_copystatus_text(self):
        """Return the status message accordly to copystatus code.

        0 - 'Preparing to copy'
        1 - 'Copying remote files'
        2 - 'Compressing files'
        3 - 'Files copied'
        else - 'Please wait'

        """
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
    """Load the program configurations from a text file using ConfigParser."""
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

def save_config(section='dummy_section', values=[['server','rhostname'],['files','/tmp/file1,/tmp/file2'],['optional_files','/tmp/optional_file1,/tmp/optional_file2']]):
    """TODO method. Save new ou update servers configuration."""
    config = ConfigParser.RawConfigParser()
    config.read(CONFIG_FILE);

    config.add_section(section)

    for x,y in values:
        config.set(section, x, y)

    with open(CONFIG_FILE, 'wa') as configfile:
        config.write(configfile)

    load_config()

def get_files(section):
    """Get files remotely, ask for optional files and shows a progress bar.

    For the section passed as a parameter, it get the config to build the
    command, and if there is an optional_files tag, it asks if the user
    wants to get the optional files. After the command is build, it creates
    a progress bar dialog, pass the command to CopyAndZip class and shows
    the status of the copy.

    keyword arguments:
    section: It is the section name found in CONFIG_FILE.

    """
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
    """A litle helper to minimize a string, returning /SuperLongS.../Readable

    It shorts the string accordly to max_size and delimiter. When the string
    is longer than max_size, it tries to reduce to a read the last token
    identified by delimiter.

    Keyword arguments:
    s: String to reduce (or not)
    max_size: Which size should 's' be reduced to. (default=35)
    delimiter: Which delimiter is being used (default=/)

    """
    if len(s) > max_size:
        tokens = s.split(delimiter)
        s = s[0:max_size - len(tokens[len(tokens) - 1]) - 4] + '...' + delimiter + tokens[len(tokens) - 1]
    return s


def load_user():
    """Load user name to connect to remote hosts.

    Load user name to connect to remote hosts. It uses 'default_user' tag
    from GETLOG section, and if the 'ask_for_user' tag is 'True', then
    prompt for the user. When it's off, it loads and uses 'default_user'
    directly.

    """
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
    """Show all the sections in a graphical window for user to choose.

    Show all the sections from the CONFIG_FILE in a graphical window
    for user to choose. It does not display the GETLOG section, and more
    than one configuration can be selected.

    """
    dialog = wx.MultiChoiceDialog( None, 'Choose the items to collect logs', 'Get log', options )

    if dialog.ShowModal() == wx.ID_CANCEL:
        dialog.Destroy()
        quit()

    returnValue = dialog.GetSelections()
    dialog.Destroy()
    return returnValue

def ask_for_password():
    """Asks for password to connect to remote hosts.

    As it is not recommended to store passwords, it asks for password to connect
    to remote hosts. The same password is used for all selected servers.

    """
    global user_password
    user_password = ''
    dialog = wx.PasswordEntryDialog(None, 'Input the server password', 'Server password', user_password)

    if dialog.ShowModal() == wx.ID_CANCEL:
        dialog.Destroy()
        quit()

    user_password = dialog.GetValue()
    dialog.Destroy()

def show_yesno_dialog(text):
    """Another helper that shows a Yes/No dialog with the text argument"""
    dialog = wx.MessageDialog(None, text, 'Get log',wx.YES_NO|wx.ICON_QUESTION)

    returnValue = False
    if dialog.ShowModal() == wx.ID_YES:
        returnValue = True

    dialog.Destroy()

    return returnValue


#MAIN FUNCTION#
def main():
    """Main function to follow the standards. It manages the whole thing.

    It loads the config, start an application gui background needs, show the
    choices for the user, get the password, get the files and zip them. All
    or almost all using other methods here.

    """
    print "Running getlog tool"

    load_config()
    app=wx.PySimpleApp()
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