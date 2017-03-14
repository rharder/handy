


import numpy as np

from bokeh.plotting import figure, output_file, show
from bokeh.sampledata.stocks import AAPL

# prepare some data
aapl = np.array(AAPL['adj_close'])
aapl_dates = np.array(AAPL['date'], dtype=np.datetime64)

window_size = 30
window = np.ones(window_size)/float(window_size)
aapl_avg = np.convolve(aapl, window, 'same')

# output to static HTML file
output_file("stocks.html", title="stocks.py example")

# create a new plot with a a datetime axis type
p = figure(width=800, height=350, x_axis_type="datetime")

# add renderers
p.circle(aapl_dates, aapl, size=4, color='darkgrey', alpha=0.2, legend='close')
p.line(aapl_dates, aapl_avg, color='navy', legend='avg')

# NEW: customize by setting attributes
p.title.text = "AAPL One-Month Average"
p.legend.location = "top_left"
p.grid.grid_line_alpha=0
p.xaxis.axis_label = 'Date'
p.yaxis.axis_label = 'Price'
p.ygrid.band_fill_color="olive"
p.ygrid.band_fill_alpha = 0.1

# show the results
show(p)




#
# import numpy as np
# from bokeh.plotting import *
# from bokeh.models import ColumnDataSource
#
# # prepare some date
# N = 300
# x = np.linspace(0, 4*np.pi, N)
# y0 = np.sin(x)
# y1 = np.cos(x)
#
# # output to static HTML file
# output_file("linked_brushing.html")
#
# # NEW: create a column data source for the plots to share
# source = ColumnDataSource(data=dict(x=x, y0=y0, y1=y1))
#
# TOOLS = "pan,wheel_zoom,box_zoom,reset,save,box_select,lasso_select"
#
# # create a new plot and add a renderer
# left = figure(tools=TOOLS, width=350, height=350, title=None)
# left.circle('x', 'y0', source=source)
#
# # create another new plot and add a renderer
# right = figure(tools=TOOLS, width=350, height=350, title=None)
# right.circle('x', 'y1', source=source)
#
# # put the subplots in a gridplot
# p = gridplot([[left, right]])
#
# # show the results
# show(p)



#
# import numpy as np
#
# from bokeh.plotting import figure, output_file, show
#
# # prepare some data
# N = 4000
# x = np.random.random(size=N) * 100
# y = np.random.random(size=N) * 100
# radii = np.random.random(size=N) * 1.5
# colors = [
#     "#%02x%02x%02x" % (int(r), int(g), 150) for r, g in zip(50+2*x, 30+2*y)
# ]
#
# # output to static HTML file (with CDN resources)
# output_file("color_scatter.html", title="color_scatter.py example", mode="cdn")
#
# TOOLS="resize,crosshair,pan,wheel_zoom,box_zoom,reset,box_select,lasso_select"
#
# # create a new plot with the tools above, and explicit ranges
# p = figure(tools=TOOLS, x_range=(0,100), y_range=(0,100))
#
# # add a circle renderer with vectorized colors and sizes
# p.circle(x,y, radius=radii, fill_color=colors, fill_alpha=0.6, line_color=None)
#
# # show the results
# show(p)



# http://bokeh.pydata.org/en/latest/docs/user_guide/quickstart.html#userguide-quickstart
# from bokeh.plotting import figure, output_file, show
#
# x = [1,2,3,4,5]
# y = [6,7,2,4,5]
#
# output_file("lines.html")
#
# p = figure(title="simple line example", x_axis_label="x", y_axis_label="y")
#
# p.line(x,y, legend="Temp.", line_width=2)
#
# show(p)
#
# from bokeh.plotting import figure, output_file, show
#
# # prepare some data
# x = [0.1, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
# y0 = [i**2 for i in x]
# y1 = [10**i for i in x]
# y2 = [10**(i**2) for i in x]
#
# # output to static HTML file
# output_file("log_lines.html")
#
# # create a new plot
# p = figure(
#    tools="pan,box_zoom,reset,save",
#    y_axis_type="log", y_range=[0.001, 10**11], title="log axis example",
#    x_axis_label='sections', y_axis_label='particles'
# )
#
# # add some renderers
# p.line(x, x, legend="y=x")
# p.circle(x, x, legend="y=x", fill_color="white", size=8)
# p.line(x, y0, legend="y=x^2", line_width=3)
# p.line(x, y1, legend="y=10^x", line_color="red")
# p.circle(x, y1, legend="y=10^x", fill_color="red", line_color="red", size=6)
# p.line(x, y2, legend="y=10^x^2", line_color="orange", line_dash="4 4")
#
# # show the results
# show(p)
