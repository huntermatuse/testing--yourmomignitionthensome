import os
import sys

logger = system.util.getLogger('exchange.comtrade')
	
def folderRoot():
	"""File path to the folder containing comtrade files"""
	return '/usr/local/bin/ignition/webserver/webapps/comtrade'
	
def folderStorage():
	return '%s/storage' % folderRoot()	
	
def folderUpload():
	return '%s/upload/' % folderStorage()
	
def folderFtp():
	return '%s/ftp/' % folderStorage()	
	
def sftpScript():
	return '%s/scripts/sftpcopy.sh' % folderRoot()
	
def zipFolder():
	return '%s/zips/' % folderRoot()
	
def localDirectoryToTree(directoryPath):
	def createItem(label, expanded, data, items):
		return {
			"label": label,
			"expanded": expanded,
			"data": data,
			"items": items
		}

	def walkDirectory(path):
		items = []
		for root, dirs, files in os.walk(path):
			dirs.sort()  # Sort directories alphabetically
			files.sort()  # Sort files alphabetically
			for dirName in dirs:
				fullPath = os.path.join(root, dirName)
				data = {'isFile': False, 'fullPath': fullPath, 'timestamp': system.date.now()}
				items.append(createItem(dirName, False, data, walkDirectory(fullPath)))
			for fileName in files:
				if fileName.endswith(':Zone.Identifier'):
					continue
				fullPath = os.path.join(root, fileName)
				data = {'isFile': True, 'fullPath': fullPath, 'timestamp': system.date.now()}
				items.append(createItem(fileName, False, data, []))
			break
		return items

	rootItems = walkDirectory(directoryPath)
	return rootItems
	
def localTree():
	return localDirectoryToTree(folderStorage())

def filterNestedDict(d, parentKey = None, filterOutKeys = ['values']):
	"""
	Filters out specific list values from a dictionary, useful when there is too much data
	
	Args:
		d (dict): The dictionary to filter
		parentKey (string): name of the dictionary being passed in
		filterOutKeys (list): names of keys to filter out
	"""
	if isinstance(d, list):
		if parentKey in filterOutKeys:
			return []
		else:
			return [filterNestedDict(item, parentKey) for item in d]
	elif isinstance(d, dict):
		return {key: filterNestedDict(value, key) for key, value in d.items()}
	else:
		return d
		
def addToDict(d, keys, value):
	"""
	Set a value in a nested dictionary, creating any necessary keys along the way.
	
	Args:
		d (dict): The dictionary to update.
		keys (list): A list of keys representing the path in the nested dictionary.
		value: The value to set at the specified path.
	"""
	for key in keys[:-1]:
		if key not in d:
			d[key] = {}
		d = d[key]
	d[keys[-1]] = value

		
def strToDateAndMicro(date, time, dateFormat='dd/MM/yyyy', timeFormat = 'HH:mm:ss.SSS'):
	d = time.find('.')+4
	timeWithMillis = time[:d]
	microStr = time[d:]
	if len(microStr) > 0:
		micro = int(microStr) * 10 ** (3-len(microStr))
	else:
		micro = 0
	return system.date.parse('%s %s' % (date, timeWithMillis), '%s %s' % (dateFormat, timeFormat)), micro

def average(points):
	return 1.0 * sum([float(p) for p in points]) / len(points)

def parse(filename, sessionId, pageId, dateFormat = 'dd/MM/yyyy'):	
	logger.info('Starting to parse file: %s' % filename)
	
	filepath, extension = os.path.splitext(filename)

	comtradeObj = exchange.comtrade.comtrade.ComtradeRecord()
	comtradeObj.read('%s.cfg' % filepath, '%s.dat' % filepath)
	
	
	startTimestamp, startMicro = strToDateAndMicro(comtradeObj['start_date'], comtradeObj['start_time'], dateFormat)
	triggerTimestamp, triggerMicro = strToDateAndMicro(comtradeObj['trigger_date'], comtradeObj['trigger_time'], dateFormat)
	
	if system.date.format(startTimestamp, 'yyyy-MM-dd')=='1970-01-01' and system.date.format(triggerTimestamp, 'yyyy-MM-dd')!='1970-01-01':
		# startTimestamp is invalid, but triggerTimestamp is valid, use it instead
		startTimestamp = triggerTimestamp
		startMicro = triggerMicro
	
	startTimeMs = system.date.toMillis(startTimestamp)
	startTimeBeginning = startTimeMs % 60000
	startTimeOffset = startTimeMs - startTimeBeginning
	startFloatTime = float(system.date.toMillis(startTimestamp)) + float(startMicro)/1000.0
	timeStepMs = 1000.0 / comtradeObj['samp'][-1]
	
	data = []
	lowRes = []
	for i in xrange(comtradeObj['endsamp'][-1]):
		zeroedMillis = startTimeBeginning + i * timeStepMs
		zeroedSeconds = zeroedMillis / 1000.0
		time = system.date.fromMillis(startTimeOffset + long(zeroedMillis))
		if i == 0:
			prevTime = time
			prevZeroedSeconds = zeroedSeconds
			prevIndex = i
		elif time != prevTime or i == comtradeObj['endsamp'][-1] - 1:
			if i - 1 > prevIndex:
				lowRes.append(
					[prevTime,prevZeroedSeconds,0]+
					[average(comtradeObj['A'][iA]['values'][prevIndex:i-1]) for iA in xrange(comtradeObj.cfg_data['#A'])]+
					[average(comtradeObj['D'][iD]['values'][prevIndex:i-1]) for iD in xrange(comtradeObj.cfg_data['#D'])]
				)
			else:
				lowRes.append(
					[prevTime,prevZeroedSeconds,0]+
					[comtradeObj['A'][iA]['values'][i-1] for iA in xrange(comtradeObj.cfg_data['#A'])]+
					[comtradeObj['D'][iD]['values'][i-1] for iD in xrange(comtradeObj.cfg_data['#D'])]
				)
			prevTime = time
			prevZeroedSeconds = zeroedSeconds
			prevIndex = i
		data.append(
			[time,zeroedSeconds,0]+
			[comtradeObj['A'][iA]['values'][i] for iA in xrange(comtradeObj.cfg_data['#A'])]+
			[comtradeObj['D'][iD]['values'][i] for iD in xrange(comtradeObj.cfg_data['#D'])]
		)
	headers = (
		['time','zeroedSeconds', 'zero'] + 
		['A%s' % (iA+1) for iA in xrange(comtradeObj.cfg_data['#A'])] + 
		['D%s' % (iD+1) for iD in xrange(comtradeObj.cfg_data['#D'])]
	)
	lowResHeaders = (
		['time','zeroedSeconds', 'zero'] + 
		['A%s' % (iA+1) for iA in xrange(comtradeObj.cfg_data['#A'])] + 
		['D%s' % (iD+1) for iD in xrange(comtradeObj.cfg_data['#D'])]
	)
	highRes = system.dataset.toDataSet(headers, data)
	lowRes = system.dataset.toDataSet(lowResHeaders, lowRes)

	addToDict(system.util.getGlobals(),['exchange','comtrade',sessionId,pageId], {
		 'highRes': highRes
		,'lowRes' : lowRes
		,'timestamp': system.date.now()
		,'filename': filename
	})
	logger.info('copied dictionary into globals')
	
	del data
	del lowRes
	
	return {
		'data': filterNestedDict(comtradeObj.cfg_data), 
		'timestamp': system.date.now(), 
		'filename': filename.replace(folderRoot(),''), 
		'startTimeOffset':startTimeOffset
	}