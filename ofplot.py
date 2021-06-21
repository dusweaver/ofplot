import glob
import os
import sys
import shlex,subprocess
import numpy as np
from matplotlib import pyplot as plt
import PyFoam
from PyFoam.Execution.UtilityRunner import UtilityRunner


class Configuration:
    def __init__(self, target):
        self.home = os.path.abspath('.')
        if target[-1] == '/':
            self.target = target[:-1]

        else:
            self.target = target

        if os.environ['WM_PROJECT_VERSION'][0] == 'v':
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

        #name of sampling line files
        self.samplenames = []

        self.read_files(self.target)
        self.decomposed = False
        self.run_parallel('blockMesh')
        self.get_domain_size()       

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
        for file_ in all_files:
            if not os.path.isfile(file_):
                self.cases.append(file_)
        try:
            self.cases.remove(f'{target}/results')
        except:
            pass

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
        string += '}'
        string += f'start   ({value_loc[0][0]} {value_loc[1][0]} {value_loc[2][0]});' + '\n'
        string += f'end     ({value_loc[0][1]} {value_loc[1][1]} {value_loc[2][1]});' + '\n'
        string += f'fields  ({key_field});' + '\n'
        string += '#includeEtc "caseDicts/postProcessing/graphs/graph.cfg"' + '\n'

        filename = f'sample_{key_loc}_{key_field}'
        with open(case+'/system/'+filename, 'w') as f:
            f.write(string)
        self.samplenames.append(filename)

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
        self.samplenames.append(filename)

    def reconstruct_par(self, case):
        os.chdir(case)
        for time in self.times:
            for field in self.fields:
                command = ['reconstructPar', '-time', str(time), '-fields', field, '-noLagrangian', '-newTimes']
            subprocess.run(command)
        os.chdir(self.home)

    def add_time(self, value):
        self.times.append(value)
        #solution = PyFoam.RunDictionary.SolutionDirectory.SolutionDirectory(self.target)
        #print(solution.getLast())
        #if value == 'latest':
            #self.times.append(solution.getLast())
        #elif value == 'first':
            #self.times.append(solution.getFirst())
        #elif value == 'all':
            #if self.reconstructed:
                #self.times.append(solution.getTimes())
            #else:
                #self.times.append(solution.getParallelTimes())
        #elif isinstance(value, int):
            #self.times.append(value)
        #else:
            #print('Time not found: ', value)

    def add_field(self, value, col=1):
        self.fields[value] = col
    
    def add_line(self, x='length', y='length', z='length', coord='rel'):
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

    #in theory this nested parallel script should work but haven't tried because I need self.samplenames
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

    def groupByCase(self):
        pass

    def groupByTime(self):
        pass

    def groupBySample(self):
        pass

    def group_by(self):
        grouped = []
        for case in self.cases:
            for sample in self.samplenames:
                samplesplit = sample.split('_')
                samplename = samplesplit[1][:-1] + '_' + samplesplit[2] + '.xz'
                for time in self.times:
                    #print(case, sample, time)
                    #data = np.loadtxt(case + '/postProcessing/' + sample + '/' + str(time) + '/' + samplename)
                    # x, y = np.loadtxt(sample)
                    # fig, ax = plt.subplots()
                    # #ax.scatter(exp_x, exp_y_m[id_], label='EXP')
                    # ax.scatter(x, y, label='CFD')
                    # ax.legend(loc='best')
                    # os.makedirs('results', exist_ok=True)
                    # plt.savefig(f'results/{case}.png')
                    pass
        #print(data)

    def generate(self):
        for case in self.cases:
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

#Dustin notes:
# Ability to use run_parallel('blockMesh') before Configuration is done because get_domain_size() required polymesh
