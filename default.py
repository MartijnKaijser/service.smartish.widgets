#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is based on service.skin.widgets
#    Thanks to the original authors

import os
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import random
import urllib
import datetime
import socket
from traceback import print_exc
from time import gmtime, strftime

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson
    
__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__localize__     = __addon__.getLocalizedString

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        self._parse_argv()
        
        try:
            clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
            clientsocket.connect( ( "localhost", 45354 ) )
            if self.ID is None:
                log( "### (WIDGET) Sending message %s|%s" %( self.TYPE, sys.argv[ 1 ] ) )
                clientsocket.send( "%s|%s" %( self.TYPE, sys.argv[ 1 ] ) )
            else:
                log( "### (WIDGET) Sending message %s|%s|%s" %( self.TYPE, self.ID, sys.argv[ 1 ] ) )
                clientsocket.send( "%s|%s|%s" %( self.TYPE, self.ID, sys.argv[ 1 ] ) )
            message = clientsocket.recv( 128 )
            log( "### (WIDGET) Recieved message: " + message )
            clientsocket.close()

        except:
            log( "Unable to establish connection to service" )
            xbmcplugin.endOfDirectory(handle= int(sys.argv[1]))
            
    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 2 ].split( "&" ) )
        except:
            params = {}
        self.TYPE = params.get( "?type", "" )
        self.ID = params.get( "id", None )

    
log('script (widget) version %s started' % __addonversion__)
Main()
log('script (widget) %s stopped' % __addonversion__)
