# ofplot
Python module to assist the sampling and post-processing of OpenFOAM cases

Minimal example
---------------

```python
import ofplot

plot = ofplot.Configuration()
plot.add_line(x=0.5, z=0.5)
plot.add_time(100)
plot.generate()
plot.post_process()
plot.plot_by('case')
```
