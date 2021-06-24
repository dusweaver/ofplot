import os
import ofplot as of

if os.environ['WM_PROJECT_VERSION'][0] == 'v':
    target = 'testCOM'
else:
    target = 'testORG'

plot = of.Configuration(target)
plot.decomposed = True

#plot.run_parallel('blockMesh')
#plot.run_parallel('simpleFoam')

#plot.add_field('p')  # scalar
plot.add_field('U', 0)  # vector
 
plot.add_line(x=0.25, z=0.5, coord='rel')
# plot.add_line(x=0.5, z=0.5, coord='rel')
# plot.add_line(x=0.75, z=0.5, coord='rel')
#plot.add_plane(x=0.0, y=0.5, z=0.0, normal='y')

#plot.add_time(100)
plot.add_time(200)

plot.generate()

#plot.run_parallel('simpleFoam')

plot.post_process_test()

plot.group_data()

#plot.plot_lines('time')
plot.plot_lines('case')
#plot.plot_lines('sample')
