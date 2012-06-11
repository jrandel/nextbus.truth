# nextmunipy.py module
# written by Jason Randel
# original version: 2012/05/14

from xml.dom import minidom
import urllib2
import numpy
import time
import warnings
from datetime import datetime, timedelta
# import nmvis


# some definitions
MAX_STOPS_PER_PREDICTION = 150
MIN_TIME_BETWEEN_REQUESTS = 45
STOP_DATABASE_FILENAME = '/users/jason/documents/python work/NextMuniStopDatabase.dat'
KEEP_PREDICTION_XML = False


# a struct for holding characters used to parse/write data files,
#    as well as the 
class StopDatabaseParser:
    def __init__(self):
        self.databaseFilename = STOP_DATABASE_FILENAME
        self.separator = '; '
        self.assigner = '='
        self.separator_2 = ','
        self.stopTag = 'stopTag'
        self.nameTag = 'name'
        self.latTag = 'lat'
        self.lonTag = 'lon'
        self.idTag = 'id'
        self.routesTag = 'routes'
        self.routeDirTag = 'routedirs'
        self.commentTag = '#'
        self.order = ['routeTag', 'stopTag', 'vehicle', 'directionTag', \
                      'startTime', 'endTime', 'currentTime', \
                      'predictedWait', 'actualWait', 'uncertainty',
                      'latitude', 'longitude']
    
    # methods for getting index corredsponding to data columns
    def index(self, aString): return self.order.index(aString)
    def routeIndex(self): return self.index('routeTag')
    def stopIndex(self): return self.index('stopTag')
    def vehicleIndex(self): return self.index('vehicle')
    def directionIndex(self): return self.index('directionTag')
    def dirIndex(self): return self.index('directionTag')
    def startTimeIndex(self): return self.index('startTime')
    def stopTimeIndex(self): return self.index('endTime')
    def endTimeIndex(self): return self.index('endTime')
    def currentTimeIndex(self): return self.index('currentTime')
    def predIndex(self): return self.index('predictedWait')
    def predictionIndex(self): return self.index('predictedWait')
    def predictedWaitIndex(self): return self.index('predictedWait')
    def predWaitIndex(self): return self.index('predictedWait')
    def pwIndex(self): return self.index('predictedWait')
    def waitIndex(self): return self.index('actualWait')
    def realWaitIndex(self): return self.index('actualWait')
    def rwIndex(self): return self.index('actualWait')
    def awIndex(self): return self.index('actualWait')
    def uncertaintyIndex(self): return self.index('uncertainty')
    def deltaIndex(self): return self.index('uncertainty')
    def latitudeIndex(self): return self.index('latitude')
    def latIndex(self): return self.index('latitude')
    def longitudeIndex(self): return self.index('longitude')
    def lonIndex(self): return self.index('longitude')
    
		
  
  
def listOfAttributesFromList(theList, attrName):
    newList = []
    print 'hi'
    for a in theList:
        newList.append(getattr(a, attrName))
    return newList
    
# general function for sending commands to NextBus API
def sendCommand(cmdStr):

    baseURL = 'http://webservices.nextbus.com/service/publicXMLFeed?command='
    cmdStr = cmdStr.replace(' ', '+')
    url = baseURL + cmdStr
    
    f = urllib2.urlopen(url)

    if f.code != 200:
        raise Exception('Error: url request code is ' + str(f.code) + '; quitting.')

    result = minidom.parse(f)

    #if result.getElementsByTagName("Error"):        
    #    raise Exception('An error occurred while parsing XML results from URL:\n' + url + '\nError:\n' + str(result.getElementsByTagName("Error")))
        
    return result
    
  
# gets predictions for all stops specified in route  
#    returns (minutes, seconds, currentTime)
#    minutes & seconds are lists of lists, where the outer list corresponds
#    to stops, and the inner list corresponds to the upcoming busses at each stop
def getMultiStopPrediction(routeTagList, stopList):

    # stopList must be a list
    if type(stopList) == str: stopList = [stopList]
    elif type(stopList) == list and type(stopList[0]) != str:
        try:
            stopList = BusStop().getTags(stopList)
        except:
            raise Exception('Input must be a list of stops or stop tags (strings).')
    
    # force tag input to be a list of same length as stopList
    if type(routeTagList) == str:
        routeTagList = [routeTagList] * len(stopList)
    elif type(routeTagList) == list and len(routeTagList) == 1:
        routeTagList = [routeTagList[0]] * len(stopList)
        
    # make sure lists are the same length
    if len(routeTagList) != len(stopList):
        raise Exception('routeTagList and stopList must be same length')
    
    # check stopList length; if greater than allowed, split request in half recursively.
    if len(stopList) > MAX_STOPS_PER_PREDICTION:
    
        warnings.warn('Number of stops requested (%i) exceeds maximum allowed (%i).\n' \
                      '  Attempting to split request in two...' % (len(stopList), MAX_STOPS_PER_PREDICTION))
        try:
            halfway = int(numpy.ceil(len(stopList) / 2.0))
            predList1 = getMultiStopPrediction(routeTagList[:halfway], stopList[:halfway])
            predList2 = getMultiStopPrediction(routeTagList[halfway:], stopList[halfway:])
            nStops = len(numpy.unique( [p.stopTag for p in predList1] + [p.stopTag for p in predList2] ))
            if len(predList1 + predList2) != nStops:
                warnings.warn('Recursive call to getMultiStopPrediction did not return the right number of stops\n' + 
                              '  (%i predictions for %i stops)' % (nStops, len(stopList)))
            return (predList1 + predList2)
        except:
            warnings.warn('Could not split stop request in half.  Keeping only the first %i stops.' % MAX_STOPS_PER_PREDICTION)
            stopList = stopList[0:MAX_STOPS_PER_PREDICTION]
        
        
    # BUILD REQUEST STRING
    cmdStr = 'predictionsForMultiStops&a=sf-muni'
    for tag, stop in zip(routeTagList, stopList):
        shortTag = tag.split('_')[0]
        cmdStr += '&stops=%s|%s' % (shortTag, stop)

    xmlData = sendCommand(cmdStr)

    # check for a returned error
    if xmlData.getElementsByTagName("Error"):
        raise Exception('Error in getting prediction data.')

    xmlByStop = xmlData.getElementsByTagName("predictions")

    sec = []
    min = []
    predictionList = []
    currentTime = datetime.now()
    
    thePredictions = []    
        
    for xs in xmlByStop:
        
        routeTag = None; routeName = None; stopTag = None; stopName = None
        if xs.hasAttribute('routeTag'): routeTag = str(xs.getAttribute('routeTag'))
        if xs.hasAttribute('routeTitle'): routeName = str(xs.getAttribute('routeTitle'))
        if xs.hasAttribute('stopTag'): stopTag = str(xs.getAttribute('stopTag'))
        if xs.hasAttribute('stopTitle'): stopName = str(xs.getAttribute('stopTitle'))
        stopName = stopName.replace('&amp;', '&')
        
        xmlByDir = xs.getElementsByTagName("direction")
        
        dirs = []
        for xd in xmlByDir:
            directionName = None
            if xd.hasAttribute('title'): directionName = xd.getAttribute('title')

            xmlByPred = xd.getElementsByTagName("prediction")

            for xp in xmlByPred:
                newPrediction = Prediction(xp)
                newPrediction.routeTag = routeTag
                newPrediction.routeName = routeName
                newPrediction.stopTag = stopTag
                newPrediction.stopName = stopName
                newPrediction.directionName = directionName
                newPrediction.currentTime = currentTime
                
                predictionList.append(newPrediction)
                sec.append(newPrediction.getSeconds())
                min.append(newPrediction.getMinutes())
    
    return predictionList
    # return (min, sec, currentTime, predictionList)
    
       
# gets predictions for all stops specified in route  
#    returns (minutes, seconds, currentTime)
#    minutes & seconds are lists of lists, where the outer list corresponds
#    to stops, and the inner list corresponds to the upcoming busses at each stop
def getMultiStopPredictionOld(routeTagList, stopList):

    # stopList must be a list
    if type(stopList) == str: stopList = [stopList]
    
    # check stopList length
    if len(stopList) > MAX_STOPS_PER_PREDICTION:
        warnings.warn('Number of stops requested (%i) exceeds maximum allowed (%i).\n' \
            '  Keeping only the first %i.' % (len(stopList), MAX_STOPS_PER_PREDICTION, MAX_STOPS_PER_PREDICTION))
        stopList = stopList[0:MAX_STOPS_PER_PREDICTION]
        
    # force tag input to be a list of same length as stopList
    if type(routeTagList) == str:
        routeTagList = [routeTagList] * len(stopList)
    elif type(routeTagList) == list and len(routeTagList) == 1:
        routeTagList = [routeTagList[0]] * len(stopList)
        
    # make sure lists are the same length
    if len(routeTagList) != len(stopList):
        raise Exception('routeTagList and stopList must be same length')
        
	# build command string
    cmdStr = 'predictionsForMultiStops&a=sf-muni'
    for tag, stop in zip(routeTagList, stopList):
        shortTag = tag.split('_')[0]
        cmdStr += '&stops=%s|%s' % (shortTag, stop)

    xmlData = sendCommand(cmdStr)

    # check for a returned error
    if xmlData.getElementsByTagName("Error"):
        raise Exception('Error in getting prediction data.')

    # get the stop and direction info from the first xml block
    xmlStop = xmlData.getElementsByTagName("predictions")
    if not xmlStop: xmlStop = None
    
    # extract predictions in mins, secs	
    pred = xmlData.getElementsByTagName("prediction")

    sec = []
    min = []
    predictionList = []
    currentTime = datetime.now()
    
    #for (p,st) in (pred, stopList):
    for p in pred:
        # make a new Prediction instance, add it to the list 
        predObj = Prediction(p, xmlStop)
        predObj.setTimeStamp(currentTime)
        predictionList.append(predObj)	
        
        s = int(p.getAttribute("seconds"))
        m = int(p.getAttribute("minutes"))
        sec.append(s)
        min.append(m)

    return (min, sec, currentTime, predictionList)
    
        
# get all predictions for a given bus object and direction string        
#def getPredictionsForBusAndDirection(bus, direction):
    #return getMultiStopPrediction(bus.
    return None
    


# utility functions not specific to a particular line/stop:
def routeFromString(aStr):
    # aStr is of the format '12_OB1', '12', 'F_OBCSTRO', etc
    s = aStr.split('_')
    if not s: return None
    return s[0]
   
def routeAndDirectionTagFromString(aStr):
    import re
    # aStr is of the format '12_OB1', '12', 'F_OBCSTRO', etc
    s = aStr.split('_')
    if not s: return None
    r = s[0]
    if len(s) > 1:
        d = s[1]
        ii = d.lower().find('ib')
        io = d.lower().find('ob')
        if ii == 0 or io == 0:
            a = d.split(d[0:2])
            a = a[1]	# a[0] should always be ''
            d = '_' + d[0:2]
            m = re.findall(r'\d+', a)
            if len(m) > 0:
                d += m[0]
        else: d = ''
        
    else: d = ''
    
    return (r + d)

  
  
  
#
# Prediction
#
class Prediction:

    # called by both __init__ and __init__(xml)
    def initialSetup(self):
        self.routeTag = None
        self.stopTag = None
        self.routeName = None        
        self.stopName = None
        self.directionName = None
        self.timeStamp = None	# this is set internally, when the prediction is downloaded.
        
        # the following are set externally:
        self.startTime = None
        self.endTime = None
        self.actualWait = None
        self.uncertainty = None
        self.currentTime = None	  # this is set by a controlling class, so the time of download can be managed
        
        self.minutes = []; self.seconds = []
        self.vehicle = None; self.block = None; self.tripTag = None
        self.isLayovered = None; self.isDeparture = None
        self.epochTime = []; self.isComplete = False
        
    
    def __init__(self, xml=None):
        
        self.initialSetup()
        if not xml: return
        
        self.timeStamp = datetime.now()
        hasAllAttributes = True
        
        if KEEP_PREDICTION_XML: self.xml = xml
        
        if xml.hasAttribute('minutes'): self.minutes = int(xml.getAttribute('minutes')); 
        else: hasAllAttributes = False
        if xml.hasAttribute('seconds'): self.seconds = int(xml.getAttribute('seconds')); 
        else: hasAllAttributes = False
        if xml.hasAttribute('vehicle'): self.vehicle = str(xml.getAttribute('vehicle')); 
        else: hasAllAttributes = False
        if xml.hasAttribute('block'): self.block = str(xml.getAttribute('block')); 
        else: hasAllAttributes = False
        if xml.hasAttribute('tripTag'): self.tripTag = str(xml.getAttribute('tripTag')); 
        else: hasAllAttributes = False
        if xml.hasAttribute('affectedByLayover'): self.isLayovered = bool(xml.getAttribute('affectedByLayover')); 
        else: hasAllAttributes = False
        if xml.hasAttribute('isDeparture'): self.isDeparture = bool(xml.getAttribute('isDeparture')); 
        else: hasAllAttributes = False
        if xml.hasAttribute('epochTime'): self.epochTime = int(xml.getAttribute('epochTime')); 
        else: hasAllAttributes = False
        if xml.hasAttribute('dirTag'): self.directionTag = str(xml.getAttribute('dirTag')); 
        else: hasAllAttributes = False
        if not self.routeTag: self.routeTag = self.directionTag.split('_')[0]
        self.isComplete = hasAllAttributes

    
    #
    #
    # BASIC METHODS
    
    def __len__(self):
        if self.stopTag: return 1
        else: return 0
        
        
    #
    #
    # "ACCESSORS"
        
    def setStartTime(self, t):
        self.startTime = t
        
    def setEndTime(self, t, delta=0.0):
        self.endTime = t
        w = self.calcActualWait()
        self.setUncertainty(delta)
              
    def setCurrentTime(self, t=None):
        if t is None: t = datetime.now()
        self.currentTime = t
    
    
    def setUncertainty(self, delta=0.0):
        self.uncertainty = delta
        
    def getMinutes(self):
        return self.minutes
    
    def getSeconds(self):
        return self.seconds
        
    def getVehicle(self):
        return self.vehicle
        
    def getStopTag(self):
        if self.stopTag: return self.stopTag
        else: return None

    
    #
    #
    # OTHER METHODS
    
    # calculate the real wait time from the stop and arrival (current) times
    def calcActualWait(self):
        if self.actualWait and (self.actualWait > 0.0):
            wait1 = self.actualWait
            wait2 = self.endTime - self.currentTime
            wait2 = wait2.total_seconds()
            self.actualWait = (wait1 + wait2) / 2.0
        else:
            self.actualWait = self.endTime - self.currentTime
            self.actualWait = self.actualWait.total_seconds() / 60.0
        return self.actualWait
    
    # print the prediction to screen    
    def show(self, params='short'):
        print "PREDICTION FOR ROUTE " + self.routeTag
        print '  --> Stop Tag:  ' + self.getStopTag()
        print '  --> Minutes:   ' + str(self.minutes)
        print '  --> Seconds:   ' + str(self.seconds)
        print '  --> Direction: ' + (self.directionTag)
        print '  --> Vehicle:   ' + (self.vehicle)
        if (type(params) == str) and (params.lower() in ['long','full','all','l']):
            print '  --> Block:    ' + (self.block)
            print '  --> Trip:     ' + (self.tripTag)
            print '  --> Layover:  ' + str(self.isLayovered)
            print '  --> Departure: ' + str(self.isDeparture)
            print '  --> Epoch Time: ' + str(self.epochTime)
        if not self.isComplete: print '  --> Incomplete prediction record'
        
 
# 
# PredictionList
#
class PredictionList:

    def __init__(self):
        self.predictions = []
        self.timeOfPredictions = []
    
    def __init__(self, newPredList):
        if type(newPredList) is not list:
            newPredList = [newPredList]
        
        if len(newPredList) == 0: return None
        
        # make sure newPredList contains prediction instances   
        try:
            newPredList[0].getVehicle()    
        except:
            raise Exception('PredictionList can only be initialized with a list of predictions')
        
        self.predictions = newPredList
        
    
    # get the list to operate like a real list
    # index (i.e., x = ['a',1,2,'b']; x.index('a') returns 0, x.index(1) returns 1, etc.
    def __index__(self, item):
        return self.predictions.index(item)
    def index(self, item):
        return self.predictions.index(item)
            
    # length    
    def __len__(self):
        return len(self.predictions)
    def len(self):
        return len(self.predictions)
    
    # getitem         
    def __getitem__(self, indices):
        return self.predictions[indices]
    def getitem(self, indices):
        return self.predictions[indices]
        # newList = []
        # if type(indices) == int: return self.predictions[indices]
        # for i in indices:
        #     newList.append(self.predictions[i])
        # return newList
        
    # returns a dictionary of prediction lists sorted by vehicle (key = vehicle)
    def sortByVehicle(self, preds=None):
        newDict = {}
        
        # default to the predictions list
        if preds == None: preds = self.predictions
        
        for p in preds:
            try:
                newDict[p.vehicle].append(p)
            except KeyError:    # this means newDict[p.vehicle] does not exist yet; make it
                newDict[p.vehicle] = [p]
                
        for k in newDict.keys():
            newDict[k] = PredictionList(newDict[k])
        return newDict
        
       
    # another "Class" method to get all vehicle tags in a predicionList 
    def getVehicles(self, preds=None):
        # default to the predictions list
        if preds == None: preds = self.predictions
        v = []
        for p in preds:
            if p.vehicle not in v: v.append(p.vehicle)
        return v
        
    
    def getMinutes(self):
        m = numpy.ones(len(self.predictions)) * -1
        for i in range(len(self.predictions)):
            p = self.predictions[i]
            m[i] = p.getMinutes()
        
            
            
    # "Class" method for getting the prediction minutes for a certain vehicle in the list
    def predictionTimesForVehicle(self, vehicleTag, predList=None):
        
        # default to the predictions list
        if predList == None: predList = self.predictions
        
        if type(predList) is not list: predList = predList.predictions
        
        predDict = self.sortByVehicle(predList)
        if type(vehicleTag) is not str: vehicleTag = str(vehicleTag)
        
        # get the predictions corresponding to vehicle tag
        try:
            preds = predDict[vehicleTag]
        except KeyError:
            return []
            #raise Exception('Vehicle ' + vehicleTag + ' does not appear in the supplied list of predictions')
            
        if type(preds) is not list: preds = preds.predictions
        
        # loop over predictions, and extract them
        sec = -1.0 * numpy.ones((len(preds),1))
        min = -1.0 * numpy.ones((len(preds),1))
        
        for i in range(len(preds)):
            p = preds[i]
            if p.seconds > 0: sec[i] = p.seconds
            if p.minutes > 0: min[i] = p.minutes
            
        return (min, sec)
            
    # instance version of the above method
    #def predictionTimesForVehicle(self, vehicleTag):
    #    return self.predictionTimesForVehicle(self.predictions, vehicleTag)
    
    # show all predictions
    def show(self, arg='short'):
        print "PREDICTION LIST FOR ROUTE " + self.predictions[0].routeTag + " (" + self.predictions[0].directionTag + ")"
        for p in self.predictions:
            optStr = ''
            if (type(arg) == str) and (arg.lower() in ['long','full','all','l']):
                optStr = '  (' + p.stopName + '; ' + p.directionName + ')'
            print "  Stop " + p.getStopTag() + " --> " + str(p.getMinutes()) + " min" + optStr
           
           
        

#
# BusRoute
#
class BusRoute:
    # routeTag, routeName, directionList, stops
    
    #	 initializer
    def setup(self):
        self.stops = []
        self.routeTag = ''
        self.routeName = ''
        self.directionList = {}
        self.directionTags = {}
        self.stopOrder = {}
        
    # initializer with a tag (string or xml data)
    def __init__(self, tag=None):
        self.setup()
        if not tag: return
        
        if type(tag) == str:
            self.initByRouteTag(tag)
        elif type(tag) == instance:
            self.downloadRouteInfo(tag)
        else:
            raise Exception('Invalid input type: ' + type(tag))
    
    
    # display the route info for an instance
    def show(self, params='short'):
        print "ROUTE " + self.routeTag
        print "  Name: " + self.routeName
        print "  Directions: "
        print self.directionList
        print "  Direction tags: "
        print self.directionTags
        
        # show all stops, if asked to do so
        if (type(params) == str) and ('long' in params.lower() or 'stops' in params.lower()):
			for dir in self.directionList.keys():
				print "  " + dir + " stops:"
				for tag in self.stopOrder[dir]:
					s = self.stopWithTag(tag)
					if s:
						print "    " + s.tag + " -- " + s.name
     
    #
    #
    # BASIC METHODS   
    def __len__(self):
        if self.routeTag: return 1
        else: return 0
           
    #
    #    
    # ROUTE INFO RETRIEVAL 

    # initializer for an input that is explicitly a string   
    def initByRouteTag(self, tag):
        success = self.loadFromFile(tag)
        if not success:
            success = self.downloadRouteInfo(tag)
        if not success:
            raise Exception('Could not load Route info for route "%s" from file or download from NextBus.com' % tag)
            
            
    # get route info using NextBus API        
    def downloadRouteInfo(self, tag):
        if type(tag) == str:
            xmlData = sendCommand('routeConfig&a=sf-muni&r=%s' % tag)          
        else:
            xmlData = tag
            
        rte = xmlData.getElementsByTagName("route")

        rte = rte.item(0)
        self.routeTag = str(rte.getAttribute("tag"))
        self.routeName = str(rte.getAttribute("title"))
        
        dirs = xmlData.getElementsByTagName("direction")
        
        if len(dirs) == 0:
            raise Exception('Cannot find direction info')
        #if len(dirs) != 2:
        #    print 'Number of directions is not 2...'
           
        self.directionList = {} 
        self.directionTags = {}
        self.stopOrder = {}

        for dir in dirs:
            dirName = str(dir.getAttribute("name"))
            dirTag = str(dir.getAttribute("tag"))
            dirFullName = str(dir.getAttribute("title"))
            dirFullName.replace('&amp;', '&')
            #print dirName + ", " + dirTag + ", " + dirFullName
            self.directionList[dirName] = dirFullName
            self.directionTags[dirName] = dirTag
            
            stps = dir.getElementsByTagName("stop")
            slist = []
            for s in stps:
                slist.append(str(s.getAttribute('tag')))
            self.stopOrder[dirName] = slist
            

        # get all stop info    
        stps = rte.getElementsByTagName("stop")
        if len(stps) == 0:
            raise Exception('Cannot find stop info')
           
        # instantiate stop objects
        self.stops = []
        count = 0
        for s in stps:
#             print s.toxml()
#             print s.hasAttribute('title')
            if s.hasAttribute('title'):
                
                newStop = BusStop(s)
                newStop.routes.append(self.routeTag)
                direction = self.directionOfStop(newStop.tag)
                if isinstance(direction, list):
                    for d in direction: 
                        newStop.routeDirs.append(self.directionTags[d])
                else:
                    newStop.routeDirs.append(self.directionTags[direction])
                #newStop.show()
                
                if len(self.stops) > 0:
                    (flags,i) = newStop.compareStops(self.stops)
                    if not any(flags):
                        self.stops.append(newStop)
                else: 
                    self.stops.append(newStop)
                count += 1
        
        obstops = self.outboundStops()

        # make sure stops are in correct order
        #  this order is given by self.stopOrder, which is used in the inboundStops/outboundStops fcns
        self.stops = self.inboundStops()
        
        for s in obstops:
            self.stops.append(s)
            
        self.xml = xmlData
        
        return True
        
    
    # load cached route info        
    def loadFromFile(self, tag):
        return False
        
    
    #
    #
    # DIRECTIONS
    
    # the string corresponding to the inbound direction (usually 'Inbound')
    def inboundKey(self):
        dirs = self.directionTags.keys()
        for d in dirs:
            if 'in' in d.lower(): return d
        return []
        
    # the string corresponding to the outbound direction (usually 'Outbound')   
    def outboundKey(self):
        dirs = self.directionTags.keys()
        for d in dirs:
            if 'out' in d.lower(): return d
        return []        
    
    # the inbound tag used in URLs for the route + direction (i.e., 12_IB1 or 14X_OB)
    def inboundRouteTag(self):
        return self.directionTags[self.inboundKey()]
        
    # the outbound tag used in URLs for the route + direction (i.e., 12_IB1 or 14X_OB)
    def outboundRouteTag(self):
        return self.directionTags[self.outboundKey()]
        
    # the normalized 'Inbound'/'Outbound' string, which is a key for the directionList & directionTags dictionaries
    def directionKeyLike(self,str):
        isIn = False
        isOut = False
        if str.lower().find('in') == 0: isIn = True
        elif str.lower().find('out') == 0: isOut = True
        elif 'ib' in str.lower(): isIn = True
        elif 'ob' in str.lower(): isOut = True
        if (isIn and isOut) or ((not isIn) and (not isOut)): return None
        elif isIn: return self.inboundKey()
        elif isOut: return self.outboundKey()
        else: raise Exception('Truth table should not have reached this point.')
    
    
    #
    #
    # STOPS
    
    # an ordered list of tags for the inbound route    
    def inboundStopTags(self):
        k = self.inboundKey()
        if k: return self.stopOrder[k]
        else: return []
    
    # an ordered list of tags for the inbound route    
    def outboundStopTags(self):
        k = self.outboundKey()
        if k: return self.stopOrder[k]
        else: return []
    
    # an ordered list of stop objects for inbound route    
    def inboundStops(self):
        return self.stopsWithTags(self.inboundStopTags())
    
    # an ordered list of stop objects for outbound route 
    def outboundStops(self):
        a = self.outboundStopTags()
        b = self.stopsWithTags(a)
        return self.stopsWithTags(self.outboundStopTags())
        
    # return the key(s) for the directions the stop tag lies on
    def directionOfStop(self, tag):
        d = []
        if self.stopIsInbound(tag):
            d.append(self.inboundKey())
        if self.stopIsOutbound(tag):
            d.append(self.outboundKey())
        if len(d) == 1: d = d[0]
        elif len(d) > 1:
            warnings.warn('Stop ' + tag + ' is listed on multiple directions for route ' + self.routeTag)
        return d
    
    # if the input stop tag lies on the inbound route, return True        
    def stopIsInbound(self, tag):
        k = self.inboundKey()
        flag = False
        if k: flag = (tag in self.stopOrder[k])
        return flag
    
    # if the input stop tag lies on the outbound route, return True
    def stopIsOutbound(self, tag):  
        k = self.outboundKey()
        flag = False
        if k: flag = (tag in self.stopOrder[k])
        return flag   
    
    # positions (lat/lon) of inbound stops
    def inboundStopPositions(self):
        stops = self.inboundStops()
        lat = numpy.array([])
        lon = numpy.array([])
        tag = []
        for s in stops:
            lon = numpy.append(lon, s.longitude)
            lat = numpy.append(lat, s.latitude)
            tag.append(s.tag)
        return (lat,lon,tag)
    
    # positions (lat/lon) of outbound stops
    def outboundStopPositions(self):
        stops = self.outboundStops()
        lat = numpy.array([])
        lon = numpy.array([])
        tag = []
        for s in stops:
            lon = numpy.append(lon, s.longitude)
            lat = numpy.append(lat, s.latitude)
            tag.append(s.tag)
        return (lat,lon,tag)
    
    # returns an ordered list of stops according to the input tag list
    def stopsWithTags(self, tagList):
        stops = []
        for tag in tagList:
            s = self.stopWithTag(tag)
            if s: stops.append(s)
        return stops
        
    # return the stop with a tag that matches the input tag (if one exists)
    def stopWithTag(self, tag):
        for s in self.stops:
            if s.tag == tag:
                return s
        return None
            
    # get a stop by specifying "Folsom" and "16th"
    def stopsFromStreets(self, st1, st2, direction='None'):
        stops = []
        for st in self.stops:
            components = st.name.split('&')
            for c in components:
                c = c.strip()
                
            if len(components) < 2:
                if st1.lower() in components[0].lower():
                    stops.append(st)
            else:
                if st1.lower() in components[0].lower() and st2.lower() in components[0].lower():
                    stops.append(st)

        return stops
            
    # get a stop's tag by specifying cross streets
    def stopTagFromStreets(self, st1, st2):
        stops = self.stopsFromStreets(st1,st2)
        if stops:
            tags = []
            for s in stops:
                tags.append(s.tag)
            return tags
        else: return None
    
    # ("CLASS METHOD")
    # sort an argument (a list) with corresponding stop tags stopTags so that the
    #   argument order matches the order in the route's stopOrder variable
    def sortStopTags(self, stopTags, args=None):
        
        ins = []; outs = []
        
        # if no argument is provided, assume the user just wants stopTags sorted according
        #    to their order in stopOrder:
        if not args:
            args = stopTags
            
        # inputs must both be lists
        if not isinstance(stopTags, list): stopTags = [stopTags]
        if not isinstance(args, list): args = [args]
        
        if len(stopTags) != len(args):
            raise Exception('stop tag list must have same # of elements as the list to sort (2nd argument)')

        # get the inbound/outbound stop tags IN ORDER (guaranteed by xxxstopTags(), which pulls from stopOrder)
        inStops = self.inboundStopTags()
        outStops = self.outboundStopTags()
        
        stopsAndArgs = zip(stopTags, args)
        
        # find the index where each tag occurs in in/outStops:
        inIndex = []; outIndex = []
        inArgs = []; outArgs = []
        for line in stopsAndArgs:
            t = line[0]				# the stop tag
            a = line[1]				# the argument
            try:
                inIndex.append(inStops.index(t))
                inArgs.append(a)
                
            except ValueError:		# this means that the tag t was not found in the list; no need to do anything except try the outbound list
                try:
                    outIndex.append(outStops.index(t))
                    outArgs.append(a)
                except ValueError:  # no need to do anything
                    None		
                except:             # a different kind of error
                    raise Exception('Error in finding tag "%s" in stop order list' % t)
        
        # order arg according to the indices found above
        if inIndex:
           indicesAndArgs = zip(inIndex, inArgs)
           indicesAndArgs.sort()
           (inIndex, inArgs) = zip(*indicesAndArgs)
           inIndex = list(inIndex)
           inArgs = list(inArgs)

        if outIndex:
           indicesAndArgs = zip(outIndex, outArgs)
           indicesAndArgs.sort()
           outIndex, outArgs = zip(*indicesAndArgs)
           outIndex = list(outIndex)
           outArgs = list(outArgs)
           
        # return a single list or tuple, depending on whether both inbound & outbound 
        #   stop tags were present
        if inArgs and outArgs: (inArgs, outArgs)
        elif inArgs: return inArgs
        elif outArgs: return outArgs
        else: return []
            
        
    # ("CLASS METHOD")
    # sort an argument (a list) with corresponding stops (each with a tag) so that the
    #   argument order matches the order in the route's stopOrder variable    
    def sortStops(self, stopList, arg):
        return self.sortStopTags(BusStop().getTags(stopList), arg)
        
    #    
    #
    # PREDICTIONS        
    
    # get all predictions for one direction:
    def getPredictionsForStopTags(self, stopTagList):
        return getMultiStopPrediction(self.routeTag, stopTagList)
        
    # prediction for a list of stop objects
    def getPredictionsForStops(self, stopList):
        tags = []
        if type(stopList) == str: stopList = [stopList]
        for s in stopList: tags.append(s.tag)
        return getMultiStopPrediction(self.routeTag, tags)
        
    # prediction for a stop index
    def getPredictionForStopIndex(self, stopIndexList):
        return self.getPredictionsForStopTags(self.stops[stopIndexList])
        
    # all predictions for a given direction
    def getPredictionsForDirection(self, directionStr='Inbound'):
        stopTags = self.stopOrder[self.directionKeyLike(directionStr)]
        return getMultiStopPrediction(self.routeTag, stopTags)
        
    # all predictions for a given direction, returned in the form of a PredictionList object
    def getPredictionListForDirection(self, directionStr='Inbound'):
        stopTags = self.stopOrder[self.directionKeyLike(directionStr)]
        preds = getMultiStopPrediction(self.routeTag, stopTags)
        return(PredictionList(preds))
    
    
    #
    # Display on Google maps
    def getGoogleMap(self, direction='Inbound', opt=None):
        arg = direction
        direction = self.directionKeyLike(direction)
        if direction == self.inboundKey():
            stops = self.inboundStops()
            color = 'red'
        elif direction == self.outboundKey():
           stops = self.outboundStops()
           color = 'blue'
        else:
            warnings.warn('BusRoute.getGoogleMapUrl:: Input direction "%s" is not recognized.' % arg)
            return
        
        if opt: option = opt
        else: option = None
        
        positions = []
        for s in stops:
            positions.append(s.getPosition())	# position is a list of coordinate tuples (x,y)
        url = nmvis.gmapStops(positions, c=color, opt=option)
        
        nmvis.copyStringToClipboard(url)
        return url
        
        
        
              
#
# BusStop
#    
class BusStop:

    # tag, name, latitude, longitude, stopID
    
    #
    # INITIALIZATION
    
    def setup(self):
        self.routes = []
        self.routeDirs = []
        self.dbp = StopDatabaseParser()
        self.tag = None
               
    def __init__(self, someStopInfo=None):
        self.setup()

        if someStopInfo == None:   # probably using the instance for its "Class methods"
            return
        elif isinstance(someStopInfo, str):
            if len(someStopInfo) >= 6:
                try:
                    self.setFromDatabaseLine(someStopInfo)
                except:
                    self.setFromDatabaseWithTag(someStopInfo)
            else:
                self.setFromDatabaseWithTag(someStopInfo)
                    
        elif isinstance(someStopInfo, int):
            self.setFromDatabaseWithTag(str(someStopInfo))

        else:
            self.setByXML(someStopInfo)
        
    
    #
    # BASIC METHODS
    def __len__(self):
        if self.tag: return 1
        else: return 0
        
    #
    # STOP INFO RETRIEVAL
    
    # parse a line from the database and populate stop fields
    def setFromDatabaseLine(self, txt):

        dbp = self.dbp
        separator = dbp.separator
        assigner = dbp.assigner
        
        # if txt is empty, exit
        if not txt: return False
        
        # if txt is a comment line, exit
        if txt[0] == dbp.commentTag: return False
        
        data = txt.split(separator)
        if data:

            for pair in data[1:]:
                kv = pair.split(assigner)

                if len(kv) != 2:
                    raise Exception('Stop Database tag-value syntax is not preserved in line:\n%s' % txt)
                key = kv[0]
                val = kv[1]
                if key == dbp.stopTag: self.tag = val
                elif key == dbp.nameTag: self.name = val
                elif key == dbp.latTag: self.latitude = float(val)
                elif key == dbp.lonTag: self.longitude = float(val)
                elif key == dbp.idTag: self.stopID = int(val)
                elif key == dbp.routesTag:
                    routes = val.split(dbp.separator_2)
                    for r in routes:
                        self.routes.append(r.strip('\n'))
                elif key == dbp.routeDirTag:
                    directions = val.split(dbp.separator_2)
                    for d in directions:
                        self.routeDirs.append(d.strip('\n'))
                else:
                    warnings.warn('Unrecognized tag in Stop Database tag/value pair:\n  %s' % pair)
                    
        return True
        
        
    # load the stop info from the database
    def setFromDatabaseWithTag(self, tag):
    
        # get database parser object (more of a struct, really)
        dbp = StopDatabaseParser()
        separator = dbp.separator
        assigner = dbp.assigner
        
        fid = open(dbp.databaseFilename, 'r')
        
        txt = fid.readline()
        data = txt.split(dbp.separator)
        
        while txt and data[0] != tag:
            txt = fid.readline()
            data = txt.split(separator)
            
        if fid and txt:
            self.setFromDatabaseLine(txt)

        fid.close()
             
        
    # this should be the designated initializer
    def setByXML(self, xmlData):
        if not xmlData.hasAttribute('tag'): raise Exception('XML data does not have tag property')
        else: self.tag = str(xmlData.getAttribute('tag'))
        if not xmlData.hasAttribute('title'): raise Exception('XML data does not have title property')
        else: 
            title = str(xmlData.getAttribute('title'))
            self.name = title.replace('&amp;', '&')
        if not xmlData.hasAttribute('lat'): raise Exception('XML data does not have lat property')
        else: self.latitude = float(xmlData.getAttribute('lat'))
        if not xmlData.hasAttribute('lon'): raise Exception('XML data does not have lon property')
        else: self.longitude = float(xmlData.getAttribute('lon'))
        if not xmlData.hasAttribute('stopId'): raise Exception('XML data does not have stopId property')
        else: 
            try: self.stopID = int(xmlData.getAttribute('stopId'))
            except: self.stopID = xmlData.getAttribute('stopId')
        self.xml = xmlData    
    
    
    # display to command line    
    def show(self):
        print 'STOP ' + self.tag
        print '  Tag: ' + self.tag + '\n  Name: ' + self.name + '\n  Latitude: ' + \
            str(self.latitude) + '\n  Longitude: ' + str(self.longitude) + \
            '\n  Stop ID: ' + str(self.stopID)
        if self.routes:
            rstr = ''
            for r in self.routes: rstr += (r + ', ')
            if len(rstr) > 0: rstr = rstr[:-2]
            print '  Routes: ' + rstr
        if self.routeDirs:
            dstr = ''
            for d in self.routeDirs: dstr += (d + ', ')
            if len(dstr) > 0: dstr = dstr[:-2]
            print '  Route/direction tags: ' + dstr

    
    #
    # OTHER METHODS
    
    # compare this stop to a list of other stops, returning an array with True where they are identical (deep copies)
    def compareStops(self, someStops):
        i = v = []
        index = 0
        for aStop in someStops:
            flag = True
            flag *= (self.tag == aStop.tag)
            flag *= (self.name == aStop.name)
            flag *= (self.latitude == aStop.latitude)
            flag *= (self.longitude == aStop.longitude)
            flag *= (self.stopID == aStop.stopID)
            i.append(flag)
            if flag: v.append(index)
            index += 1
        return (numpy.array(i), numpy.array(v))
            
           
    #
    # "ACCESSORS"
    
    # add a verified route to this stop
    def addRoute(self, routeTag):
        success = False
        if (NextBusClient().isValidRouteTag(routeTag)):
            self.routes.append(routeTag)
            success = True
        return success    
    
    # get the latitude, longitude as a tuple
    def getPosition(self):
        return (self.latitude, self.longitude)
        
    # return a prediction for the next bus on the provided route    
    def getNextBusOnRoute(self, arg):
        return getNextBusOnRoute(arg, None)
        
    def getNextBusOnRoute(self, arg1, arg2):
        # if routeTag not in self.routes:
        #     raise Exception('Route: ' + routeTag + ' is not part of this stop')
        #     return None
        # return None
        
        if type(arg1) == str:
            tag = arg1
        else:
            try:
                tag = arg1.directionTags[arg2]
            except:
                None

        xmlData = sendCommand('predictions&a=sf-muni&r=%s&s=%s' % (tag, self.tag) )
        if xmlData.getElementsByTagName("Error"):
            shortRouteTag = tag.split('_')
            shortRouteTag = shortRouteTag[0]
            xmlData = sendCommand('predictionsForMultiStops&a=sf-muni&stops=%s|%s' % (shortRouteTag, self.tag) )
        
        if xmlData.getElementsByTagName("Error"):
            raise Exception('Error in getting prediction data.')
            
        pred = xmlData.getElementsByTagName("prediction")
        
        sec = []
        min = []
        currentTime = datetime.now()
        for p in pred:
            s = p.getAttribute("seconds")
            m = p.getAttribute("minutes")
            sec.append(s)
            min.append(m)
            
        return (min, sec, currentTime)
     
     
    #
    # "CLASS METHODS"
    
    # return a list of tags for the input list of stops
    def getTags(self, stopList):
        if isinstance(stopList, list):
            tags = []
            for s in stopList:
                tags.append(s.tag)
        else:
            tags = [stopList.tag]
        return tags
           
    # return a list of positions (lat-lon tuples) for a list of stops
    def getPositions(self, stopList):
        if isinstance(stopList, list):
            p = []
            for s in stopList:
                p.append(s.getPosition())
        else:
            p = [stopList.getPosition()]

        return p
    
    
    
    
### some other functions
  
# the official format of the string used in the stop database (a text file)
def stopDatabaseEntryString(stop, parser=None, lineCount=0):
    if not parser:
        parser = StopDatabaseParser()
    sep = parser.separator
    assign = parser.assigner
    routeSep = parser.separator_2
    
    newStr = '%i' % lineCount + sep + \
                 parser.stopTag + assign + '%s' % stop.tag + sep + \
                 parser.nameTag + assign + '%s' % stop.name + sep + \
                 parser.latTag + assign + '%f' % stop.latitude + sep + \
                 parser.lonTag + assign + '%f' % stop.longitude + sep + \
                 parser.idTag + assign + '%i' % stop.stopID + sep
                 
    # route tags
    rteStr = parser.routesTag + assign
    for rs in stop.routes:
        rteStr += '%s' % rs + routeSep
    if len(stop.routes) > 0: rteStr = rteStr[:-len(routeSep)]	# get rid of trailing routeSep
    newStr += rteStr
    newStr += sep
    
    # route direction tags
    dirStr = parser.routeDirTag + assign
    for ds in stop.routeDirs:
        dirStr += '%s' % ds + routeSep
    if len(stop.routeDirs) > 0: dirStr = dirStr[:-len(routeSep)]	# get rid of trailing routeSep
    newStr += dirStr
    
    return newStr
    
    
# Get all the stops from the NextBus website and write them to a txt database
def makeStopRecord(redundantStopList=None):
    from datetime import datetime
    import os
    from copy import copy
    
    dbp = StopDatabaseParser()
    filename = dbp.databaseFilename
    sep = dbp.separator
    assign = dbp.assigner
    routeSep = dbp.separator_2
	
	# if a non-curated list has not been provided, create it (and save to file)	
    if not redundantStopList:
				
		print 'Requesting routes...'
		data = sendCommand('routeList&a=sf-muni')
		routes = data.getElementsByTagName('route')
	
		tags = []
		for r in routes:
			tags.append(str(r.getAttribute("tag")))
		print '--> done with route request.\n%i routes found.\n' % len(tags)
		
		stopTags = []
		stopList = []
		routesByStop = []
		routes = []
		redundantStopList = []	# stops may be listed multiple times b/c they appear on multiple routes
		
		# get info for each route (and extract stop info)
		print 'Requesting stops...'
		
		(filename2,ext) = os.path.splitext(filename)
		filename2 = filename2 + '_TEMP' + ext
		fid2 = open(filename2, 'w')
		fid2.write('# line | stopTag | name | routeTags | routeDirTags | latitude | longitude | stopID')
		count = 0
		
		for t in tags:
			
			rte = BusRoute(t)
			print '\n  Route: ' + t
			routes.append(rte)
			
			for s in rte.stops:
			    redundantStopList.append(s)
			    
			    # write to temporary file: create string
			    entry = stopDatabaseEntryString(s, lineCount=count, parser=dbp)
			    
			    # write to file
			    fid2.write(entry + '\n')
			    count += 1
			    print entry
			
			print '  --> done.'
			print '  (waiting)'        
			time.sleep(MIN_TIME_BETWEEN_REQUESTS)
		
		print '--> done reading stops.'
		
	# end stopList generation loop.
    
    if not redundantStopList:      
        return False
    
    # organize stops into a non-redundant list
    stopList = []
    stopTags = []
    
    for stop in redundantStopList:
        
        # see if the stop has already appeared
        try:
            idx = stopTags.index(stop.tag)
        except ValueError:	# if a stop has not been encountered before (this is the usual case), add it to the list
            stopList.append(copy(stop))
            stopTags.append(stop.tag)
            idx = len(stopList) - 1		# the index of the current (last) stop
        
        # make sure the route associated with the current stop is listed in the non-redundant list's routes:
        if len(stop.routes) != 1:
            stop.show()
            print('Stop %s should only have one route.' % stop.tag)
        else:
            if stop.routes[0] not in stopList[idx].routes:
                stopList[idx].routes.append(stop.routes[0])
                if stop.routeDirs[0] not in stopList[idx].routeDirs:
                    stopList[idx].routeDirs.append(stop.routeDirs[0])
        
    # stopList is now completed. Organize by tag (if possible)
    try:
        numericTag = list(numpy.array(stopTags))
        stopList = sorted(stopList, key = lambda stop: stop.tag)
    except:
        print "Cannot order stops by tag becuase non-numeric tags were encountered."
            
    # write all stop info to file    
    print '\nWriting stops to database: ' + filename
    
    fid = open(filename, 'w')
    lineCount = 0 
    
    # header info
    fid.write(dbp.commentTag + ' NextMuni Stop Database\n')
    fid.write(dbp.commentTag + ' File: ' + filename + '\n')
    fid.write(dbp.commentTag + ' Last updated: ' + str(datetime.now())+ '\n')
    fid.write(dbp.commentTag + ' line | stopTag | name | latitude | longitude | stopID | routes | directions\n')
    fid.write(dbp.commentTag + '\n')
    percentDone = 0.0
    nStops = len(stopList)
    
    for s in stopList:
        
        entry = stopDatabaseEntryString(s, lineCount=lineCount, parser=dbp)
        if entry and entry[-1] == '\n': entry = entry[:-1]
        lineCount += 1

        #print '  Line ' + str(lineCount) + ': ' + entry
        if len(s.routes) > 1:
            print s.routes, s.routeDirs
        # write stop info to file
        fid.write(entry + '\n')
        
        # show update on screen
        updateOn = 5. / 100.
        if numpy.ceil(float(lineCount) / float(nStops) * 1./updateOn) > numpy.ceil(percentDone * 1./updateOn):
            print '\n*** %i percent complete.\n' % (round(float(lineCount) / float(nStops) * 1./updateOn) * updateOn * 100.0)
        percentDone = float(lineCount) / float(nStops)
        
    
    print '--> done writing to file.'
    
    fid.close()
    return True
        
    
# turn a string in the format of the TEMP stop list file into a stop object 
# Note that this format is NOT the same as used in the real database file 
# (it lacks tags, i.e., "stopTag=3312; routes=J,14,F; ...")
def stopFromEntryString(entry, parser=None):
    if not parser:
        parser = StopDatabaseParser()
    items = entry.split(parser.separator)
    if len(items) > 7:
        items = items[1:]	# first entity is a line number
    stop = BusStop()
    stop.tag = items[0].strip()
    stop.name = items[1].strip()
    stop.routes = [items[2].strip()]
    stop.routeDirs = [items[3].strip()]
    stop.latitude = float(items[4])
    stop.longitude = float(items[5])
    stop.stopID = int(items[6])
    return stop
    
    
# get a stoplist from the temporary file (which does not have full route info for stops, and may list redundant stops)
def stopListFromFile(filename):
    parser = StopDatabaseParser()
    fr = open(filename,'r')
    
    stopList = []
    lineCount = 0 

    for entry in fr:
        if entry:
            if entry[0] == '#':
                None	# ignore; comment
            else:
                stop = BusStop()	# create a new instance
                stop.setFromDatabaseLine(entry)
                stopList.append(stop)
        else:
            print 'Could not parse line %i:\n  %s' % (lineCount, entry)

        lineCount += 1
        
    return stopList
            
    
def standardizeDatabase(filename):
    
    import os
    
    fr = open(filename, 'r')
    (filename2,ext) = os.path.splitext(filename)
    filename2 = filename2 + '_standard' + ext
    
    fw = open(filename2, 'w')
    
    parser = StopDatabaseParser()
    tok = parser.routeDirTag
    for entry in fr:
        parts = entry.split(tok)
        newEntry = entry
        newRouteDirs = ''
        newLabel = ''
        if len(parts) > 1:
            newEntry = parts[0]
            routeDirs = (parts[1].strip(parser.assigner + '\n')).split(parser.separator_2)
            for r in routeDirs:
                rData = r.split('_')
                routeTag = rData[0]
                label = rData[1:]
                
                newLabel = ''
                if 'IB' in label or 'ib' in label or any(['ib' in x.lower() for x in label]):
                    newLabel = 'IB'
                if 'OB' in label or 'ob' in label or any(['ob' in x.lower() for x in label]):
                    newLabel = 'OB'
                
                if not newLabel:
                    print('Could not find IB/OB in direction string: %s' % r)
                    newLabel = ''
                
                newRouteDirs += routeTag + '_' + newLabel + parser.separator_2
            
            if len(newRouteDirs) > 0:
                newRouteDirs = newRouteDirs[:-len(parser.separator_2)]
            newEntry += (tok + parser.assigner + newRouteDirs)
    
        if newLabel:
            fw.write(newEntry + '\n')
    
    fw.close()
    fr.close()            
        