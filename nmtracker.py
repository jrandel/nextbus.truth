# NMTRACKER.PY
#    Contains class definitions for dynamic prediction timing.
#    StopController:  Updates prediction times at a single stop (using nextmunipy.getMultiStopPrediction)
#                     Writes predictions to file once the actual wait time has been determined
#
#    TrackerControlelr:  Manages multiple StopController for a single (or multiple) routes/directions.
#                        Synchronizes the updating of the StopControllers (and the timing intervals)
# Output Format:
# routeTag, stopTag, vehicle, directionTag, startTime, endTime, currentTime, predictedWait, actualWait, waitUncertainty,

import nextmunipy as nm
import matplotlib as mat
from datetime import datetime, timedelta
import time
import numpy
import warnings
import os, csv

WAIT_TIME = 60.0
TIME_TO_RUN = 60 * 60 * 2
MINIMUM_INTERVAL = 30
MAX_STOPS_PER_REQUEST = 100
APPEND_DATE = True

UNITS = 'minutes'
DATABASE_FILENAME_BASE = '/users/jason/documents/python work/PredictionDatabaseRte'
DATABASE_FILE_EXT = 'dat'
VERBOSE = True
PREDICTION_TIME_THRESHOLD = 1.0
MISSING_VALUE = numpy.NaN

#
#
# STOPCONTROLLER CLASS        
#

class StopController:       
    '''
    Returns an object that sends requests to nextbus.com for the purpose of retrieving bus prediction info for a list of bus stops.
    '''
    # initialize with a list of nextmunipy.BusStop instances
    def __init__(self, stops):
        self.stops = stops
        self.lastUpdateTime = None
        self.stopUpdateTimes = [-1] * len(stops)

        self.checkStops()
        self.routeTag = self.stops[0].routes[0]
        
        self.clearPredictions()
        
      
    # return True if all stops have matching route tags  
    def checkStops(self):
        
        if len(self.stops) < 1:
            raise Exception('StopController must be initialized with at least 1 stop')
        route = self.stops[0].routes
        if isinstance(route, list):
            if len(route) > 1:
                self.stops[0].show()
                raise Exception('StopController stops cannot have most than one associated route')
            else:
                route = route[0]
        
        # check each stop to make sure its routes match that of stops[0]
        flags = []
        for s in self.stops:
            f = False
            if isinstance(s.routes, list):
                if len(s.routes) > 1:
                    s.show()
                    warnings.warn('StopController stops cannot have most than one associated route')
                elif s.routes[0] == route:
                    f = True
            elif isinstance(s.routes, str):
                f = True
            flags.append(f)
        
        return all(flags)
        
            
    
    # UTILITY METHODS
            
    # get the tags for the input stop objects as a list
    def tagsOfStops(self, stops):
        tags = []
        for s in stops:
            tags.append(s.tag)
        return tags
        
    # get the route tags for the input stop objects as a list
    def routeTagsOfStops(self, stops):
        routeTags = []
        for s in stops:
            routeTags.append(s.routes[0])
        return routeTags
        
    # return the stop that has the input tag (string)    
    def stopWithTag(self, tags):
        theStops = []
        for s in self.stops:
            if s.tag in tags:
                theStops.append(s)
        return theStops
    
    def showStops(self, stops=None):
        if stops == None: stops = self.stops
        print "Stops:"
        for s in stops:
            dstr = ''
            for d in s.routeDirs: dstr += str(d)
            a = "  " + s.tag
            if dstr: a += " (" + dstr + ")"
            print a
            
    
       
    # INSTANCE METHODS
         
    # sets all prediction times to empty
    def clearPredictions(self):
        self.predictions = {}
        for s in self.stops:
            self.predictions[s.tag] = []
            
            
    # Returns a boolean (or list of booleans) indicating whether the input stop 
    #   (or list of stops) has been updated on the most recent update.
    def isStopUpdated(self, arg):
        # arg is either an index or string (tag), or a list
        if isinstance(arg, list):
            out = []
            for a in arg:
                out.append(self.isStopUpdated(a))
            return out
            
        elif isinstance(arg, str):
            s = stopWithTag(arg)
            
        elif isinstance(arg, int):
            s = self.stops[arg]
            
        i = self.stops.index(s)
        return self.stopUpdateTimes[i] == self.lastUpdateTime
        
    # send output to screen   
    def show(self):
        print "Stop controller for Route " + self.routeTag
        for s in self.stops:
            dstr = ''
            for d in s.routeDirs: dstr += str(d)
            print "  " + s.tag + " (" + dstr + ")"
     
            
            
    # THE MOST IMPORTANT METHOD !
    # get predicted arrival times and assign to appropriate stops
    def updatePredictions(self):
        
        currentTime = datetime.now()
        
        #if len(self.stops) > MAX_STOPS_PER_REQUEST:
        #    warnings.warn('Desired number of stops (%i) exceeds maximum multi-stop request length set by application (%i).\n  (The actual limit on number of stops in a multi-stop request is 150.)' % (len(self.stops), MAX_STOPS_PER_REQUEST))
        
        # get predictions for all stops in one URL request    
        preds = nm.getMultiStopPrediction(self.routeTagsOfStops(self.stops), self.tagsOfStops(self.stops))
        predList = nm.PredictionList(preds)
        
        self.clearPredictions()
        stopTags = self.tagsOfStops(self.stops)
        
        for p in predList:
            idx = stopTags.index(p.stopTag)
            
            self.predictions[p.stopTag].append(p)
            self.stopUpdateTimes[idx] = currentTime
        
        self.lastUpdateTime = currentTime
    
    
    # Returns the predictions as a dictionary, with stop tags as keys
    def predictionTimes(self, preds=None):
        
        # populate an empty prediction times dictionary
        predTimes = {}
        vehicle = {}
        for s in self.stops:
            predTimes[s.tag] = []
            vehicle[s.tag] = []
        
        # get default argument    
        if preds is None:
            preds = self.predictions
        
        # loop over dictionary, and translate prediction into list
        for k in preds.keys():
            ps = preds[k]
            for p in ps:
                if (UNITS == 'seconds'): ptime = p.getSeconds()
                else: ptime = p.getMinutes()
                predTimes[k].append(ptime)
                vehicle[k].append(p.getVehicle())
            
        return predTimes, vehicle
            
    # Returns the predictions as a matrix
    def predictionTimesMatrix(self, preds=None):
    
        import numpy
        
        (predTimes, vehicles) = self.predictionTimes(preds)
        keys = predTimes.keys()
        M = len(keys)
        N = 0
        
        stopVec = []
        for k in keys:
            d = predTimes[k]
            N = max([N, len(d)])
            stopVec.append(k)
        
        Mat = -1.0 * numpy.ones((M,N))
        
        # assemble matrix
        for r in range(M):
            k = keys[r]
            data = predTimes[k]
            for c in range(len(data)):
                Mat[r,c] = data[c]
                
                
        # change stops vector to int, if possible
        x = -1.0 * numpy.ones(len(stopVec))
        for i in range(len(stopVec)):
            if stopVec[i].isdigit(): 
                x[i] = int(stopVec[i])
        if all(x >= 0):
            stopVec = x
            
        return (Mat,stopVec)


#     # Returns a list of prediction times for a specified vehicle tag
#     def predictionTimesForVehicle(self, v):
#         return None
                
    
        
        
#
# TRACKERCONTROLLER
#
class TrackerController:
    '''
    An object that controls the timing of a StopController's prediction request methods, 
    and generates a database file (currently, a text file) that is periodically updated 
    with prediction/arrival information
    '''
    # initialize using route tag (e.g., '12' or 'N')
    def __init__(self, routeTag, stopIndices=None):
        self.route = nm.BusRoute(routeTag)
        self.timeToRun = TIME_TO_RUN
        self.defaultWaitTime = WAIT_TIME
        self.count = 0
        self.startTime = None
        
        
        # the stop controller
        self.stops = self.route.stops
        if stopIndices:
            newStops = []
            for i in stopIndices:
                newStops.append(self.stops[i])
            self.stops = newStops
            
        self.stopController = StopController(self.stops)
        # make sure all stops only have a single route listed
        for s in self.stopController.stops:
            s.routes = [self.route.routeTag]
        
        
        # file I/O ivars
        fname = DATABASE_FILENAME_BASE + self.route.routeTag
        if APPEND_DATE:
        	# put in YYYYMMDD_HHMMSS format
            fname += ('_' + str(datetime.now()).replace('-','').replace(':','').split('.')[0].replace(' ','_') )
        fname += '.' + DATABASE_FILE_EXT
        self.filename = fname
        
        # open the file where data will be saved (with overwrite turned on; when data
        #	is actually saved, append mode is used)
        self.fid = open(self.filename, 'w')
        self.writeHeaderToFile()
        self.fid.close()	# close for now; open in append mode later
        
            
        # the predictions
        self.activePredictionContainer = {}  # dictionary (key=vehicleNo) containing lists of predictions
        self.predictionArchive = [] # list of arrived predictions
        self.predictionCount = 0
        
        # output
        print "Tracker Controller initialized to follow route %s" % self.route.routeTag
        print "  - Predictions will be saved to:\n      %s" % self.filename
            
    
    # write header info to file
    def writeHeaderToFile(self):
        self.fid.write('# Prediction data for Route ' + self.route.routeTag + '\n')
        self.fid.write('# Date: ' + str(datetime.now()).split('.')[0] + '\n')
        stopStr = ''
        for s in self.stops:
            stopStr += (s.tag + '; ')
        self.fid.write('# Stops to track (%i total): ' % len(self.stops) + '\n')
        self.fid.write('#   ' + stopStr + '\n')
        self.fid.write('# routeTag | stopTag | vehicle | directionTag | startTime | endTime | currentTime | predictedWait | actualWait | uncertainty | latitude | longitude\n')
        
        
    # get all vehicles in a list of predictions
    def getVehicles(self, predList):
        V = []
        for p in predList:
            v = p.getVehicle()
            if v not in V:
                V.append(v)
        return V
    
    
    #
    #
    # VIEWING METHODS
    
    # general-purpose viewer
    def show(self):
        print self.activePredictionContainer
    
    # outputs (to console) the vehicles that are currently being tracked at each stop
    def showActivePredictions(self):
        keys = self.activePredictionContainer.keys()
        for stopTag in keys:
            predByVehicle = self.activePredictionContainer[stopTag]
            vehicles = predByVehicle.keys()
            print "STOP " + stopTag
            print "  Vehicles: " + str(vehicles)
            for v in vehicles:
                preds = predByVehicle[v]
                for p in preds:
                    print "  " + v + ": " + str(p.currentTime).split('.')[0] + " --> " + str(p.getMinutes())
                    
    
    #
    #
    # DATA UPDATING & SAVING METHODS
    
    # save the predictions to file
    def archivePredictions(self, predictions):    
        
        dbp = nm.DatabaseParser()
        sep = dbp.separator
        self.fid = open(self.filename, 'a')
        
        for p in predictions:
        
#          # warn the user if the prediction has not been closed (setEndTime was not called):
#             if not p.actualWait:
#                 warnings.warn('The following prediction may not be closed:')
#                 p.show()
#                 print 'Predicted wait: ' + str(p.getMinutes())
#                 print 'Actual wait:    ' + str(p.actualWait)
            
            if p.actualWait >= 0.0 and p.getMinutes() >= PREDICTION_TIME_THRESHOLD:
            
				# store to ivar:
				self.predictionArchive.append(p)
				self.predictionCount += 1
				
				print "ACTUAL WAIT: " + str(p.actualWait)
				
				# get stop info
				try:
				    stop = self.route.stopWithTag(p.stopTag)
				    if stop:
				        (lat, lon) = stop.getPosition()
				    else:
				        warnings.warn("Could not find stop with tag %s in BusRoute stop list. Cannot save lat/lon." % p.stopTag)
				except:
				    lat, lon = MISSING_VALUE, MISSING_VALUE
				        
				# save prediction to file:
				s = '%s' % p.routeTag + sep
				s += '%s' % p.stopTag + sep
				s += '%s' % p.getVehicle() + sep
				s += '%s' % p.directionTag + sep
				s += '%s' % str(p.startTime).split('.')[0] + sep
				s += '%s' % str(p.endTime).split('.')[0] + sep
				s += '%s' % str(p.currentTime).split('.')[0] + sep
				s += '%i' % p.getMinutes() + sep
				s += '%f' % p.actualWait + sep
				s += '%i' % p.uncertainty + sep
				s += '%f' % lat + sep
				s += '%f' % lon + sep
				s += '\n'
				self.fid.write(s)
            
   
         
    # Call to indicate that the predicted vehicle has arrived in a prediction list
    #    (independent of writing prediction to file--this is done by archivePredictions)
    def closePredictions(self, predList, updateTime=None):
    
        if isinstance(predList, nm.Prediction):
            predList = [predList]
        
        if not updateTime:
            updateTime = self.stopController.lastUpdateTime
            
        check = predList[0].endTime
                
        for p in predList:
            p.setEndTime(updateTime)
        
        #self.showArrival(predList)
        
        if check == predList[0].endTime:
            warnings.warn('output list has not been changed; could be a reference/value problem.')
                
        return predList
            
            
    # Cycles through predictions to see if any arrivals occurred, and takes appropriate database action
    def trackUsingPredictions(self, predictions, updateTime):
        
        # predictions are organized by stop (i.e., predictions' keys are stop tags)
        keys = predictions.keys()
        
        activeStops = self.activePredictionContainer.keys()				# the stops in the container currently
        
        for stopTag in keys:
            
            predsByStop = predictions[stopTag]           				# all predictions for a certain stop
            vehiclesCurrentlyAtStop = self.getVehicles(predsByStop)		# the vehicles currently at that stop
            
            # find the vehicles at this stop that we are tracking (in the container):
            if stopTag in activeStops:
                contents = self.activePredictionContainer[stopTag]
                if isinstance(contents, dict):
                    vehiclesBeingTrackedAtStop = contents.keys()
                else:
                    vehiclesBeingTrackedAtStop = []
            else:
                self.activePredictionContainer[stopTag] = {}
                vehiclesBeingTrackedAtStop = []
                    
            for p in predsByStop:
                v = p.getVehicle()		# one of the vehiclesCurrentlyAtStop
                p.startTime = self.startTime
                
                if v in vehiclesBeingTrackedAtStop:
                    self.activePredictionContainer[stopTag][v].append(p)
                else:
                    if (p.getMinutes() > 0):
                        self.activePredictionContainer[stopTag][v] = [p]
                    else:
                        None
                        # this means we have already counted the vehicle as arrived (i.e., its
                        #   timer went to 0 in a previous iteration), but it is still on the prediction
                        #   list.  In this case, do not re-add it to the list.
                
            # see if any vehicles have arrived (i.e., are no longer in the vehiclesCurrentlyAtStop list)
            arrivedVehicles = []
            for v in vehiclesBeingTrackedAtStop:
                arrived = None
                if v not in vehiclesCurrentlyAtStop:
                    p = self.activePredictionContainer[stopTag][v][-1]
                    estimatedWait = p.getMinutes()
                    actualTime = (datetime.now() - p.currentTime).total_seconds()/60.0
                    if estimatedWait / actualTime > 4.0:
                        arrived = 'arrival unlikey; estimate exceeded real wait time by factor of >= 4.0'
                        del self.activePredictionContainer[stopTag][v]
                    else:
                        arrivedVehicles.append(v)
                        arrived = 'no longer on active vehicle list'
                elif self.activePredictionContainer[stopTag][v][-1].getMinutes() <= 0:    # if times has reached 0, count vehicle as arrived
                    p.setEndTime(updateTime)  # <----- this is used to set the time when prediction went to 0; it will be averages with the time when the vehicle disappeared from the list
                    #arrivedVehicles.append(v)
                    arrivalLogic = 'timer reached zero'
                
                if VERBOSE and arrived:
                    stop = self.route.stopWithTag(stopTag)
                    print '*** Vehicle ' + v + ' arrived at stop ' + stopTag + ' (' + stop.name + ') ***'
                    print '    Reason: ' + arrived + '\n'
   
            # if there are arrived vehicles
            for v in arrivedVehicles:
                # move all predictions for this vehicle at this stop to the archive
                predsToArchive = self.activePredictionContainer[stopTag][v]   # <-- this is a list of predictions
                if predsToArchive:
                    self.closePredictions(predsToArchive, updateTime)
                    del self.activePredictionContainer[stopTag][v]
                    self.archivePredictions(predsToArchive)
  
  
    #
    #
    # TIMING METHODS
    
    # runs the tracker on the specified route, generating a data file    
    def start(self):
        
        elapsedTime = 0
        startTime = datetime.now()
        currentTime = datetime.now()
        endTime = startTime + timedelta(seconds=self.timeToRun)
        currentWaitTime = self.defaultWaitTime
        aveExecutionTime = 0
        
        self.startTime = startTime
        self.count = 0
        
        # begin timing the route
        try:
            while currentTime <= endTime:
               
                print '+---------------------------------------------------'
                print '| ITERATION ' + str(self.count)
                print '|   Current time:      ' + str(currentTime).split('.')[0]
                print '|   Expected end time: ' + str(endTime).split('.')[0]
                print '|   Tracking %i stops' % len(self.stops)
                if self.predictionCount > 0: print '|   %i predicted arrivals recorded' % self.predictionCount
                print '+---------------------------------------------------\n'            
           
                # wait the specified amount of time
                if (self.count > 0): time.sleep(currentWaitTime)
                t0 = datetime.now()
				
                # update predictions
                self.stopController.updatePredictions()
				
                # see if any arrivals occurred, and log predictions
                self.trackUsingPredictions(self.stopController.predictions, self.stopController.lastUpdateTime)
                # self.showActivePredictions()
				
				
                # update execution time
                currentTime = datetime.now()
                self.count += 1
                aveExecutionTime = ((self.count - 1) * aveExecutionTime + (currentTime - t0).total_seconds()) / self.count
                currentWaitTime = max(self.defaultWaitTime - aveExecutionTime, 1e-3)
			
			# end of while loop.
        
        except:
            print '\n\n*** LOOP FAILED TO COMPLETE ***\n\n'
        self.stop()
    
    
    # stop method cleans up file i/o, and displays results
    def stop(self):
        self.fid.close()
        
        print '\n\n\nExecution completed at ' + str(datetime.now()).split('.')[0]
        print '\nAll prediction info saved to:\n' + '--> ' + self.filename
        print '--> (%i predictions total)' % self.predictionCount
        
        
        
        
#
# UTILITY FUNCTIONS
#

# Loads the specified file, makes a copy, and appends the stop latitude/longitude info
#   (Early database files were not saved with this information; this corrects the omission)
def appendLatLonToDatabaseFile(filename, route):

    from numpy import nan
    MISSING_VALUE = nan
    
    dbp = nm.DatabaseParser()
    sep = dbp.separator
        
    fr = open(filename,'r')
    (fileBase, ext) = os.path.splitext(filename)
    tempFilename = fileBase + '_TEMP' + ext
    fw = open(tempFilename, 'w')
    count = 0
    errorCount = 0
    badStopTags = []
    
    try:
        for line in fr:
            if line.strip()[0] == dbp.commentTag:
                newLine = line
            else:
                newLine = line.replace('\n','')
                data = line.split(sep)
                stopTag = data[1].strip()
                try:
                    stop = route.stopWithTag(stopTag)
                    (lat,lon) = stop.getPosition()
                except:
                    (lat,lon) = MISSING_VALUE, MISSING_VALUE
                    errorCount += 1
                    badStopTags.append(stopTag)
                newLine += (str(lat) + sep + ' ' + str(lon) + sep + '\n')
        
            count += 1
        
            fw.write(newLine)
    except:
        fr.close()
        fw.close()
        
    fr.close()
    fw.close()
        
    print "%i lines copied to file %s" % (count, tempFilename)
    print "%i errors encountered in determining/writing latitude/longitude values" % errorCount
    if errorCount > 0:
        print badStopTags
        
        