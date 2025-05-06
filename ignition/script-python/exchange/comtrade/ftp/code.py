import ftplib
import os

def downloadFtpFiles(ftpHost, ftpPort, ftpUser, ftpPass, remoteDir, localDir):
	try:
		ftp = ftplib.FTP()
		ftp.connect(host=ftpHost, port=ftpPort)
		ftp.login(ftpUser, ftpPass)
		ftp.set_pasv(True)  # Enable passive mode
		downloadDirectory(ftp, remoteDir, localDir)
	except Exception as e:
		print("FTP Error: ", e)
	finally:
		ftp.quit()

def downloadDirectory(ftp, remoteDir, localDir):
	if not os.path.exists(localDir):
		os.makedirs(localDir)
	ftp.cwd(remoteDir)
	fileList = ftp.nlst()
	for fileName in fileList:
		localFile = os.path.join(localDir, fileName)
		newPath = '%s/%s'%(remoteDir, fileName)
		try:
			ftp.cwd(newPath)  # Try to change to the directory
			# If successful, it's a directory, so download its contents recursively
			downloadDirectory(ftp, newPath, localFile)
			ftp.cwd('..')  # Go back to the parent directory
		except ftplib.error_perm:
			# If changing directory fails, it's a file, so download it
			with open(localFile, 'wb') as f:
				ftp.retrbinary('RETR ' + newPath, f.write)

def main():
	downloadFtpFiles(ftpHost='myFTP', ftpPort=21, ftpUser='ftp', ftpPass='ftp', remoteDir='/comtrade/', localDir=exchange.comtrade.utils.folderFtp())
