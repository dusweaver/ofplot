import glob
import os
import sys
import shlex,subprocess

import PyFoam
from PyFoam.Execution.UtilityRunner import UtilityRunner

class Configuration:
    def __init__(self, target):
        self.home = os.path.abspath('.')
        if target[-1] == '/':
            self.target = target[:-1]

        else:
            self.target = target

        self.files = []
        self.cases = []
        self.domain = []
        self.times = []
        self.fields = {}
        self.locations = {}

        #name of sampling line files
        self.samplenames={}

        self.read_files(self.target)
        self.decomposed = False
        self.get_domain_size()       

    def get_domain_size(self):
        os.chdir(self.cases[0])
        output = subprocess.check_output(['checkMesh'], encoding='utf-8')
        for line in output.splitlines():
            if 'bounding box' in line:
                a = line.replace('(','').replace(')','').split('box')[-1].split()
        self.domain = [[a[0], a[1], a[2]],[a[3], a[4], a[5]]]
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
        print(self.cases)

    def create_sample_cfg(self, case):
        os.chdir(self.home)
        string  = '//sampleDict.cfg' + '\n'
        string += 'interpolationScheme cellPointFace;' + '\n'
        string += 'setFormat   raw;' + '\n'
        string += 'setConfig' + '\n'
        string += '{' + '\n'
        string += 'type    uniform;' + '\n'
        string += 'axis    distance;' + '\n'
        string += 'nPoints 100;' + '\n'
        string += '}'
        with open(case+'/system/sampleDict.cfg', 'w') as f:
            f.write(string)

    def create_sample_line(self, case, key_loc, value_loc, key_field):
        string  = f'//sample{key_loc}.cfg' + '\n'
        string += f'start   ({value_loc[0][0]} {value_loc[1][0]} {value_loc[2][0]});' + '\n'
        string += f'end     ({value_loc[0][1]} {value_loc[1][1]} {value_loc[2][1]});' + '\n'
        string += f'fields  ({key_field});' + '\n'
        string += '#include "sampleDict.cfg"' + '\n'
        string += 'setConfig { type uniform; }' + '\n'
        string += '#includeEtc "caseDicts/postProcessing/graphs/graph.cfg"' + '\n'
        with open(case+f'/system/sample_{key_loc}_{key_field}', 'w') as f:
            f.write(string)

    def reconstruct_par(self, case):
        os.chdir(case)
        for time in self.times:
            for field in self.fields:
                command = ['reconstructPar', '-time', str(time), '-fields', field, '-noLagrangian', '-newTimes']
            subprocess.run(command)
        os.chdir(self.home)

    def add_time(self, value):
        solution = PyFoam.RunDictionary.SolutionDirectory.SolutionDirectory(self.target)
        if value == 'latest':
            self.times.append(solution.getLast())
        elif value == 'first':
            self.times.append(solution.getFirst())
        elif value == 'all':
            if self.reconstructed:
                self.times.append(solution.getTimes())
            else:
                self.times.append(solution.getParallelTimes())
        elif isinstance(value, int):
            self.times.append(value)
        else:
            print('Time not found: ', value)
            
            
    def add_field(self, value, col=1):
        self.fields[value] = col
    
    def add_location(self, x='length', y='length', z='length'):
        current = f'line{len(self.locations)}'
        if not isinstance(x, str) and not isinstance(y, str):
            self.locations[current] = [[x, x],[y, y],[self.domain[0][2], self.domain[1][2]]]
        elif not isinstance(x, str) and not isinstance(z, str):
            self.locations[current] = [[x, x],[self.domain[0][1], self.domain[1][1]],[z, z]]
        elif not isinstance(y, str) and not isinstance(z, str):
            self.locations[current] = [[self.domain[0][0], self.domain[1][0]],[y, y],[z, z]]
        else:
            print(f'Bad location definition: {x} {y} {z}')
            
    def run_parallel(self, command):
        #change to the home directory
        home = os.chdir(self.home)
        print('entering directory: ', os.getcwd())

        args = ['parallel', command, '-case', ':::'] +self.cases

        print(args)

        subprocess.run(args)

    #in theory this nested parallel script should work but haven't tried because I need self.samplenames
    def run_postprocess(self):

        args = ['parallel', run_parallel('postProcess'),'-time',':::'] + self.samplenames

        subprocess.run(args)

        pass

    
    def groupByCase(self):
        pass

    def plot(self):            
        fig, ax = plt.subplots()
        ax.scatter(exp_x, exp_y_m[id_], label='EXP')
        ax.scatter(x, y, label='CFD')
        ax.legend(loc='best')
        os.makedirs('results', exist_ok=True)
        plt.savefig(f'results/{case}.png')
           
    def run(self):
        for case in self.cases:
            self.create_sample_cfg(case)
            if not self.decomposed:
                self.reconstruct_par(case)
            for key_loc, value_loc in self.locations.items():
                for key_field in self.fields:
                    self.create_sample_line(case, key_loc, value_loc, key_field)
                #post_process(case, key)
            #self.plot()


#Dustin notes:
# Ability to use run_parallel('blockMesh') before Configuration is done because get_domain_size() required polymesh

        
if __name__ == '__main__':
    target = sys.argv[1]
    plot = Configuration(target)

    
    
    plot.add_field('p') # scalar
    plot.add_field('U', 2) # vector
    #plot.add_field('R', 4) # tensor
    
    plot.add_location(x=0.1, y=0.5)
    plot.add_location(x=0.9, y=0.5)
    #plot.add_location(y=0.0, z=0.0)
    
    plot.add_time(200)
    #plot.add_time('latest')

    plot.run_parallel('simpleFoam')

    
    plot.decomposed = True

    
    
    plot.run()
