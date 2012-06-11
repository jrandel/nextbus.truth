# NMVIS

predTime = []
stopId = []
realTime = []


import matplotlib as mat
import pylab, matplotlib
import numpy
import gmapsapistatic as gmap
import subprocess
import nextmunipy as nm
import nmdata         

# ----------------------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ----------------------------------------------------------------------------------------

# returns True if the input is of any of the following forms:
#    ( (x1,y1), (x2,y2), ... )        	tuple of 2-element tuples
#    [ (x1,y1), (x2,y2), ... ] 			list of 2-element tuples
#    ([x1,x2,...], [y1,y2,...] ) 		2-element tuple of lists
def isCoordList(v):
    try:
        print gmap.convertToCoords(v)
        return True
    except gmap.CoordError:
        return False
        
    

# ----------------------------------------------------------------------------------------
# 1-D VISUALIZATION
# ----------------------------------------------------------------------------------------
     
# show a histogram of actual wait times with a given predicted wait time  
def histAtPredTime(routeTag=None,pt=10):
    (p,r) = nmdata.loadWaitTimes(routeTag)
    v = []
    for i in range(len(p)):
        if p[i] == pt:
            v.append(r[i])
    pylab.hist(v)
    #pylab.hist(v)
    print "\n%.2f +/- %.2f min real wait (for %i min predicted wait)" % (numpy.mean(v), numpy.std(v), pt)
    delay = numpy.mean(v) - pt
    print "  --> %.2f min delay" % delay
    return v


# show a scatter plot of the input wait times (usually p,w from loadData() function)
def scatterWaitTimes(p,w):
    pylab.plot(p,w,'o')
  
  
    
# ----------------------------------------------------------------------------------------    
# 2-D VISUALIZATION
# ----------------------------------------------------------------------------------------


def histByPredTime(routeTag=None):
    
    '''
    y = 1.3 + 0.052413 * x fits the data well for predictions < 30min. 
    '''
    thresh = numpy.exp(-0.5)
    minDelay = -20
    maxDelay = 40
    delayIncrement = 1.0
    SHOWY = True
    mode = ''
    npts = 100
    
    #theData = nmdata.PredData(nmdata.loadData(routeTag))
    theData = nmdata.PredData(routeTag)
    
    delay = numpy.array(theData.delays())
    
    # delay = delay/p	# turns delay into a percent delay
    
    rBins = numpy.arange( numpy.floor(numpy.min(delay[delay>=minDelay])), \
					  numpy.ceil(numpy.max(delay[delay<=maxDelay])), \
					  delayIncrement)
    rc = rBins + numpy.diff(rBins)[0]
    rc = rc[:-1]
    rx = numpy.linspace(numpy.min(rBins), numpy.max(rBins), npts)
	
    maxP = 60
    Y = numpy.zeros((len(rBins) - 1, maxP))
    nPredictions = numpy.ones(maxP)
    
    Yg = numpy.zeros((npts, maxP))
    Yi = Yg
    eU = numpy.zeros(maxP)
    eL = numpy.zeros(maxP)
    meanDelay = numpy.zeros(maxP)
    modeDelay = numpy.zeros(maxP)
    stdDelay = numpy.zeros(maxP)
    
    for t in range(maxP):
        delayByP = theData.delaysForPredEqualTo(t)
        if any(numpy.isnan(delayByP)):
            print t,delayByP
        (h,edges) = numpy.histogram( delayByP, bins=rBins, range=(minDelay,maxDelay) )
        h = 1.0 * h   # convert to float
        
        Y[:,t] = h
        nPredictions[t] = numpy.max((numpy.sum(h), 1))
        #if any(h): h = h/numpy.sum(h)
        #h[numpy.isnan(h)] = 0.0
        
        meanDelay[t] = numpy.mean(delayByP)
        stdDelay[t] = numpy.std(delayByP)
        modeDelay[t] = rBins[list(h).index(numpy.max(h))]
        
        if any(h):
            eL[t] = rBins[list(h/max(h) > thresh).index(True)]
            hList = list(h)
            hList.reverse()
            hList = numpy.array(hList)
            eU[t] = rBins[list(hList/max(hList) > thresh).index(True)]
        Yg[:,t] = numpy.sum(h) * numpy.exp(-(rx - meanDelay[t])**2/(2*(stdDelay[t])**2))
        Yi[:,t] = numpy.interp(rx, rc, h)

    if SHOWY:
        fig = pylab.figure(facecolor='w')
        if mode == 'stacked':
            colorMap = matplotlib.cm.get_cmap('spring')
            x = edges + numpy.diff(edges)[0]
            x = x[0:-1]
            for i in range(maxP):
                y = Y[:,i]
                pylab.bar(x,1.0,color=colorMap(float(i)/float(maxP)),linewidth=1.0)
        else:
            scaling = 100.0
            N = numpy.tile(nPredictions,(numpy.shape(Yi)[0],1))
            pylab.imshow(Yi/N * scaling, origin='lower', extent=[0,maxP,numpy.min(edges),numpy.max(edges)], aspect='auto')
            pylab.plot(range(0,maxP),[0.0]*maxP,'--w',linewidth=2.0)
            #pylab.plot(range(0,maxP),modeDelay + 1.,'-ow',linewidth=3.0)
            #pylab.plot(range(0,maxP),meanDelay,'.-w',linewidth=1.5)
            #pylab.plot(range(0,maxP),meanDelay + stdDelay,'--w',linewidth=1.0)
            #pylab.plot(range(0,maxP),meanDelay - stdDelay,'--w',linewidth=1.0)
            #pylab.plot(range(0,maxP),eU,'--w',linewidth=2.0)
            #pylab.plot(range(0,maxP),eL,'--w',linewidth=2.0)
            pylab.axis((1.,maxP,min(edges),max(edges)))
            pylab.axis((1.,30.,-2.,8.));
            pylab.clim((0,0.35 * scaling))
            cb = pylab.colorbar()
            cb.ax.set_ylabel('Frequency (%)')
            pylab.xlabel('Predicted Wait (minutes)')
            pylab.ylabel('Real wait ${-}$ predicted wait (minutes)')
            
            print "mean / std:"
            for i,m,s in zip(list(range(maxP)), list(meanDelay), list(stdDelay)):
                print "  %i    %f +/- %f (%i)" % (i,m,s,int(numpy.sum(Y[:,i])))
                
    return rBins,(Y,Yg,Yi),(meanDelay,stdDelay,modeDelay,eL,eU)
        

# def histByVar(routeTag=None, varName='predictions'):
#     thresh = numpy.exp(-0.5)
#     minDelay = -20
#     maxDelay = 40
#     delayIncrement = 1.0
#     SHOWY = True
#     mode = ''
#     npts = 100
#     
#     theData = nmdata.PredData(nmdata.loadData(routeTag))
#     yData = numpy.array(theData.delays())
#     xData = numpy.array(getattr(theData, varName))
#     
#     binEdges = numpy.arange( numpy.floor(numpy.min(yData[yData>=minDelay])), \
# 					  numpy.ceil(numpy.max(yData[yData<=maxDelay])), \
# 					  delayIncrement)
#     binCenters = binEdges + numpy.diff(binEdges)[0]
#     binCenters = binCenters[:-1]
#     binsForFit = numpy.linspace(numpy.min(binEdges), numpy.max(binEdges), npts)
# 	
#     xMax = numpy.max(xData)
#     H = numpy.zeros((len(binEdges) - 1, xMax))
#     Hg = numpy.zeros((npts, xMax))		# gaussian 
#     Hi = Yg								# linear interpolation
#     nPredictions = numpy.ones(xMax)
#     
#     xAve = numpy.zeros(xMax)
#     xMode = numpy.zeros(xMax)
#     xStd = numpy.zeros(xMax)
#     
#     for x in range(xMax):
#         delayByP = theData.dataForVarEqualTo(strOut, strVar, val):

    
# ----------------------------------------------------------------------------------------
# GOOGLE MAPS VISUALIZATION
# ----------------------------------------------------------------------------------------


# Base-level functions (plot stops, etc
def copyStringToClipboard(aStr):
    
    if type(aStr) != str:
        raise Exception('Input must be a string')
        return
    
    # copy the url to the clipboard
    p = subprocess.Popen(['pbcopy'],stdin=subprocess.PIPE)
    p.stdin.write(aStr)
    p.stdin.close()
        
    
# gmapStops
#   Show all of the indicated locations (a list or route object) on a gmap path/series of markers
def gmapStops(locations, c=None, opt=None):
    
    # normalize input
    if not isCoordList(locations):
        try: 
            locations = locations.inboundStopPositions()   # returns (lat,lon,stopTag)
            locations = (locations[0],locations[1])
        except AttributeError:
            raise Exception('Could not determine stop positions from input BusRoute object')

    if opt and 'mark' in opt:
        url = gmap.googleMapWithMarkers(locations, c=c)
    else:
        url = gmap.googleMapWithPaths(locations, c=c);
        
    copyStringToClipboard(url)
    return url
  
    
# shows stops with different color paths between each stop
def gmapStopsWithColors(locations, colorByLocation, decimate=1):
    
    if type(locations[0]) != tuple and type(locations[0]) != list and type(locations[0]) != numpy.ndarray:   # assume locations is a list of bus stops
        pos = []
        for s in locations: pos.append(s.getPosition())
        locations = pos
    
    # input checking
    if type(colorByLocation) != list:
        if len(locations) == 1:
            colorByLocation = [colorByLocation]
        else:
            raise Exception('colorByLocation must be a list')
        
    if len(colorByLocation) != len(locations):
        raise Exception('Location list must be same length of color list')

    if decimate > 1:
        newLocations = []; newColors = []
        count = 0
        for loc, color in zip(locations, colorByLocation):
            if numpy.mod(count,decimate) == 0:
                newLocations.append(loc)
                newColors.append(color)
            count += 1
        if loc != locations[-1]:
            newLocations.append(locations[-1])
            newColors.append(colorByLocation[-1])
        locations = newLocations
        colorByLocation = newColors
    
    # get the basic URL    
    url = gmap.googleMapBasicUrl()
    
    # add every path
    for index in range(len(locations) - 1):
        loc1 = locations[index]
        loc2 = locations[index+1]
        color = colorByLocation[index]
        url = gmap.gmAddPath(url, [loc1,loc2], c=color, w=9.9)
        
    # send to clipboard
    copyStringToClipboard(url)
    return url