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
import thread
import socket
from datetime import datetime
from traceback import print_exc
from time import gmtime, strftime

import cPickle as pickle

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__localize__     = __addon__.getLocalizedString
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")

__resource__     = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")


sys.path.append(__resource__)
import library, sql, tmdb

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        self.WINDOW = xbmcgui.Window(10000)
        
        #json_query = simplejson.loads( xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "JSONRPC.Introspect", "id": 1}') )
        #print(simplejson.dumps(json_query, sort_keys=True, indent=4 * ' '))
        
        self._init_vars()
        
        self.QUIT = False
        
        # Before we load any threads, we need to use strftime, to ensure it is imported (potential threading issue)
        strftime( "%Y%m%d%H%M%S",gmtime() )
        
        thread.start_new_thread( self._player_daemon, () )
        thread.start_new_thread( self._socket_daemon, () )
        self._daemon()            
            
    def _init_vars(self):
        self.WINDOW = xbmcgui.Window(10000)
        #self.Player = Widgets_Player(action = self.mediaStarted, ended = self.mediaEnded)
        #self.Monitor = Widgets_Monitor(update_listitems = self._update)
        self.playingLiveTV = False
        
        self.movieWidget = None
        self.episodeWidget = None
        self.albumWidget = None
        self.pvrWidget = None
        
        self.movieLastUpdated = 0
        self.episodeLastUpdated = 0
        self.albumLastUpdated = 0
        self.pvrLastUpdated = 0
        
        # Create a socket
        self.serversocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        
    def _player_daemon( self ):
        # This is the daemon which will add information about played media to the database
        
        # Create a connection to the database
        self.connectionWrite = sql.connect()
        
        # Create a player monitor
        self.Player = Widgets_Player(action = self.mediaStarted, ended = self.mediaEnded)
        
        # Loop
        while not xbmc.abortRequested and running == True:
            xbmc.sleep( 1000 )
                    
    def _socket_daemon( self ):
        # This is the daemon which will send back any requested widget
        log( "Widget listener started" )
        
        # Bind the server
        self.serversocket.bind( ( "localhost", 45354 ) )
        self.serversocket.listen( 5 )
        
        # Loop
        while not xbmc.abortRequested and running == True:
            try:
                connection, address = self.serversocket.accept()
            except socket.timeout:
                continue
            except:
                print_exc()
                continue
            #buf = connection.recv( 64 )
            thread.start_new_thread( self._socket_thread, (connection, address ) )
        log( "Widget listener stopped" )
        
    def _socket_thread( self, connection, address ):
        buf = connection.recv( 128 )
        if len( buf ) > 0:
            log( "### (SERVICE) recieved message: " + repr( buf ) )
            if buf == "QUIT":
                connection.send( "QUITTING" )
            else:
                data = buf.split( "|" )
                # Display Widget
                if data[ 0 ] == "movies" and self.movieWidget is not None:
                    xbmcplugin.setContent( int( data[ 1 ] ), "movies" )
                    xbmcplugin.addDirectoryItems( int( data[1] ),self.movieWidget[:int( __addon__.getSetting( "returnLimit" ) )] )
                    xbmcplugin.endOfDirectory( handle=int( data[1] ) )
                if data[ 0 ] == "episodes" and self.episodeWidget is not None:
                    xbmcplugin.setContent( int( data[ 1 ] ), "episodes" )
                    xbmcplugin.addDirectoryItems( int( data[1] ),self.episodeWidget[:int( __addon__.getSetting( "returnLimit" ) )] )
                    xbmcplugin.endOfDirectory( handle=int( data[1] ) )
                if data[ 0 ] == "albums" and self.albumWidget is not None:
                    xbmcplugin.setContent( int( data[ 1 ] ), "albums" )
                    xbmcplugin.addDirectoryItems( int( data[1] ),self.albumWidget[:int( __addon__.getSetting( "returnLimit" ) )] )
                    xbmcplugin.endOfDirectory( handle=int( data[1] ) )
                if data[ 0 ] == "pvr" and self.pvrWidget is not None:
                    xbmcplugin.addDirectoryItems( int( data[1] ),self.pvrWidget[:int( __addon__.getSetting( "returnLimit" ) )] )
                    xbmcplugin.endOfDirectory( handle=int( data[1] ) )
                    
                # Play media
                if data[ 0 ] == "playpvr":
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"channelid": ' + data[ 1 ] + '} } }' )
                    xbmcplugin.setResolvedUrl( handle=int( data[ 2 ] ), succeeded=False, listitem=xbmcgui.ListItem() )
                if data[ 0 ] == "playrec":
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"recordingid": ' + data[ 1 ] + '} } }' )
                    xbmcplugin.setResolvedUrl( handle=int( data[ 2 ] ), succeeded=False, listitem=xbmcgui.ListItem() )
                if data[ 0 ] == "playalb":
                    log( "Sending JSON request to play album" )
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": { "albumid": ' + data[ 1 ] + ' } } }' )
                    log( "Setting that we handled the play album request" )
                    xbmcplugin.setResolvedUrl( handle=int( data[ 2 ] ), succeeded=False, listitem=xbmcgui.ListItem() )
                    log( "Done" )
                    
                log( "### (SERVICE) sending message: OK" )
                connection.send( "OK" )
        else:
            log( "### (SERVICE) sending message: NODATA" )
            connection.send( "NODATA" )
    
                    
    def _daemon( self ):
        # This is a daemon which will update the widget with latest suggestions
        self.connectionRead = sql.connect( True )
        count = 0
        while not xbmc.abortRequested:
            count += 1
            if count >= 60 or self.movieWidget is None or self.episodeWidget is None or self.albumWidget is None or self.pvrWidget is None:
                nextWidget = self._getNextWidget()
                if nextWidget is not None:
                    log( "### Starting to get widget " + nextWidget )
                    # If live tv is playing, call the mediaStarted function in case channel has changed
                    if self.playingLiveTV:
                        self.mediaStarted( self.connectionRead )
                        
                    # Get the users habits out of the database
                    habits, freshness = sql.getFromDatabase( self.connectionRead, nextWidget )
                    
                    # Pause briefly, and again check that abortRequested hasn't been called
                    xbmc.sleep( 100 )
                    if xbmc.abortRequested:
                        return
                        
                    # Get all the media items that match the users habits
                    weighted, items = library.getMedia( nextWidget, habits, freshness )
                    
                    # Pause briefly, and again check that abortRequested hasn't been called
                    xbmc.sleep( 100 )
                    if xbmc.abortRequested:
                        return
                        
                    # Generate the widgets
                    if weighted is not None:
                        listitems = library.buildWidget( nextWidget, weighted, items )
                    else:
                        listitems = []
                    
                    # Save the widget
                    if nextWidget == "movie":
                        log( "### Saving movie widget" )
                        self.movieWidget = listitems
                        self.movieLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                        self.WINDOW.setProperty( "smartish.movies", self.movieLastUpdated )
                    elif nextWidget == "episode":
                        log( "### Saving episode widget" )
                        self.episodeWidget = listitems
                        self.episodeLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                        self.WINDOW.setProperty( "smartish.episodes", self.episodeLastUpdated )
                    elif nextWidget == "pvr":
                        log( "### Saving PVR widget" )
                        self.pvrWidget = listitems
                        self.pvrLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                        self.WINDOW.setProperty( "smartish.pvr", self.pvrLastUpdated )                        
                    elif nextWidget == "album":
                        log( "### Saving album widget" )
                        self.albumWidget = listitems
                        self.albumLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                        self.WINDOW.setProperty( "smartish.albums", self.albumLastUpdated )
                
                # Reset counter and update widget type
                count = 0
                
                # If no media playing, clear last played
                if not xbmc.Player().isPlaying():
                    library.lastplayedType = None
                    library.lastplayedID = None
                    
            xbmc.sleep( 1000 )
            
        # Send a message to the socket (this will cause it to close)
            
    def _getNextWidget( self ):
        # This function finds the widget which was the last to be udpated
        update = { self.pvrLastUpdated: "pvr", self.albumLastUpdated: "album", self.episodeLastUpdated: "episode", self.movieLastUpdated: "movie" }
        
        for key in sorted( update.keys() ):
            return update[ key ]
        
    def mediaEnded( self ):
        # Media has finished playing, clear our saved values of what was playing
        self.playingLiveTV = False
        
    def mediaStarted( self, connection = None ):
        log( "Local playback started function" )
        # Get the active player
        json_query = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}' )
        log( "Got active player" )
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        
        json_query = simplejson.loads(json_query)
        
        if json_query.has_key('result'):
            playerid = json_query[ "result" ][ 0 ][ "playerid" ]
            
            # Get details of the playing media
            log( "Getting details of playing media" )
            json_query = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str( playerid ) + ', "properties": [ "title", "artist", "albumartist", "genre", "year", "rating", "album", "track", "duration", "comment", "lyrics", "playcount", "fanart", "director", "trailer", "tagline", "plot", "plotoutline", "originaltitle", "lastplayed", "writer", "studio", "mpaa", "cast", "country", "imdbnumber", "premiered", "productioncode", "runtime", "set", "showlink", "streamdetails", "top250", "votes", "firstaired", "season", "episode", "showtitle", "file", "resume", "artistid", "albumid", "tvshowid", "setid", "watchedepisodes", "disc", "tag", "art", "genreid", "displayartist", "albumartistid", "description", "theme", "mood", "style", "albumlabel", "sorttitle", "episodeguide", "uniqueid", "dateadded", "channel", "channeltype", "hidden", "locked", "channelnumber", "starttime", "endtime" ] } }' )
            log( "Got details of playing media" )
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            
            json_query = simplejson.loads(json_query)
            if json_query.has_key( 'result' ):
                log( repr( json_query[ "result" ] ) )
                type = json_query[ "result" ][ "item" ][ "type" ]
                if type == "episode":
                    self.episode( json_query[ "result" ][ "item" ] )
                elif type == "movie":
                    self.movie( json_query[ "result" ][ "item" ] )
                elif type == "song":
                    log( "Playing media is a song" )
                    self.song( json_query[ "result" ][ "item" ] )
                elif type == "channel":
                    # Get details of the current show
                    live_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0",  "id": 1, "method": "PVR.GetChannelDetails", "params": {"channelid": %d, "properties": [ "broadcastnow" ]}}' %( json_query[ "result" ][ "item" ][ "id" ] ) )
                    live_query = unicode(live_query, 'utf-8', errors='ignore')
                    live_query = simplejson.loads(live_query)
                    
                    # Check the details we need are actually included:
                    if live_query.has_key( "result" ) and live_query[ "result" ].has_key( "channeldetails" ) and live_query[ "result" ][ "channeldetails" ].has_key( "broadcastnow" ):
                        if self.playingLiveTV:
                            # Only update if the current show has changed
                            if not self.lastLiveTVChannel == str( json_query[ "result" ][ "item" ][ "id" ] ) + "|" + live_query[ "result" ][ "channeldetails" ][ "broadcastnow" ][ "starttime" ]:
                                self.livetv( json_query[ "result" ][ "item" ], live_query[ "result" ][ "channeldetails" ][ "broadcastnow" ], connection )
                        else:
                            self.livetv( json_query[ "result" ][ "item" ], live_query[ "result" ][ "channeldetails" ][ "broadcastnow" ], connection )
                            
                        # Save the current channel, so we can only update on channel change
                        self.playingLiveTV = True
                        self.lastLiveTVChannel = str( json_query[ "result" ][ "item" ][ "id" ] ) + "|" + live_query[ "result" ][ "channeldetails" ][ "broadcastnow" ][ "starttime" ]
                
                elif type == "unknown" and "channel" in json_query[ "result" ][ "item"] and json_query[ "result" ][ "item" ][ "channel" ] != "":
                    self.recordedtv( json_query[ "result" ][ "item" ] )
        
    def movie( self, json_query ):
        # This function extracts the details we want to save from a movie, and sends them to the addToDatabase function
        
        log( repr( json_query ) )
        
        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
        
        # Save this is lastplayed, so the widgets won't display it
        library.lastplayedType = "movie"
        library.lastplayedID = json_query[ "id" ]
        self.movieLastUpdated = 0
        
        # MPAA
        if json_query[ "mpaa" ] != "":
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "mpaa", json_query[ "mpaa" ] )
        
        # Tag
        for tag in json_query[ "tag" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "tag", tag )
        
        # Director(s)
        for director in json_query[ "director" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "director", director )
            
        # Writer(s)
        for writer in json_query[ "writer" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "writer", writer )
            
        # Studio(s)
        for studio in json_query[ "studio" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "studio", studio )
            
        # Genre(s)
        for genre in json_query[ "genre" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "genre", genre )
            
        # Actor(s)
        for actor in json_query[ "cast" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "actor", actor[ "name" ] )
            
        # Is it watched
        if json_query[ "playcount" ] == 0:
            # This is a new movie
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "special", "unwatched" )
        
        # Get additional info from TMDB
        keywords, related = sql.getTMDBExtras( "movie", json_query[ "id" ], json_query[ "imdbnumber" ], json_query[ "year" ] )
        for keyword in keywords:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "keyword", keyword )
        for show in related:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "related", show )        
        
        # Convert dateadded to datetime object
        dateadded = datetime.now() - datetime.strptime( json_query[ "dateadded" ], "%Y-%m-%d %H:%M:%S" )
        
        # How new is it
        if dateadded.days <= 2:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "special", "fresh" )
        if dateadded.days <= 7:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "special", "recentlyadded" )
            
        # Mark played, so we can get percentage unwatched/recent
        sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "special", "playedmedia" )
        
    def episode( self, json_query ):
        # This function extracts the details we want to save from a tv show episode, and sends them to the addToDatabase function
        
        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
                
        # Save this as last played, so the widgets won't display it
        library.lastplayedType = "episode"
        library.lastplayedID = json_query[ "id" ]
        library.tvshowInformation.pop( json_query[ "tvshowid" ], None )
        library.tvshowNextUnwatched.pop( json_query[ "tvshowid" ], None )
        library.tvshowNewest.pop( json_query[ "tvshowid" ], None )
        self.episodeLastUpdated = 0
        
        # TV Show ID
        sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "tvshowid", json_query[ "tvshowid" ] )
        
        # Now get details of the tv show
        show_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": %s, "properties": ["sorttitle", "mpaa", "premiered", "episode", "watchedepisodes", "studio", "genre", "cast", "tag", "imdbnumber" ]}, "id": 1}' % json_query[ "tvshowid" ] )
        show_query = unicode(show_query, 'utf-8', errors='ignore')
        show_query = simplejson.loads(show_query)
        show_query = show_query[ "result" ][ "tvshowdetails" ]
        
        # MPAA
        sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "mpaa", show_query[ "mpaa" ] )
            
        # Studio(s)
        for studio in show_query[ "studio" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "studio", studio )
            
        # Genre(s)
        for genre in show_query[ "genre" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "genre", genre )
            
        # Tag(s)
        for genre in show_query[ "tag" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "tag", tag )
        
        # Actor(s)
        for actor in show_query[ "cast" ]:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "actor", actor[ "name" ] )

        # Is it watched
        if json_query[ "playcount" ] == 0:
            # This is a new episode
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "special", "unwatched" )
            
        # Get additional info from TMDB
        keywords, related = sql.getTMDBExtras( "episode", json_query[ "imdbnumber" ], show_query[ "label" ], show_query[ "premiered" ][:-6] )
        for keyword in keywords:
            log( "Adding keyword " + keyword )
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "keyword", keyword )
        for show in related:
            log( "Adding related " + show )
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "related", show )        
        
        # Convert dateadded to datetime object
        dateadded = datetime.now() - datetime.strptime( json_query[ "dateadded" ], "%Y-%m-%d %H:%M:%S" )
        
        # How new is it
        if dateadded.days <= 2:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "special", "fresh" )
        if dateadded.days <= 7:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "special", "recentlyadded" )
            
        # Mark played, so we can get percentage unwatched/recent
        sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "special", "playedmedia" )
        
    def recordedtv( self, json_query ):
        log( repr( json_query ) )
        # This function extracts the details we want to save from a tv show episode, and sends them to the addToDatabase function
        
        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
        
        # Save this as last played, so the widget won't display it
        library.lastplayedType = "recorded"
        library.lastplayedID = json_query[ "id" ]
        self.pvrLastUpdated = 0
        
        # Channel
        sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "channel", json_query[ "channel" ] )
        
        # Genre(s)
        for genre in json_query[ "genre" ]:
            for splitGenre in genre.split( "/" ):
                sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "genre", splitGenre )
            
        # Is it watched
        if json_query[ "lastplayed" ] == "":
            # This is a new episode
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "special", "unwatched" )
        
        # Convert startime to datetime object
        dateadded = datetime.now() - datetime.strptime( json_query[ "starttime" ], "%Y-%m-%d %H:%M:%S" )
        
        # How new is it
        if dateadded.days <= 2:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "special", "fresh" )
        if dateadded.days <= 7:
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "special", "recentlyadded" )
            
        # Mark played, so we can get percentage unwatched/recent
        sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "special", "playedmedia" )
        
    def livetv( self, json_query, live_query, connection = None ):
        # This function extracts the details we want to save from live tv, and sends them to the addToDatabase function
        
        if connection is None:
            connection = self.connectionWrite
        
        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
        
        # Trigger PVR to be next widget to be updated
        self.pvrLastUpdated = 0
                
        # ChannelType
        sql.addToDatabase( connection, dateandtime, time, day, "live", "channeltype", json_query[ "channeltype" ] )

        # Channel
        sql.addToDatabase( connection, dateandtime, time, day, "live", "channel", json_query[ "channel" ] )
        
        # ChannelNumber
        sql.addToDatabase( connection, dateandtime, time, day, "live", "channelnumber", json_query[ "channelnumber" ] )
        
        # ChannelID
        sql.addToDatabase( connection, dateandtime, time, day, "live", "channelid", json_query[ "id" ] )
        
        # Genre
        for genre in live_query[ "genre" ]:
            for splitGenre in genre.split( "/" ):
                sql.addToDatabase( connection, dateandtime, time, day, "live", "genre", splitGenre )
            
        # Mark played, so we can get percentage unwatched/recent
        sql.addToDatabase( connection, dateandtime, time, day, "live", "special", "playedmedia" )
        sql.addToDatabase( connection, dateandtime, time, day, "live", "special", "playedlive" )
        
    def song( self, json_query ):
        # This function extracts the details we want to save from a song, and sends them to the addToDatabase function
        log( "Local function for parsing playing song" )
        
        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
        
        # Now get details of the album
        log( "Getting album details" )
        album_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"albumid": %s, "properties": [ "title", "description", "artist", "genre", "theme", "mood", "style", "type", "albumlabel", "rating", "year", "musicbrainzalbumid", "musicbrainzalbumartistid", "fanart", "thumbnail", "playcount", "genreid", "artistid", "displayartist" ]}, "id": 1}' % json_query[ "albumid" ] )
        log( "Got album details" )
        album_query = unicode(album_query, 'utf-8', errors='ignore')
        album_query = simplejson.loads(album_query)
        album_query = album_query[ "result" ][ "albumdetails" ]
        
        # Check album has changed
        if library.lastplayedType == "album" and library.lastplayedID == album_query[ "albumid" ]:
            log( "### NOT updating album info" )
            return
            
        log( "### Updating album info" )
        
        # Save album, so we only update data on album change
        library.lastplayedType = "album"
        library.lastplayedID = album_query[ "albumid" ]
        self.albumLastUpdated = 0

        log( repr( album_query ) )
        
        for artist in album_query[ "artist" ]:
            log( artist )
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "artist", artist )
        
        for style in album_query[ "style" ]:
            log( style )
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "style", style )
        
        for theme in album_query[ "theme" ]:
            log( theme )
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "theme", theme )
        
        log( album_query[ "label" ] )
        sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "label", album_query[ "label" ] )
        
        for genre in album_query[ "genre" ]:
            log( genre )
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "genre", genre )
        
        for mood in album_query[ "mood" ]:
            log( mood )
            sql.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "mood", mood )        
        
class Widgets_Player(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.action = kwargs[ "action" ]
        self.ended = kwargs[ "ended" ]

    def onPlayBackStarted(self):
        log( "Playback started" )
        xbmc.sleep(1000)
        log( "Calling local playback started function" )
        self.action()
            
    def onPlayBackEnded(self):
        self.ended()

    def onPlayBackStopped(self):
        self.ended()

log('script (service) version %s started' % __addonversion__)
running = True
try:
    Main()
except:
    log( "script (service) fatal error" )
    print_exc()
running = False
log( "Sending message asked socket to stop listening" )
clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
clientsocket.connect( ( "localhost", 45354 ) )
clientsocket.send( "QUIT" )
clientsocket.close()
log('script (service) version %s stopped' % __addonversion__)