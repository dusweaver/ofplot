import glob
import os
import sys
import subprocess
import numpy as np
from matplotlib import pyplot as plt
import PyFoam
from PyFoam.Execution.UtilityRunner import UtilityRunner
import pickle

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
        self.times = []
        self.fields = {}
        self.lines = {}
        self.planes = {}
        self.data = {}
        self.samplenames = []
        #self.read_files(self.target)
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

    def read_files(self, target):
        all_files = glob.glob(f'{target}/*')
        print(all_files)
        for file_ in all_files:
            if not os.path.isfile(file_):
                self.cases.append(file_)
        try:
            self.cases.remove(f'{target}/results')
        except:
            pass

        print(self.cases)

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

                for i in range(len(folderNames)):
                    
                    if folderNames[-i-2] == self.target:
                        casePath =  self.target + '/' + casePath
                        break
                    else:
                        casePath =  folderNames[-i-2] + '/' + casePath 

                self.cases.append(casePath)
   

        os.chdir(self.home)

    def read_samples(self):
        all_files = glob.glob(f'{self.target}/*/system/sample_*')
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
        if len(self.domain) == 0:
            self.get_domain_size()
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

    def add_time(self, value):
        value = str(value)
        solution = PyFoam.RunDictionary.SolutionDirectory.SolutionDirectory(self.cases[0])
        if value == 'latest':
            self.times.append(solution.getLast())
        elif value == 'first':
            self.times.append(solution.getFirst())
        elif value == 'all':
            if self.reconstructed:
                self.times.append(solution.getTimes())
            else:
                self.times.append(solution.getParallelTimes())
        else:
            self.times.append(value)

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

    def post_process(self):
        args = ['parallel', self.run_parallel('postProcess'), '-time', ':::'] + self.samplenames
        subprocess.run(args)

    def post_process_test(self):
        for case in self.cases:
            os.chdir(case)
            for time in self.times:
                args = ['parallel', 'postProcess', '-time', str(time), '-func', ':::'] + self.samplenames
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
        for case in self.cases:
            times = {}
            for time in self.times:
                samples = {}
                for sample in self.samplenames:
                    samplesplit = sample.split('_')
                    if 'line' in sample:
                        samplename = samplesplit[1][:-1] + '_' + samplesplit[2] + '.xy'
                    elif 'plane' in sample:
                        samplename = samplesplit[2] + '_' + samplesplit[1][:-1] + '.raw'
                    else:
                        print('Unknown sample type')
                    data = np.loadtxt(case + '/postProcessing/' + sample + '/' + str(time) + '/' + samplename)
                    samples[sample] = data
                times[str(time)] = samples
                print(case, time, sample, data[0])
            self.data[case] = times
            # save all data as a file
            pickle.dump(self.data, open('data_dump.pkl', 'wb'))

    def plot_lines(self, group):
        ''' Plot lines grouped by conditions:
        group by 'sample', 'time' and 'case'
        '''
        os.makedirs('results', exist_ok=True)
        if group == 'sample':
            for case in self.cases:
                for time in self.times:
                    fig, ax = plt.subplots()
                    for sample in self.data[case][time]:
                        if 'plane' in sample:
                            continue
                        transposed = np.transpose(self.data[case][time][sample])
                        ax.scatter(transposed[0], transposed[1], label=sample)
                        ax.set_title(f'{case} at time {time}')
                        ax.legend(loc='best')
                        folder = case.replace('/','_')
                    plt.savefig(f'results/sample_{folder}_{sample}_{time}.png')
                    plt.close(fig)

        if group == 'time':
            for case in self.cases:
                for sample in self.samplenames:
                    if 'plane' in sample:
                        continue
                    fig, ax = plt.subplots()
                    for time in self.times:
                        transposed = np.transpose(self.data[case][time][sample])
                        ax.scatter(transposed[0], transposed[1], label=time)
                        ax.set_title(f'{case} on {sample}')
                        ax.legend(loc='best')
                        folder = case.replace('/','_')
                    plt.savefig(f'results/time_{folder}_{sample}_{time}.png')
                    plt.close(fig)

        if group == 'case':
            for sample in self.samplenames:
                if 'plane' in sample:
                    continue
                for time in self.times:
                    fig, ax = plt.subplots()
                    for case in self.cases:
                        transposed = np.transpose(self.data[case][time][sample])
                        ax.scatter(transposed[0], transposed[1], label=case)
                        ax.set_title(f'Sample {sample} at time {time}')
                        ax.legend(loc='best')
                        folder = case.replace('/','_')
                    plt.savefig(f'results/cases_{folder}_{sample}_{time}.png')
                    plt.close(fig)

    def plot_plane(self):
        ''' Plot extracted surface from plane sampling
        '''
        os.makedirs('results', exist_ok=True)
        for case in self.cases:
            for time in self.times:
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

    def generate(self):
        self.read_samples()
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
