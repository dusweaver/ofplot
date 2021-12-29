import os
import ofplot as of

if os.environ['WM_PROJECT_VERSION'][0] == 'v':
    target = 'testCOM'
else:
    target = 'tutorials/run_cases'

plot = of.Configuration(target)
plot.decomposed = True

#plot.run_parallel('blockMesh')

#plot.run_cases("simpleFoam" , max_processors = 3)

plot.reconstructed=True
plot.add_time('all',start_from=100)

plot.generate()

#plot.run_parallel('simpleFoam')

plot.post_process()

plot.group_data()


plot.plot_lines_single('sample_line0_U','case')
plot.plot_lines_single('sample_line1_U','case')

