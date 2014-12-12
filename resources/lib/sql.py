# coding=utf-8
import os, sys
from datetime import datetime, timedelta
import xbmc, xbmcgui, xbmcaddon, xbmcvfs, urllib
from traceback import print_exc
    
import sqlite3
import tmdb

import cPickle as pickle

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")
__datapath__     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ )
__datapathalt__  = os.path.join( "special://profile/", "addon_data", __addonid__ )
__skinpath__     = xbmc.translatePath( "special://skin/shortcuts/" ).decode('utf-8')
__defaultpath__  = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'shortcuts').encode("utf-8") ).decode("utf-8")
__xbmcversion__  = xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0]

def log(txt):
    try:
        if isinstance (txt,str):
            txt = txt.decode('utf-8')
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)
    except:
        pass
            
def connect( createTable = False ):
    # Ensure datapath exists
    if not xbmcvfs.exists(__datapath__):
        xbmcvfs.mkdir(__datapath__)
        
    # Connect to the database
    connection = sqlite3.connect( os.path.join( __datapath__, "database.db" ) )
    connection.text_factory = str
    c = connection.cursor()
    
    if createTable:
        # Test code - drop tables
        #c.execute( "DROP TABLE habits" )
        #c.execute( "DROP TABLE episode" )
        #c.execute( "DROP TABLE movie" )
        #connection.commit()
    
        # Check if the default table exists
        c.execute( 'SELECT * FROM sqlite_master WHERE name="habits" AND type="table"')
        
        if len( c.fetchall() ) == 0:
            # No table exists, so create it
            c.execute( '''CREATE TABLE habits (
                id INTEGER NOT NULL PRIMARY KEY,
                datetime TEXT,
                time TEXT,
                day INTEGER,
                media TEXT,
                type TEXT,
                data TEXT
                )''' )
            connection.commit()
        
        # Check if the additional TV info table exists
        c.execute( 'SELECT * FROM sqlite_master WHERE name="episode" AND type="table"')
        
        if len( c.fetchall() ) == 0:
            # No table exists, so create it
            c.execute( '''CREATE TABLE episode (
                id INTEGER NOT NULL PRIMARY KEY,
                itemID INTEGER,
                type TEXT,
                data TEXT
                )''' )
            connection.commit()
            
        # Check if the additional TV info table exists
        c.execute( 'SELECT * FROM sqlite_master WHERE name="movie" AND type="table"')
        
        if len( c.fetchall() ) == 0:
            # No table exists, so create it
            c.execute( '''CREATE TABLE movie (
                id INTEGER NOT NULL PRIMARY KEY,
                itemID INTEGER,
                type TEXT,
                data TEXT
                )''' )
            connection.commit()
        
    # Return the database connection
    c.close()
    return connection
    
def addToDatabase( connection, dateandtime, time, day, media, type, data ):
    c = connection.cursor()
    
    log( 'INSERT INTO habits (datetime, time, day, media, type, data) VALUES ("%s", "%s", %f, "%s", "%s", "%s")' %( dateandtime, time, day, media, type, data ) )
    sucess = False
    while sucess == False:
        try:
            c.execute( 'INSERT INTO habits (datetime, time, day, media, type, data) VALUES ("%s", "%s", %f, "%s", "%s", "%s")' %( dateandtime, time, day, media, type, data ) )
            sucess = True
        except:
            log( "Unable to write to database. Retrying in 1 second" )
            xbmc.sleep( 1000 )
    
    c.close()
    connection.commit()
    
def getFromDatabase( connection, type ):
    c = connection.cursor()
    
    combined = {}
    
    # Build the type part of our query
    if type == "pvr":
        # We need to retrieve both 'recorded' and 'live'
        typeQuery = "(media = 'recorded' OR media = 'live')"
    else:
        typeQuery = "media = '%s'" % type
        
    # Build the order-by part of our query
    orderQuery = "datetime DESC, type"
    
    freshness = [ 0, 0, 0 ]
    
    # Get weekdays at this time
    weight = 100 # 100 - 60
    weightChange = ( ( int( __addon__.getSetting( "dayLimit" ) ) / 7 ) / 40.0 ) * 100
    for x in range( 0, int( __addon__.getSetting( "dayLimit" ) ) + 1, 7 ):
        datetimeStart = str( datetime.now() - timedelta( days = x, hours = int( __addon__.getSetting( "hoursNow" ) ) ) )
        datetimeEnd = str( datetime.now() - timedelta( days = x, hours = -int( __addon__.getSetting( "hoursNow" ) ) ) )
        timeQuery = "datetime BETWEEN '%s' AND '%s'" %( str( datetime.now() - timedelta( days = x, hours = int( __addon__.getSetting( "hoursNow" ) ) ) ), str( datetime.now() - timedelta( days = x, hours = -int( __addon__.getSetting( "hoursNow" ) ) ) ) )
        sucess = False
        while sucess == False:
            try:
                result = c.execute( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, timeQuery, orderQuery ) )
                sucess = True
            except:
                log( "Unable to read from database. Retrying in 1 second" )
                xbmc.sleep( 1000 )
        moreFreshness = combineDatabaseResults( combined, result, float( __addon__.getSetting( "dayRecent" ) ), weight, weightChange, False )
        freshness[ 0 ] += moreFreshness[ 0 ]
        freshness[ 1 ] += moreFreshness[ 1 ]
        freshness[ 2 ] += moreFreshness[ 2 ]
        weight = weight - weightChange
        
    # Get everyday at this time
    weight = 60 # 60 - 30
    weightChange = int( __addon__.getSetting( "timeLimit" ) ) / 30.0
    for x in range( 0, int( __addon__.getSetting( "timeLimit" ) ) + 1, 1 ):
        datetimeStart = str( datetime.now() - timedelta( days = x, hours = int( __addon__.getSetting( "hoursNow" ) ) ) )
        datetimeEnd = str( datetime.now() - timedelta( days = x, hours = -int( __addon__.getSetting( "hoursNow" ) ) ) )
        timeQuery = "datetime BETWEEN '%s' AND '%s'" %( str( datetime.now() - timedelta( days = x, hours = int( __addon__.getSetting( "hoursNow" ) ) ) ), str( datetime.now() - timedelta( days = x, hours = -int( __addon__.getSetting( "hoursNow" ) ) ) ) )
        sucess = False
        while sucess == False:
            try:
                result = c.execute( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, timeQuery, orderQuery ) )
                sucess = True
            except:
                log( "Unable to read from database. Retrying in 1 second" )
                xbmc.sleep( 1000 )
        moreFreshness = combineDatabaseResults( combined, result, float( __addon__.getSetting( "timeRecent" ) ), weight, weightChange, False )
        freshness[ 0 ] += moreFreshness[ 0 ]
        freshness[ 1 ] += moreFreshness[ 1 ]
        freshness[ 2 ] += moreFreshness[ 2 ]
        weight = weight - weightChange
        
    # Get all
    weight = 30 # 30 - 10
    datetimeStart = str( datetime.now() - timedelta( days = int( __addon__.getSetting( "allLimit" ) ) ) )
    datetimeEnd = str( datetime.now() )
    timeQuery = "datetime BETWEEN '%s' AND '%s'" %( str( datetime.now() - timedelta( days = int( __addon__.getSetting( "allLimit" ) ) ) ), str( datetime.now() ) )
    sucess = False
    while sucess == False:
        try:
            result = c.execute( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, timeQuery, orderQuery ) )
            sucess = True
        except:
            log( "Unable to read from database. Retrying in 1 second" )
            xbmc.sleep( 1000 )
    moreFreshness = combineDatabaseResults( combined, result, float( __addon__.getSetting( "timeRecent" ) ), weight, 20, False )
    freshness[ 0 ] += moreFreshness[ 0 ]
    freshness[ 1 ] += moreFreshness[ 1 ]
    freshness[ 2 ] += moreFreshness[ 2 ]
    
    c.close()
    return combined, freshness
    
def combineDatabaseResults( combination, results, freshness, weight = 100, weightChange = 10, showDebug = False ):
    total = 0.00
    fresh = 0.00
    recent = 0.00
    live = 0.00
    recorded = 0.00
    
    habitLimit = int( __addon__.getSetting( "habitLimit" ) )
    
    lastDateTime = None
    lastTag = None
    valueList = []
    
    uncombined = {}
    
    count = -1
    
    for row in results:
        if showDebug:
            log( repr( row ) )
        if row[ 5 ] != "special":
            # If the key doesn't exist in the combination dictionary, add it
            if row[ 5 ] not in combination.keys():
                combination[ row[ 5 ] ] = []
            if row[ 5 ] not in uncombined.keys():
                uncombined[ row[ 5 ] ] = []
                
            # Check that this value doesn't already exist in the combination dictionary
            foundValue = False
            if len( combination[ row[ 5 ] ] ) != 0:
                for weighting, group in combination[ row[ 5 ] ]:
                    for value in group:
                        if value == row[ 6 ]:
                            foundValue = True
                            break
                            
            if len( uncombined[ row[ 5 ] ] ) != 0:
                for weighting, group in uncombined[ row[ 5 ] ]:
                    for value in group:
                        if value == row[ 6 ]:
                            foundValue = True
                            break
                        
            # The value wasn't found
            if foundValue == False:
                if lastDateTime is None or lastDateTime != row[ 1 ]:
                    count += 1
                if lastDateTime is None or lastDateTime != row[ 1 ] or lastTag != row[ 5 ]:
                    if lastDateTime is not None and len( valueList ) != 0 and len( combination[ lastTag ] ) < habitLimit:
                        # Add what we've previously saved to the combination dictionary
                        uncombined[ lastTag ].append( ( count, valueList ) )
                    # Reset lastDateTime, lastTag, valueList
                    lastDateTime = row[ 1 ]
                    lastTag = row[ 5 ]
                    valueList = [ row[ 6 ] ]
                else:
                    valueList.append( row[ 6 ] )
        else:
            if row[ 6 ] == "playedmedia":
                total += row[ 7 ]
            elif row[ 6 ] == "fresh":
                fresh += row[ 7 ]
            elif row[ 6 ] == "recentlyadded":
                recent += row[ 7 ]
            elif row[ 6 ] == "playedlive":
                live += row[ 7 ]
                
    # We've processed all rows, so add the last tag we found
    if lastDateTime is not None and len( valueList ) != 0:
        # Add what we've previously saved to the combination dictionary
        uncombined[ lastTag ].append( ( count, valueList ) )
        
    # Now add to combined database, replacing count with weight
    count += 1
    if count != 0:
        weightChange = float( weightChange ) / count
    else:
        weightChange = 0
        
    for key in uncombined.keys():
        for group, group2 in uncombined[ key ]:
            combination[ key ].append( ( weight - ( weightChange * group ), group2 ) )
    
    if total != 0:
        if fresh != 0:
            fresh = ( fresh / total ) * freshness
        if recent != 0:
            recent = ( recent / total ) * freshness
        if live != 0:
            live = ( live / total ) * freshness
            
        return[ int( fresh ), int( recent ), int( live ) ]
    else:
        return [ 0, 0, 0 ]

def getTMDBExtras( type, itemID, name, year ):
    connection = connect()
    c = connection.cursor()
    
    # Trim any year from the name (improves results)
    try:
        if name[ -6 ] == "(":
            name = name[:-7]
    except:
        # Name probably too short
        pass
    
    # Query database for additional information
    sucess = False
    while sucess == False:
        try:
            results = c.execute( "SELECT type, data FROM %s WHERE itemID = '%s'" %( type, itemID ) )
            sucess = True
        except:
            log( "Unable to read from database. Retrying in 1 second" )
            xbmc.sleep( 1000 )
    
    keywords = []
    related = []
    
    retrieved = False
    
    for row in results:
        if row[ 0 ] == "Keyword":
            keywords.append( row[ 1 ].decode( "utf-8" ) )
        if row[ 0 ] == "Related":
            related.append( row[ 1 ].decode( "utf-8" ) )
        if row[ 0 ] == "Updated":
            retrieved = True
        
    c.close()
    
    if retrieved:
        return( keywords, related )
        
    # No extra information - go get it :)
    if __addon__.getSetting( "getTMDB" ) == "false":
        # Actually, don't get it
        return( [], [] )
    
    if type == "episode":
        # Get the ID of the show
        response = tmdb.GetTMDBTVShow( name, year )
        
        if response is None:
            xbmc.sleep( 300 )
            log( "No response" )
            return( [], [] )
        
        for tmdbResponse in response:
            if "id" in tmdbResponse.keys():
                # Get the related and keywords
                response2 = tmdb.GetTMDBTVShowDetails( tmdbResponse[ "id" ] )
                
                if response2 is None:
                    xbmc.sleep( 300 )
                    return( [], [] )
                    
                # Process keywords
                if "keywords" in response2 and "results" in response2[ "keywords" ]:
                    keywordData = response2[ "keywords" ][ "results" ]
                    for keyword in keywordData:
                        keywords.append( keyword[ "name" ].lower() )
                else:
                    keywords = None
                    
                # Process related
                if "similar" in response2 and "results" in response2[ "similar" ]:
                    relatedData = response2[ "similar" ][ "results" ]
                    for show in relatedData:
                        related.append( show[ "name" ].lower() )
                else:
                    related = None
            break
    elif type == "movie":
        # Get the ID of the movie
        response = tmdb.GetTMDBMovie( name, year )
        
        if response is None:
            xbmc.sleep( 300 )
            log( "No response" )
            return( [], [] )
        
        for tmdbResponse in response:
            if "id" in tmdbResponse.keys():
                # Get the related and keywords
                response2 = tmdb.GetTMDBMovieDetails( tmdbResponse[ "id" ] )
                
                if response2 is None:
                    xbmc.sleep( 300 )
                    return( [], [] )
                    
                # Process keywords
                if "keywords" in response2 and "keywords" in response2[ "keywords" ]:
                    keywordData = response2[ "keywords" ][ "keywords" ]
                    for keyword in keywordData:
                        keywords.append( keyword[ "name" ].lower() )
                else:
                    keywords = None
                    
                # Process related
                if "similar" in response2 and "results" in response2[ "similar" ]:
                    relatedData = response2[ "similar" ][ "results" ]
                    for movie in relatedData:
                        related.append( movie[ "title" ].lower() )
                else:
                    related = None
            break
    
    if keywords is None or related is None:
        xbmc.sleep( 300 )
        return( [], [] )
    
    # If we got extra data, save it to the database
    c = connection.cursor()
    sucess = False
    while sucess == False:
        try:
            c.execute( 'INSERT INTO %s (itemID, type, data) VALUES ( "%s", "%s", "%s" )' %( type, itemID, "Updated", str( datetime.now() ) ) )
            sucess = True
        except:
            log( "Unable to write to database. Retrying in 1 second" )
            xbmc.sleep( 1000 )
    for data in keywords:
        sucess = False
        while sucess == False:
            try:
                c.execute( 'INSERT INTO %s (itemID, type, data) VALUES ( "%s", "%s", "%s" )' %( type, itemID, "Keyword", data ) )
                sucess = True
            except:
                log( "Unable to write to database. Retrying in 1 second" )
                xbmc.sleep( 1000 )
    for data in related:
        sucess = False
        while sucess == False:
            try:
                c.execute( 'INSERT INTO %s (itemID, type, data) VALUES ( "%s", "%s", "%s" )' %( type, itemID, "Related", data ) )
                sucess = True
            except:
                log( "Unable to write to database. Retrying in 1 second" )
                xbmc.sleep( 1000 )
    
    sucess = False
    while sucess == False:
        try:
            connection.commit()
            sucess = True
        except:
            log( "Unable to write to database. Retrying in 1 second" )
            xbmc.sleep( 1000 )

    xbmc.sleep( 300 )
    c.close()
    return( keywords, related )