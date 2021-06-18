# -*- coding: utf-8 -*-
"""
Script to iteratively run through all directories to find sampling and plot on the same figure. Can filter based on sampling time, sampling location, and case
"""

import pandas as pd
import os
import glob
import matplotlib.pyplot as plt

#For legends, -5,casename -4,postProcessingFolderName -3,samplingLocation -2,samplingTime
#This is used to specify the folder hierarchy number associated with sampling names, case names, and sampling times.
caseNames = -5
samplingNames = -3
samplingTimes = -2


def loopDirectories():

  rootdir = os.getcwd()

  print('entering directory: ',rootdir)
    

  #obtain the folder paths and make them a string to extract all words
  strPath = os.path.realpath(__file__)
  print( f"Full Path    :{strPath}" )
  nmFolders = strPath.split( os.path.sep )

  print( "List of Folders:", nmFolders )
  print( f"Program Name :{nmFolders[-1]}" )

  folderName = nmFolders[-2]
  parentFolderName = nmFolders[-3]
  grandParentFolderName = nmFolders[-4]
  greatgrandParentFolderName = nmFolders[-5]

  legendName = nmFolders[legendFix]

  print('Folder Name: ', folderName)
  print('Parent Folder Name: ', parentFolderName)
  print('Grand Parent Folder Name: ', grandParentFolderName)
  print('Great Parent Folder Name: ', greatgrandParentFolderName)

  try:
    #Reads the line_U.xy file and inputs into a pandas dataframe
    df = pd.read_csv("line_U.xy",  delimiter=r"\s+", names=['xloc', 'ux', 'uy','uz'])

  except IOError:
    print('There was an error opening the file!')
    return


  #now decide if should be plotted  by asking if this is the desired fix1 and fix2 combination
  if folderName == fix1 or parentFolderName == fix1:
    print('correct directory 1')
    if parentFolderName == fix2 or greatgrandParentFolderName == fix2:
      print('correct directory 2')
      df.plot(x = 'xloc', y = 'uy', label = legendName, ax=ax)
      ax.set_title(fix2+" at "+fix1)

  else:
    print("This isn't the folder you are looking for. Waves hand ominously")


  print('leaving directory: ',rootdir)




#=======================User Inputs ============================== 

fix2 = 'sampleAxial' # either the case or sample location name
fix1 = '200' #either the sampling location name or time step
legendFix = caseNames #caseNames #samplingNames # samplingTimes

#==========================================================


path = (os.getcwd())
directories = [os.path.abspath(x[0]) for x in os.walk(path)]
directories.remove(os.path.abspath(path))
ax = plt.gca()


for i in directories:
      os.chdir(i)         # Change working Directory
      try:
        loopDirectories()
      except Exception:
        print('you had an error in reading')
        pass

plt.show()