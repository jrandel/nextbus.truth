# NMDATA
#  Responsible for loading, reshaping, and filtering NextMuni predictions recorded
#  by the nmtracker.py module.

# Some constants
TIME_FMT = '%Y-%m-%d %H:%M:%S'

filenameBase = '/users/jason/documents/python work/PredictionDatabaseRte'
filenameExt = '.dat'
sep = ';'

import os
import nextmunipy as nm
import numpy
MISSING_VALUE = numpy.nan
FORCE_POSITION_FROM_DATABASE = True

# ----------------------------------------------------------------------------------------
# ACCESSING THE DATA
# ----------------------------------------------------------------------------------------

# database files have the format: PredictionDatabaseRte12_20120515_143341.dat
# this function returns the most recent database file starting with, e.g., PredictionDatabaseRte12
def findFileStartingWith(fn):
   
    import os
   
    prefix = os.path.basename(fn)
    folder = os.path.dirname(fn)
    allFiles = os.listdir(folder)
    matches = []
   
    for f in allFiles:
        if ( (prefix + '_') in f or (prefix + '.') in f ) and 'OLD' not in f:
            matches.append(f)
    if len(matches) < 1:
        filename = None
    elif len(matches) == 1:
        filename = matches[0]
    else:	# sort by date, return the most recent
        from datetime import datetime
        filename = matches[0]
        try:
            (filebase,ext) = os.path.splitext(filename)
            parts = filebase.split('_')	# filename has format: PredictionDatabaseRte12_20120515_143341.dat
            d1 = parts[1]
            t1 = parts[2]
        except IndexError:
            d1 = 0;
            t1 = 0;
            
        for m in matches:
            (filebase,ext) = os.path.splitext(m)
            parts = filebase.split('_')      # filename has format: PredictionDatabaseRte12_20120515_143341.dat
            try:
                d2 = parts[1]
                t2 = parts[2]
            except IndexError:
                d2 = 0;
                t2 = 0;
                
            if int(d2) == int(d1) and int(t2) > int(t1):
                filename = m
                d1 = d2
                t1 = t2
            elif int(d2) > int(d1):
                filename = m
                d1 = d2
                t1 = t2
    
    mostRecent = os.path.normpath(folder + '/' + filename)
    return (matches, mostRecent)
        
  
# a class for sorting data from prediction database
class PredData:
#     def __init__(self,route,stop,vehicle,direction,startTime,endTime,currentTime,p,w,delta,lat=None,lon=None):
#         self.parser = nm.StopDatabaseParser()
#         self.count = len(route)
#         if not lat: lat = [None] * self.count
#         if not lon: lon = [None] * self.count
#         self.data = []
#         for i in range(len(route)):
#             self.data.append( (route[i],stop[i].strip(),vehicle[i],direction[i].strip(), \
#                     startTime[i].strip(),endTime[i].strip(),currentTime[i].strip(), \
#                     p[i],w[i],delta[i],lat[i],lon[i],w[i]-p[i]) )
    def __init__(self, allData=None, arg='all'):
        
        # initialize and empty instance
        self.data = []
        self.count = 0
        if not allData:
            return
        # initialize with a list of route tags
        elif type(allData) == str:
            self.initWithRoute(allData, arg)
            return
            
        self.parser = nm.StopDatabaseParser()
        route = allData[self.parser.routeIndex()]
        stop = allData[self.parser.stopIndex()]
        vehicle = allData[self.parser.vehicleIndex()]
        direction = allData[self.parser.directionIndex()]
        startTime = allData[self.parser.startTimeIndex()]
        endTime = allData[self.parser.endTimeIndex()]
        currentTime = allData[self.parser.currentTimeIndex()]
        prediction = allData[self.parser.predictionIndex()]
        wait = allData[self.parser.waitIndex()]
        delta = allData[self.parser.uncertaintyIndex()]
        latitude = allData[self.parser.latIndex()]
        longitude = allData[self.parser.lonIndex()]
        delay = numpy.array(wait) - numpy.array(prediction)
                
        self.count = len(route)
        if not latitude: latitude = [None] * self.count
        if not longitude: longitude = [None] * self.count
        self.data = []
        for i in range(len(route)):
            self.data.append( (route[i],stop[i].strip(),vehicle[i],direction[i].strip(), \
                    startTime[i].strip(),endTime[i].strip(),currentTime[i].strip(), \
                    prediction[i],wait[i],delta[i],latitude[i],longitude[i],wait[i]-prediction[i]) )

                    
    # initialize the data list by loading data from a list of route tags (which indicate a list of files)
    def initWithRoute(self, routeTags, arg):
    
        if type(routeTags) == str: routeTags = [routeTags]
        for rt in routeTags:
            (filenames, recentFile) = findFileStartingWith(filenameBase + rt)
            if (arg.lower() in ['last','recent']):
                filenames = [recentFile]
            for fn in filenames:
                newData = loadData(fn)
                self.appendData(newData)
                    
                    
    # returns a dictionary that can be used like a struct to get data components
    def getDict(self, theData=None):
        if not theData:
            theData = self.data
        dataDict = {'routes': self.routes(), 'stops': self.stops(), 'vehicles': self.vehicles(), 'directions': self.directions(), \
                         'startTimes': self.startTimes(), 'endTimes': self.endTimes(), 'currentTimes': self.currentTimes(), \
                         'predictions': self.predictions(), 'waits':self.waits(), 'uncertainty': self.uncertainties(), \
                         'latitudes': self.latitudes(), 'longitudes': self.longitudes(), 'delays': self.delays()}
        return dataDict
        
    
    def copyContainingData(self, data):
        self.data = data
        return self
        
    # append another PredData object's data, or append data (in the same list-of-tuples format) to this one's data
    def appendData(self, newData):
        if type(newData) == tuple:
            newPredData = PredData(newData)
        else: 
            newPredData = newData
        self.count += newPredData.count
        self.data += newPredData.data
        
        
    def dataForVarEqualTo(self, strOut, strVar, val):
        theDict = self.getDict()
        out = theDict[strOut]
        var = theDict[strVar]
        #indices = []
        outList = []
        for (o,v) in zip(out,var):
            if v == val: outList.append(o)
        return outList
    
    # a special case of the above method    
    def delaysForPredEqualTo(self, targetPred):
        delays = self.delays()
        predictions = self.predictions()
        theDelays = []
        for (d,p) in zip(delays, predictions):
            if p == targetPred: theDelays.append(d)
        return theDelays
        #return [d for (d,p) in zip(delays,predictions) if p == targetPred]
    
    
    # some idiosyncratic getters for certain data: 
    def currentTimesInSeconds(self):
        from datetime import datetime, timedelta
        
        cts = self.currentTimes()
        t0 = datetime.strptime(min(cts), TIME_FMT)
        t0 = t0.strftime(TIME_FMT.split()[0]) + ' 00:00:00'
        t0 = datetime.strptime(t0, TIME_FMT)

#         t = []
#         for ct in cts:
#             t.append((datetime.strptime(ct,TIME_FMT) - t0).total_seconds())
#         return t
        return [(datetime.strptime(ct,TIME_FMT) - t0).total_seconds()]
    
    def dayOfWeekNumeric(self):
        from datetime import datetime
        return [datetime.strptime(ct,TIME_FMT).isoweekday() for ct in cts]
            
            
            
    # sets the output type for list getters (which as constructed return tuples)
    def formatOutput(self, out):
        return (list(out))    

	# list getters
    def routes(self,indices=None):
        A = self.getLists()
        a = A[self.parser.routeIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def stops(self,indices=None):
        A = self.getLists()
        a = A[self.parser.stopIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def vehicles(self,indices=None):
        A = self.getLists()
        a = A[self.parser.vehicleIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def directions(self,indices=None):
        A = self.getLists()
        a = A[self.parser.dirIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def startTimes(self,indices=None):
        A = self.getLists()
        a = A[self.parser.startTimeIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def endTimes(self,indices=None):
        A = self.getLists()
        a = A[self.parser.endTimeIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def currentTimes(self,indices=None):
        A = self.getLists()
        a = A[self.parser.currentTimeIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def predictions(self,indices=None):
        A = self.getLists()
        a = A[self.parser.predIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def waits(self,indices=None):
        A = self.getLists()
        a = A[self.parser.waitIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def delays(self,indices=None):
        p = numpy.array(self.predictions())
        w = numpy.array(self.waits())
        d = list(w - p)
        if indices:
            r = d; d = []
            for i in indices: d.append(r[i])
        return d
    def uncertainties(self,indices=None):
        A = self.getLists()
        a = A[self.parser.uncertaintyIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def latitudes(self,indices=None):
        A = self.getLists()
        a = A[self.parser.latIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))
    def longitudes(self,indices=None):
        A = self.getLists()
        a = A[self.parser.lonIndex()]
        if indices:
            r = a; a = []
            for i in indices: a.append(r[i])
        return(self.formatOutput(a))    
    # a utility for the above getters
    def getLists(self):
        return zip(*self.data)    
    
    def sortedBy(self, s):
        if s.lower() == 'route': sortedData = sorted(self.data, key=lambda line: line[self.parser.routeIndex()])
        if s.lower() == 'stop': sortedData = sorted(self.data, key=lambda line: line[self.parser.stopIndex()])
        if s.lower() == 'vehicle': sortedData = sorted(self.data, key=lambda line: line[self.parser.vehicleIndex()])
        if s.lower() == 'direction': sortedData = sorted(self.data, key=lambda line: line[self.parser.dirIndex()])
        if s.lower() == 'startTime': sortedData = sorted(self.data, key=lambda line: line[self.parser.startTimeIndex()])
        if s.lower() == 'endTime': sortedData = sorted(self.data, key=lambda line: line[self.parser.endTimeIndex()])
        if s.lower() == 'currentTime': sortedData = sorted(self.data, key=lambda line: line[self.parser.currentTimeIndex()])
        if s.lower() == 'predictedWait': sortedData = sorted(self.data, key=lambda line: line[self.parser.predIndex()])
        if s.lower() == 'wait': sortedData = sorted(self.data, key=lambda line: line[self.parser.wiatIndex()])
        if s.lower() == 'delay': sortedData = sorted(self.data, key=lambda line: line[-1])
        if s.lower() == 'latitude': sortedData = sorted(self.data, key=lambda line: line[self.parser.latIndex()])
        if s.lower() == 'uncertiainty': sortedData = sorted(self.data, key=lambda line: line[self.parser.deltaIndex()])
        if s.lower() == 'longitude': sortedData = sorted(self.data, key=lambda line: line[self.parser.lonIndex()])
        return self.copyContainingData(sortedData)


# Load all of the data saved to the specified file (filename)
def loadData(fn='14',opt='recent'):

    if not fn: fn = '14'
        
    if len(fn) < 10:
        (filenames, filename) = findFileStartingWith(filenameBase + fn)
    else:
        filename = fn
    print filename
    fid = open(filename, 'r')
    
    # get data indices (in line)
    parser = nm.StopDatabaseParser()
    iroute = parser.routeIndex(); istop = parser.stopIndex(); ivehicle = parser.vehicleIndex()
    idirection = parser.directionIndex(); istarttime = parser.startTimeIndex(); iendtime = parser.endTimeIndex()
    icurrenttime = parser.currentTimeIndex(); ipred = parser.predIndex(); iwait = parser.waitIndex()
    idelta = parser.uncertaintyIndex(); ilat = parser.latitudeIndex(); ilon = parser.longitudeIndex()
    
    # make empty lists
    route=[]; stop=[]; vehicle=[]; direction=[]; startTime=[]; stopTime=[]; endTime=[];
    currentTime=[]; p=[]; w=[]; delta=[]; lat=[]; lon=[];
    
    txt = fid.readline()
    
    while txt:
        if len(txt) > 0 and not txt[0] == '#':
            data = txt.split(sep)
           
            # remove endline from end of line
            if '\n' in data[-1]: data.pop()
            
            try:
                route.append(data[iroute]);
                stop.append((data[istop])); 
                vehicle.append(int(data[ivehicle])); 
                direction.append((data[idirection])); 
                startTime.append(data[istarttime]); 
                endTime.append(data[iendtime]);
                currentTime.append(data[icurrenttime]); 
                p.append(float(data[ipred])); 
                w.append(float(data[iwait])); 
                delta.append(int(data[idelta]))
                try:
                    lat.append(float(data[ilat]))
                    lon.append(float(data[ilon]))
                except IndexError:
                    lat.append(MISSING_VALUE)
                    lon.append(MISSING_VALUE)
            except IndexError:
                print "Line with less than 10 entries reached: %s" % txt
                
        txt = fid.readline()
        
    return (route,stop,vehicle,direction,startTime,endTime,currentTime,p,w,delta,lat,lon)



def loadWaitTimes(fn=None):
    (route,stop,vehicle,direction,startTime,endTime,currentTime,p,w,delta,lat,lon) = loadData(fn)
    return (p,w)
    

# this returns the delay time for a particular data file, along with stop position (lat/lon)
def getDelays(fileName,targetPredictionTimes=None,targetDirection='IB'):
    
    if not targetDirection: targetDirection = 'IB'
    
    folder = os.path.dirname(fileName)
    fileBase = os.path.basename(fileName)
    if not folder:
        fileName = os.path.normpath('/users/jason/documents/python work/' + fileBase)
        
    #(route,stop,vehicle,direction,startTime,endTime,currentTime,p,w,delta,lat,lon) = loadData(fileName)
    data = loadData(fileName)
    route = data[0]
    allRoutes = list(numpy.unique(route))
    if len(allRoutes) > 1:
        targetRoute = allRoutes[0]
        for r in allRoutes:
            if allRoutes.count(r) > allRoutes.count(targetRoute):
                targetRoute = r
        warnings.warn("Multiple routes found in file; using the most frequent one (%s)" % targetRoute)
    else:
        targetRoute = route[0]
        
    rte = nm.BusRoute(targetRoute)
    
    # separate the data columns
    dbp = nm.StopDatabaseParser()
    stopTag = data[dbp.stopIndex()]
    dirTag = data[dbp.dirIndex()]
    pw = data[dbp.predWaitIndex()]
    rw = data[dbp.realWaitIndex()]
    lat = data[dbp.latIndex()]
    lon = data[dbp.lonIndex()]
    if lat and lon:
        LAT_LON_RECORDED = True
    else:
        LAT_LON_RECORDED = False
    if FORCE_POSITION_FROM_DATABASE: LAT_LON_RECORDED = False

    sv = []; pv = []; rv = []
    waitTime = {}
    predTime = {}
    latLonAtStop = {}
    # put targetPredictionTimes in correct (list) format
    if not targetPredictionTimes:
        targetPredictionTimes = range(0,60)
        
    if type(targetPredictionTimes) == int or type(targetPredictionTimes) == float:
        targetPredictionTimes = [targetPredictionTimes]
        
    # get the wait time at each stop for the predicted times
    for i in range(len(pw)):
        if pw[i] in targetPredictionTimes and targetDirection in dirTag[i].strip():
       
            st = stopTag[i].strip()
            if waitTime.has_key(st):
                waitTime[st] += [rw[i]]
                predTime[st] += [pw[i]]
            else:
                waitTime[st] = [rw[i]]
                predTime[st] = [pw[i]]
                if LAT_LON_RECORDED:
                    latLonAtStop[st] = (lat[i],lon[i])
                else:
                    latLon = rte.stopWithTag(st).getPosition()
                    if len(latLon) != 2:
                        raise Exception('Could not determine position of stop %s' % st)
                    latLonAtStop[st] = latLon

    stops = waitTime.keys()
    latAtStop = []
    lonAtStop = []
    wait = []; delay = []; stopTags = []; npts = []
    for s in stops:
        waits = numpy.array(waitTime[s])
        preds = numpy.array(predTime[s])
        d = waits - predTime[s]
        indices = d < predTime[s];		# threshold; delay must be less than predicted time
        
        d = d[indices]
        waits = waits[indices]
        wait += [numpy.mean(waits)]
        delay += [numpy.mean(d)]
        #wait += [numpy.mean(waitTime[s])]
        #delay += [numpy.mean(waitTime[s]) - numpy.mean(predTime[s])]
        stopTags.append(s)
        #npts.append(len(waitTime[s]))
        npts.append(len(waits))
        latAtStop.append(latLonAtStop[s][0])
        lonAtStop.append(latLonAtStop[s][1])
    
    return (delay, latAtStop, lonAtStop, stopTags, npts)
 
    
# ----------------------------------------------------------------------------------------
# OUTPUTTING THE DATA
# ----------------------------------------------------------------------------------------
# def showDelayByStop(fn=None):
#     import numpy as np
#     (route,stop,vehicle,direction,startTime,endTime,currentTime,p,w,delta) = loadData(fn)
#     
#     routeTag = np.unique(route)
#     if 
#     for s in stop:
        