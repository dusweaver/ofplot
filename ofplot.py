import glob
import os
import sys
import subprocess
import numpy as np
from matplotlib import pyplot as plt
import PyFoam
from PyFoam.Execution.UtilityRunner import UtilityRunner
import pickle
import multiprocessing

import re
import time
import psutil 
from cycler import cycler
import pandas as pd

from collections import defaultdict

import itertools

import json



import os.path



class Configuration:
    def __init__(self, target):
        self.home = os.path.abspath('.')
        if target[-1] == '/':
            self.target = target[:-1]
        else:
            self.target = target

        if os.environ['WM_PROJECT_VERSION'][0] == 'v' or os.environ['WM_PROJECT_VERSION'][0] == '5':
            self.version = 'COM'
        else:
            self.version = 'ORG'
        self.files = []
        self.cases = []
        self.domain = []
        self.times = {}

        self.fields = {}
        self.lines = {}
        self.planes = {}
        self.data = {}
        self.samplenames = []
        #self.read_files(self.target)
        self.decomposed = True
        self.read_files_independent(self.target)     

    def get_domain_size(self):
        os.chdir(self.cases[0])
        output = subprocess.check_output(['checkMesh'], encoding='utf-8')
        for line in output.splitlines():
            if 'bounding box' in line:
                a = line.replace('(','').replace(')','').split('box')[-1].split()
        self.domain = [[float(a[0]), float(a[1]), float(a[2])],
                       [float(a[3]), float(a[4]), float(a[5])]]
        os.chdir(self.home)


    def read_files_independent(self, target):
        os.chdir(self.target)
        path = (os.getcwd())

        #gather all directories 
        directories = [os.path.abspath(x[0]) for x in os.walk(path)]
        directories.remove(os.path.abspath(path))

        for directory in directories:
            #Check if controlDict exists in the directory
            caseCheck = directory + "/system/controlDict"            
            if os.path.isfile(caseCheck):
                #separate the directory paths into all folder names and then concantenate to the full case path
                stringPath = os.path.realpath(directory)
                folderNames = stringPath.split( os.path.sep )

                casePath = folderNames[-1]
                #last parent folder for if criteria 
                end_parent = self.target.split("/")[-1]

                for i in range(len(folderNames)):
                    if folderNames[-i-2] == end_parent:
                        casePath =  self.target + '/' + casePath
                        break
                    else:
                        casePath =  folderNames[-i-2] + '/' + casePath 

                self.cases.append(casePath)
   
        print('the case names are: ', self.cases)
        os.chdir(self.home)

    def read_samples(self):
        for case in self.cases:
            all_files = glob.glob(f'{case}/system/sample*')
            for file_ in all_files:
                if os.path.isfile(file_):
                    filename = file_.split('/')[-1]
                    self.samplenames.append(filename)
            # remove repeated sample names
        self.samplenames = list(set(self.samplenames))

    def create_sample_line(self, case, key_loc, value_loc, key_field):  
        string  = f'//sample{key_loc}.cfg' + '\n'
        string += 'interpolationScheme cellPointFace;' + '\n'
        string += 'setFormat   raw;' + '\n'
        string += 'setConfig' + '\n'
        string += '{' + '\n'
        if self.version == 'COM':
            string += 'type    uniform;' + '\n'
        else:
            string += 'type    lineUniform;' + '\n'
        string += 'axis    distance;' + '\n'
        string += 'nPoints 100;' + '\n'
        string += '}' + '\n'
        string += f'start   ({value_loc[0][0]} {value_loc[1][0]} {value_loc[2][0]});' + '\n'
        string += f'end     ({value_loc[0][1]} {value_loc[1][1]} {value_loc[2][1]});' + '\n'
        string += f'fields  ({key_field});' + '\n'
        string += '#includeEtc "caseDicts/postProcessing/graphs/graph.cfg"' + '\n'

        filename = f'sample_{key_loc}_{key_field}'
        with open(case+'/system/'+filename, 'w') as f:
            f.write(string)

    def create_sample_plane(self, case, key_loc, value_loc, key_field):
        string  = f'//sample{key_loc}.cfg' + '\n'
        string += f'interpolationScheme cell;' + '\n'
        string += f'surfaceFormat raw;' + '\n'
        string += f'type surfaces;' + '\n'
        string += f'fields  ({key_field});' + '\n'
        string += f'surfaces' + '\n'
        string += '{' + '\n'
        string += f'    plane' + '\n'
        string += '    {' + '\n'
        string += f'        type plane;' + '\n'
        string += f'        planeType pointAndNormal;' + '\n'
        string += f'        pointAndNormalDict' + '\n'
        string += '        {' + '\n'
        string += f'            point   ({value_loc[0][0]} {value_loc[1][0]} {value_loc[2][0]});' + '\n'
        string += f'            normal     ({value_loc[0][1]} {value_loc[1][1]} {value_loc[2][1]});' + '\n'
        string += '         }' + '\n'
        string += '    }' + '\n'
        string += '};' + '\n'

        filename = f'sample_{key_loc}_{key_field}'
        with open(case+'/system/'+filename, 'w') as f:
            f.write(string)

    def reconstruct_par(self, case):
        os.chdir(case)
        for time in self.times:
            for field in self.fields:
                command = ['reconstructPar', '-time', str(time), '-fields', field, '-noLagrangian', '-newTimes']
            subprocess.run(command)
        os.chdir(self.home)

    def add_time(self, value, start_from = 0):
        value = str(value)
        for case in self.cases:
            solution = PyFoam.RunDictionary.SolutionDirectory.SolutionDirectory(case)
            if start_from == 0:
                if value == 'latest':
                    self.times[case] = solution.getLast()
                elif value == 'first':
                    self.times[case] = solution.getFirst()
                elif value == 'all':
                    if self.reconstructed:
                        self.times[case] = solution.getTimes()
                    else:
                        self.times[case] = solution.getParallelTimes()
                else:
                    self.times[case] = value
            #ugly code for filtering out a range of values starting from start_from and ending at the last value.        
            else:
                if self.reconstructed:
                    self.times[case] = solution.getTimes()
                else:
                    self.times[case] = solution.getParallelTimes()
                try:
                    #change the dictornary to an integer list filter out the values wanted and then conver to string list

                    times = list(map(str, self.times[case]))
                    times = [x for x in times if x >= start_from]
                    # for time in times:
                    #     times = str(times)
                    print("the case is:", case, " with filtered times of: ", times)
                    self.times[case] = times 
                #transient times with testing for if the time is integer and setting to that value.
                except Exception:
                    timesTemp = []
                    #maps float onto the list of strings and checkes if and changes to integer for floating digits.
                    #i.e. if 5.0 then int(5.0) = 5 (this is to match OpenFOAM notation when outputing  time folders)
                    times = list(map(float, self.times[case]))
                    times = [x for x in times if x >= start_from]
                    for time in times:
                        if time.is_integer():
                            time = int(time)
                        timesTemp.append(str(time))
                    times = timesTemp

                    print("the case is:", case, " with filtered times of: ", times)
                    self.times[case] = times       
    
        print("times added RunDictionary: ", self.times)

    def add_field(self, value, col=1):
        self.fields[value] = col
    
    def add_line(self, x='length', y='length', z='length', coord='rel'):

        if not len(self.domain):
            self.get_domain_size()

        current = f'line{len(self.lines)}'
        if coord == 'rel':
            x, y, z = self.convert_relative(x, y, z)

        if not isinstance(x, str) and not isinstance(y, str):
            self.lines[current] = [[x, x],[y, y],[self.domain[0][2], self.domain[1][2]]]
        elif not isinstance(x, str) and not isinstance(z, str):
            self.lines[current] = [[x, x],[self.domain[0][1], self.domain[1][1]],[z, z]]
        elif not isinstance(y, str) and not isinstance(z, str):
            self.lines[current] = [[self.domain[0][0], self.domain[1][0]],[y, y],[z, z]]
        else:
            print(f'Bad location definition: {x} {y} {z}')

    def add_plane(self, x, y, z, normal, coord='rel'):
        if not len(self.domain):
            self.get_domain_size()

        current = f'plane{len(self.planes)}'

        if coord == 'rel':
            x, y, z = self.convert_relative(x, y, z)

        if normal == 'x':
            normal = [1, 0, 0]
        elif normal == 'y':
            normal = [0, 1, 0]
        elif normal == 'z':
            normal = [0, 0, 1]
        else:
            print('Please define normal as x, y or z')
        self.planes[current] = [[x, normal[0]], [y, normal[1]], [z,normal[2]]]

    def convert_relative(self, x, y, z):
        if not isinstance(x, str):
            x = x * (self.domain[1][0] - self.domain[0][0])
        if not isinstance(y, str):
            y = y * (self.domain[1][1] - self.domain[0][1])
        if not isinstance(z, str):
            z = z * (self.domain[1][2] - self.domain[0][2])
        return x, y, z

    def run_parallel(self, command):
        args = ['parallel', command, '-case', ':::'] + self.cases
        subprocess.run(args)

    def post_process(self,timed=all,which_parallel='sample_names'):
        for case in self.cases:
            print("running postProcess for case: ", case)
            os.chdir(case)
            if not self.times[case]:
                print("no times added postProcessing all times...")
                args = ['parallel', 'postProcess', '-func', ':::'] + self.samplenames
                subprocess.run(args)
            else:
                if which_parallel == 'sample_names':
                    print("post processing for times in parallel (samples are sequentially solved).....")
                    for samplename in self.samplenames:
                        args = ['parallel', 'postProcess', '-func', str(samplename), '-time', ':::'] + self.times[case] 
                        print(args)
                        subprocess.run(args)
                else:
                    print("post processing for samples in parallel (times are sequentially solved)......")
                    for time in self.times[case]:
                        args = ['parallel', 'postProcess', '-func', str(time), '-time', ':::'] + self.samplenames
                        subprocess.run(args)

            os.chdir(self.home)


    def run_func_parallel(self,function):
        for case in self.cases:
            print("running function", function, "for case:", case)
            os.chdir(case)
            args = ['parallel', 'postProcess', '-func', str(function), '-time', ':::'] + self.times[case] 
            subprocess.run(args)
            os.chdir(self.home)
        
    def post_process_single(self):
        for case in self.cases:
            os.chdir(case)
            for sample in self.samplenames:
                for time in self.times:
                    args = ['postProcess', '-func', sample, '-time', str(time)]
                    subprocess.run(args)
            os.chdir(self.home)

    def group_data(self):
        print("grouping data")
        for case in self.cases:
            samples = {}
            try: 
                print("reading sampling files ",self.samplenames, " from case: ", case)
                for sample in self.samplenames:
                    times = {}
                    for time in self.times[case]:
                        samplesplit = sample.split('_')
                        print(samplesplit)
                        #this requires that the names be in a particular format.
                        if 'line' in sample:
                            samplename = 'line_' + samplesplit[-1] + '.xy'
                            print(samplename)
                        elif 'plane' in sample:
                            samplename = samplesplit[2] + '_' + samplesplit[1][:-1] + '.raw'
                        else:
                            print('Unknown sample type')
                        stringThing = case + '/postProcessing/' + sample + '/' + str(time) + '/' + samplename
                        print("the stringThing is: ", stringThing)
                        try:
                            data = np.loadtxt(stringThing)
                        except Exception:
                            print("there was an error loading the sampling text file at time:", time)

                        times[str(time)] = data
                    samples[sample] = times
                    #print(case, time, sample, data[0])

                self.data[case] = samples
            except Exception:
                print("there was an error reading one of your data from case:", case)
            # save all data as a file
            print("the keys to the data is:", self.data[case].keys())
            pickle.dump(self.data, open('data_dump.pkl', 'wb'))

    def plot_lines_single(self,sample, group, experimental_file = 'None', folder_name = 'results', pickle_input_file = 'data_dump.pkl', experimental_file2='None', **plt_kwargs):
        ''' Plot lines grouped by conditions:
        group by 'sample', 'time' and 'case'

        '''

        pickle_file = open(pickle_input_file, "rb")
        data = pickle.load(pickle_file)
        os.makedirs(f'{folder_name}', exist_ok=True)


        if group == 'time':
            for case in data.keys():
                fig, ax = plt.subplots()
                for time in data[case][sample].keys():

                    transposed = np.transpose(data[case][sample][time])
                    ax.plot(transposed[0], transposed[1], label=time, **plt_kwargs)

                    ax.set_title(f'{case} on {sample}')

                if experimental_file != 'None':
                    print("adding experimental data to the plot")

                    data_experimental = np.loadtxt( experimental_file )
                    x_experimental = np.transpose(data_experimental)[0]
                    y_experimental = np.transpose(data_experimental)[1]
                    ax.scatter(x_experimental,y_experimental,marker= 'x', color='black',label=experimental_file, **plt_kwargs)
                    ax.set_title(f'experimental file: {experimental_file}')

                if experimental_file2 != 'None':
                    print("adding second experimental data to the plot")

                    data_experimental2 = np.loadtxt( experimental_file2 )
                    x_experimental2 = np.transpose(data_experimental2)[0]
                    y_experimental2 = np.transpose(data_experimental2)[1]
                    ax.scatter(x_experimental2,y_experimental2,marker= 'x', color='blue',label=experimental_file2, **plt_kwargs)
                    ax.set_title(f'experimental file: {experimental_file2}')

                ax.legend(loc='best')
                folder = case.replace('/','_')


                plt.savefig(f'{folder_name}/time_{folder}_{sample}_{time}.png')
                plt.close(fig)

        #put all the samplenames in a list so that we can iterate through them. This is assuming that all cases have the same samples
        #which is required anyway if we want to group by case....

        if group == 'case':
            # for time in self.times[case]:
            fig, ax = plt.subplots()

            for case in data.keys():
                latestTime = 0

                #if this is a steady state case then extract the times as an integer list, otherwise as float list
                try:
                    times = list(map(int, data[case][sample].keys()))
                except Exception:
                    timesTemp = []
                    times = list(map(float, data[case][sample].keys()))
                    #needs to check for time = 5.0, for example, and return as '5' if that is the case.
                    for time in times:
                        if time.is_integer():
                            time = int(time)
                        timesTemp.append(str(time))
                    times = timesTemp

                latestTime = max(times)

                transposed = np.transpose(data[case][sample][str(latestTime)])
                ax.plot(transposed[0], transposed[1], label=f'{case} t={latestTime}', **plt_kwargs)

                ax.set_title(f'Sample {sample} at latestTime')


            if experimental_file != 'None':
                print("adding experimental data to the plot")

                data_experimental = np.loadtxt( experimental_file )
                x_experimental = np.transpose(data_experimental)[0]
                y_experimental = np.transpose(data_experimental)[1]
                ax.scatter(x_experimental,y_experimental,marker= 'x', color='black',label=experimental_file, **plt_kwargs)
                ax.set_title(f'experimental file: {experimental_file}')
                
            if experimental_file2 != 'None':
                print("adding second experimental data to the plot")

                data_experimental2 = np.loadtxt( experimental_file2 )
                x_experimental2 = np.transpose(data_experimental2)[0]
                y_experimental2 = np.transpose(data_experimental2)[1]
                ax.scatter(x_experimental2,y_experimental2,marker= 'x', color='blue',label=experimental_file2, **plt_kwargs)
                ax.set_title(f'experimental file: {experimental_file2}')


            ax.legend(loc='best')
            folder = case.replace('/','_')
            plt.savefig(f'{folder_name}/cases_{folder}_{sample}_{latestTime}.png')
            plt.cla()
            plt.close(fig)

    def plot_plane(self):
        ''' Plot extracted surface from plane sampling
        '''
        os.makedirs('results', exist_ok=True)
        for case in self.cases:
            for time in self.times[case]:
                fig, ax = plt.subplots()
                for sample in self.data[case][time]:
                    if 'line' in sample:
                        continue
                    results = self.extract_interface(self.data[case][time][sample])
                    ax.scatter(results[0], results[1], label=sample)
                    ax.set_title(f'{case} at time {time}')
                    ax.legend(loc='best')
                    folder = case.replace('/','_')
                plt.savefig(f'results/sample_{folder}_{sample}_{time}.png')
                plt.close(fig)

    def extract_interface(self, data):
        #data = np.loadtxt(sys.argv[1])
        dataT = np.transpose(data)
        print(dataT)
        dataT = data
        # get uniques
        x = np.unique(dataT[0])
        z = np.unique(dataT[2])

        interface  = 0.5

        results = []

        for i in x:
            idx = np.where(dataT[0] == i)
            values_z = dataT[2][idx]
            #sorted_z = np.argsort(values_z)
            values_field = dataT[3][idx]
            closest = np.argmin(np.abs(values_field-interface))
            results.append([i, values_z[closest]])
        print(results)
        return results

    def run_cases(self, solver , max_processors = 0):

        #checks solver name to determine if it is a CFDEM solver or not and then sets a flag
        if re.search(r'cfdemSolver',solver):
            print("running cases using the cfdem solver: ", solver)
            cfdemFlag = True
        else:
            print("running cases using OpenFoam solver: ", solver)
            cfdemFlag =False

        #checks if user specified max_processors or not.
        if max_processors ==0:
            num_cpus_system = multiprocessing.cpu_count()
            print("no user specified max cpus set. setting to sensed cpu count:", num_cpus_system)
        else:
            
            num_cpus_system = max_processors
            print("setting maximum cpus to user specified value: ", num_cpus_system)

        i=0
        num_cpus_avail = num_cpus_system
        print("number of cases",len(self.cases))
        while i < len(self.cases):
            os.chdir(self.home)

            #capture the number of processes using the command cfdemSolver and output to result.stdout and result.stderr
            #note this also includes the process running itself which is 2 processes
            # linux_command = "ps -aF | grep ' " + str(solver) + " ' | wc -l"
            # result = subprocess.run(linux_command, shell=True,capture_output=True)
            # #filter out only the digits using re
            # try:
            #     num_cpus_avail = num_cpus_system - int(re.sub('\D', '', str(result.stdout)))+2
            # except Exception:
            #     print("was unable to convert the bytes data output to a string")

            # #get the number of cpus used by decomposeParDict

            try:
                num_cpus_case = self.read_value_from_file(self.cases[i],'system/decomposeParDict', 'numberOfSubdomains')
                # print('number of cpus for the case', num_cpus_case)
            except Exception:
                print("no decomposeParDict file found, setting number of cpus for the case to 1 (num_cpus_case=1)");
                num_cpus_case = 1;

        
            
            if num_cpus_case <= num_cpus_avail:
                print('\n\nnumber of cpus available', num_cpus_avail)
                print('number of required for case', num_cpus_case)
                print("we have enough cpus for case: ", self.cases[i])
                print('opening process for case: ',self.cases[i])
                #go up a directory to CFDEM case
                os.chdir(self.home)
                os.chdir(self.cases[i])

                if cfdemFlag:
                    os.chdir("..")
                    args = ['bash', 'Allrun.sh']
                elif num_cpus_case != 1: 
                    args = ['mpirun', '-np', str(num_cpus_case), solver, '-parallel']
                else:
                    args = [solver]


                print('running the case in: ', os.getcwd())

                #this if statement is used so that the code doesn't continue on when it gets to the last case. using "call"
                #waits for the process to finish
                if i == len(self.cases)-1:
                    print('this is the last case....')
                    subprocess.call(args,stdout=open('stdout.txt', 'wb'), stderr=open('stderr.txt', 'wb'))
                else:
                    subprocess.Popen(args,stdout=open('stdout.txt', 'wb'), stderr=open('stderr.txt', 'wb'))

                time.sleep(1)
                i=i+1
                print('\n')
            else:
                print ('not enough cpus for case:', self.cases[i], 'needed:',num_cpus_case, 'avail:',num_cpus_avail, end="\r")
                #print('.', end='', flush=True)
                time.sleep(5)
                pass
            num_cpus_avail = num_cpus_avail - num_cpus_case
            
            os.chdir(self.home)


    #This function is created to read the a value from a link starting with a string
    #case: Case path from self.home
    #file: file path from case folder i.e. system/decomposePar
    #starts_with: what the line in the file starts with (a string)
    #colume_number: once the line is determined from start_wish the code splits the line into columns

    def read_value_from_file(self,case,file,starts_with, column_number = 1,log = 0):

        if log == 1:
            print('\nReading value from file')
            print('case:',case)
            print('file:',file)
            print('starting with:',starts_with)
            print('value number',column_number)
        os.chdir(case)

        try:
            #read all lines in the specified file
            lines = [line for line in open(file,'r')]
            #run through all the lines and if it starts with a phrase then something happens
            for line in lines:
                if line.startswith(starts_with):
                    if log == 1:
                        print('\nthe recognized line is: ', line)
                    try:
                        value = line.split()[column_number]
                        #filter out only the digits using re
                        value = int(re.sub('\D', '', value))
                        if log ==1:
                            print('the returned value is: ',value)
                        return value
                    except Exception:
                        print('there was an error reading the value in column:',column_number)
            os.chdir(self.home)         
        except AttributeError:
            print('There was an error in reading the file or string to replace value for case: ', case)
            os.chdir(self.home)
            pass

        os.chdir(self.home)



    def run_command_allcases(self, command):
        print(command)
        for case in self.cases:
            os.chdir(case)
            subprocess.run(command,shell=True)
            os.chdir(self.home)

    def run_OFCase_serial(self, solver = 'pimpleFoam', proc=50):

        for case in self.cases:
            os.chdir(case)
            print(os.getcwd())
            args = ['mpirun', '-np', str(proc) , 'pimpleFoam', '-parallel']
            subprocess.run(args)
            os.chdir(self.home)
        os.chdir(self.home)


    def run_OFCase_parallel(self, solver = 'pimpleFoam', proc=2, numSplits = 2):
        cases_parallel = []
        i = 0
        numSplitsTemp = numSplits
        print("the number of cases: ", len(self.cases))
        print("\nThe cases are: ", ' '.join(self.cases))
        print("\n")
        while i < len(self.cases) - 1:
            numSplits = numSplitsTemp
            while numSplits > 1:
                
                print("running case: ", self.cases[i])
                try:
                    os.chdir(self.home)
                    os.chdir(self.cases[i])
                    subprocess.Popen('mpirun -np ' + str(proc) +' '+ str(solver) + ' -parallel |tee logThatShit.txt', shell=True, stdout=open('stdout.txt', 'wb'), stderr=open('stderr.txt', 'wb'))
                except:
                    print('There was an error in running initial splits')
                i=i+1
                numSplits = numSplits-1

            print("calling last case of set: ", self.cases[i])
            try:
                os.chdir(self.home)
                os.chdir(self.cases[i])
                subprocess.call('mpirun -np ' + str(proc) + ' ' + str(solver)+ ' -parallel |tee logThatShit.txt', shell=True, stdout=open('stdout.txt', 'wb'), stderr=open('stderr.txt', 'wb'))
                i=i+1
                print("moving on to next set of cases\n")
            except:
                print('there was an error in running the last split')
            
            cases_parallel.clear()
            os.chdir(self.home)



#not used but just here for an example

    # def fit_function_out(x,fitting_expression,fitted_variables):

    #   math_dict = {'exp':np.exp, 'sin': np.sin}
    #   fitted_variables['x'] = x
     
    #   return eval(fitting_expression,fitted_variables,math_dict)
 

    #by default will input data_dump.pkl and then output data_dump_norm.pkl
    def normalize_data(self,json_file_name):

        with open(json_file_name) as f:
            json_inputs = json.load(f)
            

        #Gather all the json inputs================================
        norm_function = json_inputs['normalization_functions']
        norm_value_function = json_inputs['norm_values']

        sample_names = json_inputs["target_and_read_samples"][0]
        target_sample = list(sample_names.keys())[0]
        if len(list(sample_names.keys())) ==1:
            print('Duplicate sample names. Setting read sample to be equal to target sample')
            read_sample = list(sample_names.keys())[0]
        else:
            read_sample = list(sample_names.keys())[1]

        target_sample_col_nums = sample_names[target_sample].split(",")
        read_sample_col_nums = sample_names[read_sample].split(",")

        pickle_input_file = json_inputs["pickle_input_file"]
        pickle_output_file = json_inputs["pickle_output_file"]
        #==========================================================

        norm_functions = norm_function.split(",")
        norm_value_functions = norm_value_function.split(",")


        print("the normalization function is:", norm_functions)
        print("the norm value function is:", norm_value_functions)
        print("the target sample is:", target_sample)
        print("the read sample is", read_sample)

        
        pickle_file = open(pickle_input_file, "rb")
        data = pickle.load(pickle_file)

        for i in range(len(norm_value_functions)):
            print(i)
            for case in data.keys():    
                for sample in data[case].keys():
                    if sample == target_sample:
                        for time in data[case][sample].keys():

                            #now iterating through samples to find the sample to use for normalizing at time t=time
                            for sample_norm in data[case].keys():
                                if sample_norm == read_sample:

                                    np_norm_data = list(data[case][sample_norm][time])
                                    df = pd.DataFrame(data=np_norm_data)

                                    #create a list for the desired normalization variable.
                                    var = df[df.columns[int(read_sample_col_nums[i])]].tolist()
                                   
                                    #applies specified specified function to "var" 
                                    norm_value = eval(norm_value_functions[i])

                            np_data = list(data[case][sample][time])
                            df = pd.DataFrame(data=np_data)

                            #This is where normalization occurs
                            eval_variables = {'norm_value':norm_value}

                            df[df.columns[int(target_sample_col_nums[i])]]=df[df.columns[int(target_sample_col_nums[i])]].apply(lambda x: eval(norm_functions[i],eval_variables,{'x':x}))

                            data[case][sample][time] = df.values.tolist()

        pickle.dump(data, open(pickle_output_file, 'wb'))
                    

    def test_case_convergence(self,case_name):
        pass



    def generate(self):
        self.read_samples()
        print('the sample names are:', self.samplenames)
        for case in self.cases:
            # Reconstruct parallel cases
            if not self.decomposed:
                self.reconstruct_par(case)
            # Create sample lines
            for key_loc, value_loc in self.lines.items():
                for key_field in self.fields:
                    self.create_sample_line(case, key_loc, value_loc, key_field)
            # Create sample planes
            for key_loc, value_loc in self.planes.items():
                for key_field in self.fields:
                    self.create_sample_plane(case, key_loc, value_loc, key_field)
        print('Sample files generated')