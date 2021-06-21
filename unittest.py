import os
import ofplot as of

if os.environ['WM_PROJECT_VERSION'][0] == 'v':
    target = 'testCOM'
else:
    target = 'testORG'

plot = of.Configuration(target)

plot.add_field('p')  # scalar
plot.add_field('U', 2)  # vector

plot.add_line(x=0.1, y=0.5, coord='rel')
plot.add_line(x=0.9, y=0.5, coord='abs')
plot.add_plane(x=0.0, y=0.5, z=0.0, normal='y')

plot.add_time(100)
plot.add_time(200)

plot.decomposed = True

plot.generate()

#plot.run_parallel('simpleFoam')

plot.post_process_test()
