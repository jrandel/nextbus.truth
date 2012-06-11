# This module creates data files (txt format) that can be loaded by
# Javascript files to plot the following using Google Map's API:
#	1. Bus routes
#	2. Bus route delays



# COPY PASTE THE FOLLOWING:
# cd /users/jason/documents/python work
# import nmplotter as nmp; import nmdata; import nextmunipy as nm; import nmtracker as track; import nmvis as vis; import nmanalyze as nman;
# (d,lat,lon,st)=nmp.delaysForRoute('12',range(10,16))
# (plat,plon,dnorm)=nmp.delaysToPolyline((lat,lon),d,[0,4]);
# nmp.addDelayPolylineToFileStupid('GMapDelaysRte12.txt','12',(plat,plon),dnorm);
#
# Then go to 'GMapDelaysRte12.txt' and copy paste into the bottom of this file.


import os
import nmdata
import numpy



# '12',range(18,23),'IB' is interesting

def wrapper(routeTag,predRange=range(18,23),dirTag='IB'):
    (d,lat,lon,st)=delaysForRoute(routeTag,predRange,dirTag)
    clims = [0, numpy.ceil(numpy.max(d))]
    clims = [numpy.floor(numpy.min(d)), numpy.ceil(numpy.max(d))];
    (plat,plon,dnorm)=delaysToPolyline((lat,lon),d,clims);
    addDelayPolylineToFileStupid('GMapDelaysRte' + routeTag + '.txt',routeTag,(plat,plon),dnorm,clims,dirTag);
    print 'Route ' + routeTag + '(' + dirTag + ') ready.'
    
        
# return a list of positions and corresponding delays for a route (all files)
def delaysForRoute(routeTag, predictionRange, dirTag=None):

    prefix = 'PredictionDatabaseRte' + routeTag + '_'
    ext = '.dat'
    fileList = []
    folder = '/users/jason/documents/python work'
    
    # find all files with the target route
    files = os.listdir(folder)
    for f in files:
        if prefix in f and ext in f and not 'OLD' in f:
            fileList.append(os.path.normpath(folder + '/' + f))
        elif f == 'PredictionDatabaseRte' + routeTag + ext:
            fileList.append(os.path.normpath(folder + '/' + f))
    
    # open files, get data
    delays = []
    latitudes = []; longitudes = []
    stopTags = []; pointsInAverage = []
    for f in fileList:
        (d,lat,lon, stags, npts) = nmdata.getDelays(f, predictionRange, dirTag)
        
        for i in range(len(d)):
        	st = stags[i]
        	if st in stopTags:
        		idx = stopTags.index(st)
         		delays[idx] = (pointsInAverage[idx] * delays[idx] + npts[i] * d[i]) / (pointsInAverage[idx] + npts[i])
         		pointsInAverage[idx] = pointsInAverage[idx] + npts[i]
        	else:
        		delays += [d[i]]
        		latitudes += [lat[i]] 
        		longitudes += [lon[i]]
        		stopTags += [st]
        		pointsInAverage += [npts[i]]
    
    # put everything in order
    import nextmunipy as nm
    rte = nm.BusRoute(routeTag)
    latBefore = latitudes
    lonBefore = longitudes
    latitudes = rte.sortStopTags(stopTags, latitudes)
    longitudes = rte.sortStopTags(stopTags, longitudes)
    delays = rte.sortStopTags(stopTags, delays)
    stopTags = rte.sortStopTags(stopTags)
    
    return (delays, latitudes, longitudes, stopTags)
    

# convert delays into a gradiented polyline
def delaysToPolyline(positions, delays, colorLimits=None):
    # return startpoint, endpoint, float for colormap (0 to 1)
    # positions = (lats, lons)
    ptsPerGradSegment = 20    # when a line changes from one color to another, it does so with this many color steps
    fraction = 1./3.
    
    # make sure colorLimits is a range:
    maxDelay = numpy.max(delays)
    if type(colorLimits) == float or type(colorLimits) == int:
        colorLimits = [0., float(colorLimits)]
    elif not isinstance(colorLimits,list):
        raise Exception('colorLimits argument must be a list')
    elif not colorLimits:
        colorLimits = [0., maxDelay]
    
    # normalize delays
    delays = (delays - numpy.min(colorLimits)) / numpy.diff(colorLimits)
    
    latitudes = positions[0]
    longitudes = positions[1]
    
    # check data lengths    
    npts = len(delays)
    if len(latitudes) != len(longitudes):
        raise Exception('Number of latitude coordinates (%i) must match number of longitude coordinates (%i)' % (len(latitudes), len(longitudes)))
    if len(latitudes) != npts:
        raise Exception('Number of delays (%i) must match number of lat/lon coordinates (%i)' % (len(delays), len(longitudes)))

    # the polyline lat/lons:
    pLat = []
    pLon = []
    dNorm = []	# normalized color (0,1)
    
    for i in range(npts - 1):
    
        x = longitudes[i]
        y = latitudes[i]
        d = delays[i]
        
        tx = fraction * (longitudes[i + 1] - longitudes[i]);
        ty = fraction * (latitudes[i + 1] - latitudes[i]);
        
        xnext = x + tx
        ynext = y + ty
        dnext = d
        
        for j in range(ptsPerGradSegment):
            xnext += tx / ptsPerGradSegment
            ynext += ty / ptsPerGradSegment
            dnext = d + (delays[i + 1] - d) * j / ptsPerGradSegment
            
            pLon.append(xnext)
            pLat.append(ynext)
            dNorm.append(dnext)
            
        pLat.append(latitudes[i + 1] - ty)
        pLon.append(longitudes[i + 1] - tx)
        dNorm.append(delays[i + 1])
    
    return (pLat,pLon,dNorm)
        

# the red-yellow-green colormap
def TrafficColormap():
    import matplotlib
	
    hsv = numpy.empty((1,256,3))
    hsv[:,:,0] = numpy.linspace(0.0,1.0 * 75/255,256)  # red to green
    hsv[:,:,1] = 1.0
    hsv[:,:,2] = numpy.hstack((numpy.linspace(0.75,1.0,256/2), numpy.linspace(1.0,1.0,256/2)))
    rgb, = matplotlib.colors.hsv_to_rgb(hsv)
    
    colorMap = matplotlib.colors.LinearSegmentedColormap.from_list('TrafficLight',rgb,N=256)
    return colorMap
    
    

# ------------------------------------------------------------------------
# FUNCTIONS FOR OUTPUTTING TO FILE

#	"filetype": 'delays',
#	"routes": [    {"routeTag": '14',
#					"routeName": '14 Mission',
#					"directionName": 'Inbound',
#					"polyLine": {  "points": 400,
#								   "lat": [y0, y1, y2, ...],
#								   "lon": [x0, x1, x2, ...],
#								   "delay": [t0, t1, t2, ...],
#								   "color": [c0, c1, c2, ...]
#				  },
#				   {"routeTag": '22', 
#						...
#				 	},
#					...
#			  ]
#	}


# makes sure polyline (lat, lon, delay) has the correct list lengths
def checkPolylineData(a0,a1,a2=None):
    success = False
    if not a2:
        try:
            latitudes = a0[0]
            longitudes = a0[1]
        except IndexError:
            raise Exception('Cannot determine lat/lon from the two inputs (first one should be a 2-element list: [lats, lons])')
        delays = a1
    else:
        latitudes = a0
        longitudes = a1
        delays = a2
    
    if len(latitudes) != len(longitudes):
        raise Exception('# of latitudes and longitudes must match')
    if len(delays) != len(latitudes):
        raise Exception('# of delays must match # of latitudes and longitudes')

    return (latitudes, longitudes, delays)
    

# adds the provided polyline data to the specified file (creates it if necessary)    
def addDelayPolylineToFile(filename, route, positions, normalizedDelays):

    import json
    
    if os.path.exists(filename):
         fr = open(filename, 'r')
         theDict = json.load(fr)
    else:
         theDict = {"filetype":"delays", "routes":[]}
    
    (latitudes, longitudes, normalizedDelays) = checkPolylineData(positions, normalizedDelays)
    
    if type(route) == str: 
        import nextmunipy as nm
        route = nm.BusRoute(route)
        
    routeList = theDict["routes"]
    
    # append 
    newRouteDict = {}
    newRouteDict["routeTag"] = route.routeTag
    newRouteDict["routeName"] = route.routeName
    pLine = {"points": len(normalizedDelays), \
             "lat": latitudes, "lon": longitudes, \
             "value": normalizedDelays, "color": [] }
    newRouteDict["polyline"] = pLine
    
    routeList.append(newRouteDict)
    theDict["routes"] = routeList
    
    if os.path.exists(filename): fr.close()
    
    # write back to file
    fw = open(filename, 'w')
    json.dump(theDict, fw)
    fw.close()
    
# write a javascript line by line   
def addDelayPolylineToFileStupid(filename, route, positions, normalizedDelays, clim, dirTag):
    
    (latitudes, longitudes, normalizedDelays) = checkPolylineData(positions, normalizedDelays)
    map = TrafficColormap()
    import matplotlib
    
    if type(route) == str: tag = route
    else: tag = route.routeTag
    
    fw = open(filename,'w')
    fw.write('function getRouteTag() {return "' + tag + '";}\n');
    fw.write('function getDirTag() {return "' + dirTag + '";}\n');
    fw.write('function minDelay() { return (getClim()[0]);\n}\n');
    fw.write('function maxDelay() { return (getClim()[1]);\n}\n');
    fw.write('function getClim() { return [' + str(clim[0]) + ',' + str(clim[1]) + '];\n}\n');
    fw.write('function getPolylineLatitudes() {\n');
    fw.write('    var latitudes = [\n')
    for lat in latitudes: fw.write('        ' + str(lat) + ',\n')
    fw.write('        ];\n   return latitudes;\n}\n')
    fw.write('function getPolylineLongitudes() {\n');
    fw.write('    var longitudes =[\n')
    for lon in longitudes: fw.write('        ' + str(lon) + ',\n')
    fw.write('        ]; \n   return longitudes;\n}\n')
    fw.write('function getPolylineColors() {\n');
    fw.write('    var colors =[\n')
    for d in normalizedDelays: fw.write("       '" + matplotlib.colors.rgb2hex(map(d)) + "',\n")
    fw.write('        ];\n   return colors;\n}\n')
    
    fw.write('function colormap(val) {\n');
    fw.write('    var colors =[\n')
    for n in range(map.N): fw.write("       '" + matplotlib.colors.rgb2hex(map(n)) + "',\n")
    fw.write('        ];\n   return colors[val];\n}\n')
    fw.close()
    
    
# {
#	"filetype": 'route',
#	"routeTag": "14",
#	"routeName": "14 Mission",
#	"routeDirection": "Inbound",
#	"stops": [    {	"stopTag": '1151',
#					"stopName": 'Mission St. & 16th St.",
#					"lat": 33.556492,
#					"lon": -127.223441,
#					("delay": 1.23)
#				  }
#			  ]
#	}
def printRouteToFile(filename, route, directionInfo='IB'):

    import json
    
    if type(route) == str: 
        import nextmunipy as nm
        route = nm.BusRoute(route)
    
    # check if file already exists
    if os.path.exists(filename):
        yesOrNo = raw_input('File %s already exists. Overwrite? (y/n): ' % filename)
        if yesOrNo and yesOrNo.lower()[0] == 'y':
            print "Overwriting."
        else:
            print "Aborting."
    
    fw = open(filename, 'w')
    if not fw:
        raise Exception('Cannot open %s for writing' % filename)
        
    theDict = {}
    theDict["filetype"] = "route"
    theDict["routeTag"] = route.routeTag
    theDict["routeName"] = route.routeName
    theDict["direction"] = route.directionKeyLike(directionInfo)
    theDict["directionDescription"] = route.directionList[theDict["direction"]]
    stopList = []
    for s in route.stops:
        stopDict = {}
        stopDict["stopTag"] = s.tag
        stopDict["stopName"] = s.name
        stopDict["lat"], stopDict["lon"] = s.getPosition()
        stopList.append(stopDict)
        
    theDict["stops"] = stopList
    
    # print to json file
    json.dump(theDict, fw)
    fw.close()