import os
import ofplot as of

if os.environ['WM_PROJECT_VERSION'][0] == 'v':
    target = 'testCOM'
else:
    target = 'tutorials/change_boundaryconditions'

plot = of.Configuration(target)
plot.decomposed = True

plot.generate()

plot.change_boundaryconditions(field = 'U', boundary = "outlet", outputname = '\n{\ntype pressureInletOutletVelocity;\n value uniform (0 0 0);\n' )
plot.change_boundaryconditions(field = 'p', boundary = "outlet", outputname = '\n{\ntype totalPressure;\n p0 uniform 0;\n' )


plot.run_parallel('blockMesh')

plot.run_cases("simpleFoam" , max_processors = 3)

plot.reconstructed=True
plot.add_time('all',start_from=100)


plot.post_process()

plot.group_data()


plot.plot_lines_single('sample_line0_U','case')
plot.plot_lines_single('sample_line1_U','case')

