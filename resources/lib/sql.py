# coding=utf-8
import os, sys
from datetime import datetime, timedelta
import xbmc, xbmcgui, xbmcvfs, urllib
from traceback import print_exc
    
import sqlite3
import tmdb

import cPickle as pickle

__addon__        = sys.modules[ "__main__" ].__addon__
__addonid__      = sys.modules[ "__main__" ].__addonid__
__addonversion__ = sys.modules[ "__main__" ].__addonversion__
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
    #orderQuery = "type, COUNT(data) DESC"
    #dayOrder = "type, COUNT(data) DESC"
    #timeOrder = "type, COUNT(data) DESC"
    #allOrder = "type, COUNT(data) DESC"
    
    #altOrder = "datetime DESC, type"
    #if type == "movie":
    #    if __addon__.getSetting( "movieDayOrder" ) == "true":
    #        dayOrder = altOrder
    #    if __addon__.getSetting( "movieTimeOrder" ) == "true":
    #        timeOrder = altOrder
    #    if __addon__.getSetting( "movieAllOrder" ) == "true":
    #        allOrder = altOrder
    #elif type == "episode":
    #    if __addon__.getSetting( "tvDayOrder" ) == "true":
    #        dayOrder = altOrder
    #    if __addon__.getSetting( "tvTimeOrder" ) == "true":
    #        timeOrder = altOrder
    #    if __addon__.getSetting( "tvAllOrder" ) == "true":
    #        allOrder = altOrder
    #elif type == "album":
    #    if __addon__.getSetting( "albumDayOrder" ) == "true":
    #        dayOrder = altOrder
    #    if __addon__.getSetting( "albumTimeOrder" ) == "true":
    #        timeOrder = altOrder
    #    if __addon__.getSetting( "albumAllOrder" ) == "true":
    #        allOrder = altOrder
    #elif type == "pvr":
    #    if __addon__.getSetting( "pvrDayOrder" ) == "true":
    #        dayOrder = altOrder
    #    if __addon__.getSetting( "pvrTimeOrder" ) == "true":
    #        timeOrder = altOrder
    #    if __addon__.getSetting( "pvrAllOrder" ) == "true":
    #        allOrder = altOrder
    
    freshness = [ 0, 0, 0 ]
            
    # Get weekdays at this time
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
        moreFreshness = combineDatabaseResults( combined, result, float( __addon__.getSetting( "dayRecent" ) ), False )
        freshness[ 0 ] += moreFreshness[ 0 ]
        freshness[ 1 ] += moreFreshness[ 1 ]
        freshness[ 2 ] += moreFreshness[ 2 ]
        
    # Get everyday at this time
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
        moreFreshness = combineDatabaseResults( combined, result, float( __addon__.getSetting( "timeRecent" ) ), False )
        freshness[ 0 ] += moreFreshness[ 0 ]
        freshness[ 1 ] += moreFreshness[ 1 ]
        freshness[ 2 ] += moreFreshness[ 2 ]
        
    # Get all
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
    moreFreshness = combineDatabaseResults( combined, result, float( __addon__.getSetting( "timeRecent" ) ), False )
    freshness[ 0 ] += moreFreshness[ 0 ]
    freshness[ 1 ] += moreFreshness[ 1 ]
    freshness[ 2 ] += moreFreshness[ 2 ]
        
    c.close()
    return combined, freshness

        
    # Build the time-limit part of our query
    episodeLimit = "datetime > '%s'" % str( datetime.now() - timedelta( hours = int( __addon__.getSetting( "hoursNow" ) ) ) )
    dayLimit = "datetime > '%s'" % str( datetime.now() - timedelta( days = int( __addon__.getSetting( "dayLimit" ) ) + 2 ) )
    timeLimit = "datetime > '%s'" % str( datetime.now() - timedelta( days = int( __addon__.getSetting( "timeLimit" ) ) ) - timedelta( hours = 12 ) )
    allLimit = "datetime > '%s'" % str( datetime.now() - timedelta( days = int( __addon__.getSetting( "allLimit" ) ) ) - timedelta( hours = 12 ) )
        
    timeNow = datetime.now()
    
    # Get datetime objects for now -/+ users choice
    hourtimeStart = timeNow - timedelta( hours = int( __addon__.getSetting( "hoursNow" ) ) )
    hourtimeEnd = timeNow + timedelta( hours = int( __addon__.getSetting( "hoursNow" ) ) )
    
    # Get time strings
    hourStart = str( "%02d:%02d" %( hourtimeStart.hour, hourtimeStart.minute ) )
    hourEnd = str( "%02d:%02d" %( hourtimeEnd.hour, hourtimeEnd.minute ) )
    
    log( repr( hourStart ) + " > " + repr( hourEnd ) )
    
    # Build our query for everything we do +/- 2 hours daily
    if hourtimeStart.hour > hourtimeEnd.hour:
        # Every day
        timeQuery = "((time BETWEEN '%s' AND '24:00') OR (time BETWEEN '00:00' AND '%s'))" %( hourStart, hourEnd )
        
        # Just today
        dayQuery = "((day = %f AND time >= '%s') OR (day = %f AND time <= '%s' ))" %(hourtimeStart.weekday(), hourStart, hourtimeEnd.weekday(), hourEnd)
    else:
        # Every day
        timeQuery = "(time BETWEEN '%s' AND '%s')" %( hourStart, hourEnd )
        
        # Just today
        dayQuery = "((time BETWEEN '%s' AND '%s') AND day = %f)" %( hourStart, hourEnd, hourtimeStart.weekday() )
        
    # Perform recent episode query
    if type == "episode":
        #log( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, episodeLimit, dayOrder ) )
        dayResult = c.execute( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, episodeLimit, dayOrder ) )
        freshness = combineDatabaseResults( combined, dayResult, float( __addon__.getSetting( "dayRecent" ) ), False )
    
    # Perform day query
    #log( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, dayQuery, dayLimit, dayOrder ) )
    dayResult = c.execute( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, dayQuery, dayLimit, dayOrder ) )
    freshness = combineDatabaseResults( combined, dayResult, float( __addon__.getSetting( "dayRecent" ) ), False )
        
    # Perform time query
    #log( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, timeQuery, timeLimit, timeOrder ) )
    timeResult = c.execute( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, timeQuery, timeLimit, timeOrder ) )
    moreFreshness = combineDatabaseResults( combined, timeResult, float( __addon__.getSetting( "timeRecent" ) ), False )
    
    freshness[ 0 ] += moreFreshness[ 0 ]
    freshness[ 1 ] += moreFreshness[ 1 ]
    freshness[ 2 ] += moreFreshness[ 2 ]
    
    # Perform all query
    #log( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, allLimit, allOrder ) )
    allResult = c.execute( "SELECT *, COUNT(data) FROM habits WHERE %s AND %s GROUP BY type, data ORDER BY %s" %( typeQuery, allLimit, allOrder ) )
    moreFreshness = combineDatabaseResults( combined, allResult, float( __addon__.getSetting( "allRecent" ) ) )
    
    freshness[ 0 ] += moreFreshness[ 0 ]
    freshness[ 1 ] += moreFreshness[ 1 ]
    freshness[ 2 ] += moreFreshness[ 2 ]
    
    return combined, freshness
    
def combineDatabaseResults( combination, results, freshness, showDebug = False ):
    total = 0.00
    fresh = 0.00
    recent = 0.00
    live = 0.00
    recorded = 0.00
    
    habitLimit = int( __addon__.getSetting( "habitLimit" ) )
    
    lastDateTime = None
    lastTag = None
    valueList = []
    
    for row in results:
        if showDebug:
            log( repr( row ) )
        if row[ 5 ] != "special":
            # If the key doesn't exist in the combination dictionary, add it
            if row[ 5 ] not in combination.keys():
                combination[ row[ 5 ] ] = []
                
            # Check that this value doesn't already exist in the combination dictionary
            foundValue = False
            if len( combination[ row[ 5 ] ] ) != 0:
                for group in combination[ row[ 5 ] ]:
                    for value in group:
                        if value == row[ 6 ]:
                            foundValue = True
                            break
                    if foundValue == True:
                        break
                        
            # The value wasn't found
            if foundValue == False:
                if lastDateTime is None or lastDateTime != row[ 1 ] or lastTag != row[ 5 ]:
                    if lastDateTime is not None and len( valueList ) != 0 and len( combination[ lastTag ] ) < habitLimit:
                        # Add what we've previously saved to the combination dictionary
                        combination[ lastTag ].append( valueList )
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
        combination[ lastTag ].append( valueList )
        
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

        
def combineDatabaseResultsOld( combination, results, freshness, showDebug = False ):
    total = 0.00
    fresh = 0.00
    recent = 0.00
    live = 0.00
    recorded = 0.00
    
    habitLimit = int( __addon__.getSetting( "habitLimit" ) )
    
    lastDateTime = None
    lastTag = None

    for row in results:
        if showDebug == True:
            log( repr( row ) )
        if row[ 5 ] != "special":
            if lastDateTime is not None:
                if row[ 1 ] != lastDateTime or row[ 5 ] != lastTag:
                    # Changed DateTime or Tag - add what we've got to the combined
                    pass
                    
            # If the key doesn't exist in the combination dictionary, add it
            if row[ 5 ] not in combination.keys():
                combination[ row[ 5 ] ] = []
                
            # If we have less than the number of habits specified in settings, add this item to the dictionary
            if len( combination[ row[ 5 ] ] ) < habitLimit:
                found = False
                for data in combination[ row[ 5 ] ]:
                    if data == row[ 6 ]:
                        found = True
                        
                if found == False:
                    combination[ row[ 5 ] ].append( row[ 6 ] )
        else:
            if row[ 6 ] == "playedmedia":
                total += row[ 7 ]
            elif row[ 6 ] == "fresh":
                fresh += row[ 7 ]
            elif row[ 6 ] == "recentlyadded":
                recent += row[ 7 ]
            elif row[ 6 ] == "playedlive":
                live += row[ 7 ]
                
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
            keywords.append( row[ 1 ] )
        if row[ 0 ] == "Related":
            related.append( row[ 1 ] )
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