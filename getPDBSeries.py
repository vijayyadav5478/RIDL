import os.path

class getSeries():
	# retrieve pdb codes from pdb or pdb_redo
	def __init__(self,PDBcode,pdb_redo,outputDir):
		# PDBcode is 4 letter pdb code
		# pdb_redo takes 'false', 'initial' (= from pdb_redo without refinement),
		# or 'final' (= from pdb_redo with refinement)
		self.datasetName 	= str(PDBcode).lower()
		self.outputDir 		= outputDir+self.datasetName
		self.pdbFile 		= self.datasetName+'.pdb'
		self.mmcifFile 		= self.datasetName+'-sf.cif'
		self.mtzFile 		= self.datasetName+'.mtz'

		# make directory for this dataset
		if not os.path.exists(self.outputDir):
			os.makedirs(self.outputDir)

		if pdb_redo in ('initial','final'):
			self.refineType = pdb_redo
			# downloading pdb and mtz files from pdb_redo
			downloadSuccess = self.downloadFromPDBredo()
			if downloadSuccess is False:
				print 'Cannot continue processing current PDB code files..'
				return
			self.parseRfactorFromPDB(self.pdbFile) # get Rfactor info

			# copy input files to directory
			for fileName in (self.mtzFile,self.pdbFile):
				os.system('mv {} {}/{}'.format(fileName,self.outputDir,fileName))

		elif pdb_redo == 'false':
			# downloading pdb and mmcif files from PDB
			print 'Downloading from PDB...'
			downloadSuccess = self.downloadFromPDB()
			if downloadSuccess is False:
				print 'Cannot continue processing current PDB code files..'
				return

			# copy input files to directory
			for fileName in (self.mmcifFile,self.pdbFile):
				os.system('mv {} {}/{}'.format(fileName,self.outputDir,fileName))

			print 'running cif2mtz...'
			self.runCif2MTZ()

			# run rigid body refinement refmac jobs
			print 'running rigid body refmac... 0 cycles'
			self.runREFMAC('RIGID',0)
			self.parseRfactorFromPDB('{}/{}'.format(self.outputDir,self.refmacPDBout))

			print 'running rigid body refmac... 10 cycles'
			self.runREFMAC('RIGID',10)
			self.parseRfactorFromPDB('{}/{}'.format(self.outputDir,self.refmacPDBout))

			# run restrained refinement refmac jobs
			print 'running restrained refmac... 0 cycles'
			self.runREFMAC('REST',0)
			self.parseRfactorFromPDB('{}/{}'.format(self.outputDir,self.refmacPDBout))

			print 'running restrained refmac... 10 cycles'
			self.runREFMAC('REST',10)
			self.parseRfactorFromPDB('{}/{}'.format(self.outputDir,self.refmacPDBout))

			# compare Rfactors to those in downloaded PDB header
			print 'values stated in downloaded .pdb header'
			self.parseRfactorFromPDB('{}/{}'.format(self.outputDir,self.pdbFile))

		else:
			print "pdb_redo parameter takes one of values ('false','initial','final') only"

	def downloadFromPDB(self):
		# download the coordinate pdb file and mmcif structure factor files from PDB
		os.system('curl "http://www.rcsb.org/pdb/files/{}.pdb" -o "{}"'.format((self.datasetName).upper(),self.pdbFile))
		os.system('curl "http://www.rcsb.org/pdb/files/{}" -o "{}"'.format(self.mmcifFile,self.mmcifFile))

		# check if files downloaded
		if (self.checkFileExists('{}'.format(self.pdbFile)) is False or
			self.checkFileExists('{}'.format(self.mmcifFile)) is False):
			print 'One or more files failed to download successfully from PDB'
			return False
		else:
			return True

	def downloadFromPDBredo(self):
		# download the coordinate pdb file and mtz file generated by pdb_redo to initially attempt 
		# to recalculate R(-free) values stated in header of pdb file from PDB (this structure is 
		# after 0 cycles of rigid body refinement and pdb curation)
		pdb = self.datasetName
		if self.refineType == 'final': 
			refType = 'final' # specify correct file to download
			fileFmt = ''
		else:
			refType = '0cyc'
			fileFmt = '.gz'

		for fileType in ('pdb','mtz'):
			print 'Downloading {} file..'.format(fileType)
			os.system('curl "www.cmbi.ru.nl/pdb_redo/{}/{}/{}_{}.{}{}" -o "{}.{}{}"'.format(pdb[1:3],pdb,pdb,refType,fileType,fileFmt,pdb,fileType,fileFmt))
			
			# check if file downloaded successfully
			if self.checkFileExists('{}.{}{}'.format(pdb,fileType,fileFmt)) is False:
				print 'Failed to download {} file successfully from PDB'.format(fileType)
				return False
			else:
				if self.refineType == 'initial':
					os.system('gunzip {}.{}.gz -f'.format(pdb,fileType))

		# want to change label names in mtz file to make unique to pdb code
		self.changePDBredoMtzLabelInfo(pdb)
		# os.system('rm -f {}.mtz'.format(pdb))
		os.system('mv -f {}_editedLabels.mtz {}.mtz'.format(pdb,pdb))
		return True

	def changePDBredoMtzLabelInfo(self,pdbcode):
		# default mtz column labels are FP and SIGFP. Wish to append pdb code to these to make them unique
		# (important later on for CAD merging of mtz files)
		self.jobName = 'sftools'

		# run sftools from comman line
		self.commandInput1 = '/Applications/ccp4-6.5/bin/sftools'
		self.commandInput2 = 'mode batch\n'+\
							 'read {}.mtz mtz\n'.format(pdbcode)+\
							 'set types col "FP"\n'+\
							 'F\n'+\
							 'set labels col "FP"\n'+\
							 '"FP_{}"\n'.format(pdbcode)+\
							 'set types col "SIGFP"\n'+\
							 'Q\n'+\
							 'set labels col "SIGFP"\n'+\
							 '"SIGFP_{}"\n'.format(pdbcode)+\
							 'set types col "PHIC_ALL"\n'+\
							 'P\n'+\
							 'set labels col "PHIC_ALL"\n'+\
							 '"PHIC_{}"\n'.format(pdbcode)+\
							 'set types col "FOM"\n'+\
							 'W\n'+\
							 'set labels col "FOM"\n'+\
							 '"FOM_{}"\n'.format(pdbcode)+\
							 'set types col "FREE"\n'+\
							 'I\n'+\
							 'set labels col "FREE"\n'+\
							 '"FreeR_flag"\n'.format(pdbcode)+\
							 'write {}_editedLabels.mtz mtz\n'.format(pdbcode)+\
							 'EXIT\n'+\
							 'YES'
		self.outputLogfile = 'sftoolslogfile.txt'
		
		# run sftools job
		self.runCCP4program()

	def runCif2MTZ(self):
		# run cif2mtz job to convert mmcif structure factor file to mmcif file
		self.jobName = 'cif2mtz'

		# check if input mmcif file exist
		if self.checkFileExists('{}/{}'.format(self.outputDir,self.mmcifFile)) is False:			
			return											  

		# run Cif2Mtz from command line
		self.commandInput1 = '/Applications/ccp4-6.5/bin/cif2mtz '+\
							 'HKLIN {}/{} '.format(self.outputDir,self.mmcifFile)+\
						     'HKLOUT {}/{} '.format(self.outputDir,self.mtzFile)
		self.commandInput2 = 'END'
		self.outputLogfile = 'Cif2Mtzlogfile.txt'

		# run Cif2Mtz job
		self.runCCP4program()

	def runREFMAC(self,refineType,numCycles):
		# run n = 'numCycles' cycles of 'refineType' refinement in refmac to get phases
		self.jobName = 'refmac'
		if refineType == 'RIGID':
			bref = 'over'
			numCycString = 'rigid ncycle {}'.format(numCycles) 
		elif refineType == 'REST':
			bref = 'ISOT'
			numCycString = 'ncyc {}'.format(numCycles) 
		else: 
			print 'Unreadable refinement type.. selecting 0 cycles of rigid body refinement'
			bref = 'over'
			numCycString = 'rigid ncycle 0'
			refineType = 'RIGID'
			numCycles = 0

		# make a refinement type id to append to file names from current job
		fileInd = '_{}_{}cycles'.format(refineType,numCycles)

		# check if input files exist
		if (self.checkFileExists('{}/{}'.format(self.outputDir,self.pdbFile)) is False or
			self.checkFileExists('{}/{}'.format(self.outputDir,self.mtzFile)) is False):			
			return	

		self.refmacPDBout = '{}_refmac{}.pdb'.format(self.datasetName,fileInd)
		self.refmacMTZout = '{}_refmac{}.mtz'.format(self.datasetName,fileInd)
		self.refmacLIBout = '{}_refmac{}.cif'.format(self.datasetName,fileInd)

		self.commandInput1 = 'refmac5 '+\
							 'XYZIN {}/{} '.format(self.outputDir,self.pdbFile)+\
							 'XYZOUT {}/{} '.format(self.outputDir,self.refmacPDBout)+\
							 'HKLIN {}/{} '.format(self.outputDir,self.mtzFile)+\
						     'HKLOUT {}/{} '.format(self.outputDir,self.refmacMTZout)+\
							 'LIBOUT {}/{} '.format(self.outputDir,self.refmacLIBout)
		self.commandInput2   = 	'make check NONE\n'+\
								'make -\n'+\
								'    hydrogen ALL -\n'+\
								'     hout NO -\n'+\
								'     peptide NO -\n'+\
								'    cispeptide YES -\n'+\
								'    ssbridge YES -\n'+\
								'    symmetry YES -\n'+\
								'    sugar YES -\n'+\
								'    connectivity NO -\n'+\
								'    link NO\n'+\
								'refi -\n'+\
								'    type {} -\n'.format(refineType)+\
								'    resi MLKF -\n'+\
								'    meth CGMAT -\n'+\
								'    bref {}\n'.format(bref)+\
								'{}\n'.format(numCycString)+\
								'scal -\n'+\
								'    type SIMP -\n'+\
								'    LSSC -\n'+\
								'    ANISO -\n'+\
								'    EXPE\n'+\
								'solvent YES\n'+\
								'weight -\n'+\
								'    AUTO\n'+\
								'monitor MEDIUM -\n'+\
								'    torsion 10.0 -\n'+\
								'    distance 10.0 -\n'+\
								'    angle 10.0 -\n'+\
								'    plane 10.0 -\n'+\
								'    chiral 10.0 -\n'+\
								'    bfactor 10.0 -\n'+\
								'    bsphere 10.0 -\n'+\
								'    rbond 10.0 -\n'+\
								'    ncsr 10.0\n'+\
								'labin  FP=FP SIGFP=SIGFP -\n'+\
								'   FREE=FREE\n'+\
								'labout  FC=FC FWT=FWT PHIC=PHIC PHWT=PHWT DELFWT=DELFWT PHDELWT=PHDELWT FOM=FOM\n'+\
								'PNAME {}\n'.format(self.datasetName)+\
								'DNAME 1\n'+\
								'RSIZE 80\n'+\
								'EXTERNAL WEIGHT SCALE 10.0\n'+\
								'EXTERNAL USE MAIN\n'+\
								'EXTERNAL DMAX 4.2\n'+\
								'END'
		self.outputLogfile = 'REFMAClogfile{}.txt'.format(fileInd)

		# run REFMAC job
		self.runCCP4program()

	def runCCP4program(self):
		# generic method to run a ccp4 program on command line

		# write commandInput2 to txt file
		textinput = open('{}/{}inputfile.txt'.format(self.outputDir,self.jobName),'w')
		textinput.write(self.commandInput2)
		textinput.close()
		# run ccp4 program job
		os.system('{} < {}/{}inputfile.txt > {}/{}'.format(self.commandInput1,
												   self.outputDir,self.jobName,
												   self.outputDir,self.outputLogfile))

	def checkFileExists(self,filename):
		# method to check if file exists
		if os.path.isfile(filename) is False:
			ErrorString = 'File {} not found'.format(filename)
			print ErrorString
			return False
		else: 
			return True

	def parseRfactorFromPDB(self,fileName):
		# read a pdb file and print the Rwork and Rfree values out
		RvalFlag = 'R VALUE     (WORKING + TEST SET) :'
		RfreeFlag = 'FREE R VALUE                     :'
		fileOpen = open(fileName,'r')
		for line in fileOpen.readlines():
			if RvalFlag in line:
				Rvalue = float(line.split(RvalFlag)[1])
			elif RfreeFlag in line:
				Rfree = float(line.split(RfreeFlag)[1])
		print '---------------------------------------------'
		print 'Rfactor: {}\nRfree: {}'.format(Rvalue,Rfree)
		print '---------------------------------------------'

